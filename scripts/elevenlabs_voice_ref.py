"""Generate ElevenLabs v4/v3 voice reference audio and export a whole-second black-frame MP4 for Seedance / Higgsfield."""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL_ID = "eleven_v4"
FALLBACK_MODEL_ID = "eleven_v3"
DEFAULT_STS_MODEL_ID = "eleven_multilingual_sts_v2"
DEFAULT_VOICE_SAMPLE = Path(__file__).resolve().parent.parent / "resources" / "eva_voice_master.wav"
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
PLACEHOLDER_VALUES = {
    "",
    "your_elevenlabs_api_key_here",
    "your_voice_id_here",
    "changeme",
    "replace_me",
}


def find_dotenv(explicit_path: str | None = None) -> Path | None:
    """Locate a .env file from explicit path, CWD parents, or script parents."""
    if explicit_path:
        candidate = Path(explicit_path).expanduser().resolve()
        return candidate if candidate.is_file() else None

    search_roots = [Path.cwd().resolve(), Path(__file__).resolve().parent]
    seen: set[Path] = set()
    for root in search_roots:
        for parent in [root, *root.parents]:
            if parent in seen:
                continue
            seen.add(parent)
            env_file = parent / ".env"
            if env_file.is_file():
                return env_file
    return None


def load_dotenv(env_path: Path | None) -> dict[str, str]:
    """Parse key=value pairs from a .env file without external dependencies."""
    loaded: dict[str, str] = {}
    if env_path is None or not env_path.is_file():
        return loaded
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]
        loaded[key] = val
    return loaded


def resolve_config(args: argparse.Namespace) -> tuple[str, str, str, Path | None]:
    """Resolve API key, voice ID, and model ID from CLI args, environment, and .env."""
    env_path = find_dotenv(args.env)
    dotenv_vars = load_dotenv(env_path)

    def get_var(name: str) -> str:
        return (os.environ.get(name) or dotenv_vars.get(name) or "").strip()

    api_key = (args.api_key or get_var("ELEVENLABS_API_KEY")).strip()
    voice_id = (args.voice_id or get_var("ELEVENLABS_VOICE_ID")).strip()
    model_id = (args.model or get_var("ELEVENLABS_MODEL_ID") or DEFAULT_MODEL_ID).strip()

    if api_key.lower() in PLACEHOLDER_VALUES:
        api_key = ""
    if voice_id.lower() in PLACEHOLDER_VALUES:
        voice_id = ""
    return api_key, voice_id, model_id, env_path


def ensure_binaries() -> None:
    """Verify ffmpeg and ffprobe are available on PATH."""
    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise RuntimeError(f"Required binary '{binary}' was not found on PATH.")


def probe_media(media_path: Path) -> dict:
    """Return ffprobe JSON metadata for an audio or video file."""
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(media_path),
        ],
        text=True,
    )
    return json.loads(out)


def get_audio_duration(audio_path: Path) -> float:
    """Measure exact audio duration in seconds via ffprobe."""
    meta = probe_media(audio_path)
    duration = meta.get("format", {}).get("duration")
    if duration is None:
        audio_stream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "audio"), None)
        duration = audio_stream.get("duration") if audio_stream else None
    if duration is None:
        raise RuntimeError(f"Unable to read audio duration from {audio_path}")
    return float(duration)


def fetch_voices(api_key: str) -> list[dict]:
    """List available voices from the ElevenLabs API."""
    req = urllib.request.Request(
        f"{ELEVENLABS_BASE_URL}/voices",
        headers={"xi-api-key": api_key, "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("voices", [])


def synthesize_tts(
    *,
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str,
    output_mp3: Path,
    language_code: str | None = None,
    stability: float | None = None,
    similarity_boost: float | None = None,
    style: float | None = None,
    output_format: str = "mp3_44100_128",
) -> str:
    """Call ElevenLabs Text-to-Speech API and save the resulting MP3. Returns actual model_id used."""
    body: dict = {
        "text": text,
        "model_id": model_id,
    }
    if language_code:
        body["language_code"] = language_code
    voice_settings: dict[str, float] = {}
    if stability is not None:
        voice_settings["stability"] = stability
    if similarity_boost is not None:
        voice_settings["similarity_boost"] = similarity_boost
    if style is not None:
        voice_settings["style"] = style
    if voice_settings:
        body["voice_settings"] = voice_settings

    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}?output_format={output_format}"

    def _post(payload_dict: dict) -> bytes:
        data = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.read()

    used_model = model_id
    try:
        audio_bytes = _post(body)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        should_retry_lang = (
            exc.code in (400, 422)
            and "language_code" in body
            and "language" in err_body.lower()
        )
        if should_retry_lang:
            body_no_lang = {k: v for k, v in body.items() if k != "language_code"}
            print(
                f"[warn] Model {model_id} rejected explicit language_code; retrying with automatic language detection.",
                file=sys.stderr,
            )
            try:
                audio_bytes = _post(body_no_lang)
            except urllib.error.HTTPError as exc2:
                err_body2 = exc2.read().decode("utf-8", errors="ignore")
                if exc2.code in (400, 404, 422) and model_id == DEFAULT_MODEL_ID and "model" in err_body2.lower():
                    body_no_lang["model_id"] = FALLBACK_MODEL_ID
                    used_model = FALLBACK_MODEL_ID
                    print(
                        f"[warn] {DEFAULT_MODEL_ID} unavailable on this account/endpoint; falling back to {FALLBACK_MODEL_ID}.",
                        file=sys.stderr,
                    )
                    audio_bytes = _post(body_no_lang)
                else:
                    raise RuntimeError(f"ElevenLabs API error {exc2.code}: {err_body2}") from exc2
        elif exc.code in (400, 404, 422) and model_id == DEFAULT_MODEL_ID and "model" in err_body.lower():
            body["model_id"] = FALLBACK_MODEL_ID
            used_model = FALLBACK_MODEL_ID
            print(
                f"[warn] {DEFAULT_MODEL_ID} unavailable on this account/endpoint; falling back to {FALLBACK_MODEL_ID}.",
                file=sys.stderr,
            )
            audio_bytes = _post(body)
        else:
            raise RuntimeError(f"ElevenLabs API error {exc.code}: {err_body}") from exc

    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    output_mp3.write_bytes(audio_bytes)
    return used_model


def _build_multipart_form(
    fields: list[tuple[str, str]],
    files: list[tuple[str, Path]],
) -> tuple[bytes, str]:
    """Encode multipart/form-data body using stdlib only."""
    boundary = f"----AntigravityBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    for field_name, file_path in files:
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode("utf-8")
        )
        chunks.append(file_path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def clone_voice_from_sample(
    *,
    api_key: str,
    name: str,
    sample_paths: list[Path],
    description: str = "Consistent avatar voice clone",
) -> str:
    """Create an ElevenLabs Instant Voice Clone from reference audio samples; return voice_id."""
    for sp in sample_paths:
        if not sp.is_file():
            raise FileNotFoundError(f"Voice sample not found: {sp}")
    body, content_type = _build_multipart_form(
        fields=[("name", name), ("description", description)],
        files=[("files", sp) for sp in sample_paths],
    )
    req = urllib.request.Request(
        f"{ELEVENLABS_BASE_URL}/voices/add",
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": content_type,
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"ElevenLabs voice clone error {exc.code}: {err_body}") from exc
    voice_id = str(payload.get("voice_id") or "").strip()
    if not voice_id:
        raise RuntimeError(f"Unexpected ElevenLabs /voices/add response: {payload}")
    return voice_id


def convert_speech_to_speech(
    *,
    api_key: str,
    voice_id: str,
    source_audio_path: Path,
    output_mp3_path: Path,
    model_id: str = DEFAULT_STS_MODEL_ID,
    stability: float | None = None,
    similarity_boost: float | None = None,
    style: float | None = None,
    remove_background_noise: bool = True,
    output_format: str = "mp3_44100_128",
) -> Path:
    """Convert audio timbre onto target ElevenLabs voice while preserving exact millisecond timing."""
    fields: list[tuple[str, str]] = [
        ("model_id", model_id),
        ("remove_background_noise", "true" if remove_background_noise else "false"),
    ]
    voice_settings: dict[str, float] = {}
    if stability is not None:
        voice_settings["stability"] = stability
    if similarity_boost is not None:
        voice_settings["similarity_boost"] = similarity_boost
    if style is not None:
        voice_settings["style"] = style
    if voice_settings:
        fields.append(("voice_settings", json.dumps(voice_settings)))

    body, content_type = _build_multipart_form(
        fields=fields,
        files=[("audio", source_audio_path)],
    )
    url = f"{ELEVENLABS_BASE_URL}/speech-to-speech/{voice_id}?output_format={output_format}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": content_type,
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio_bytes = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"ElevenLabs STS error {exc.code}: {err_body}") from exc

    output_mp3_path.parent.mkdir(parents=True, exist_ok=True)
    output_mp3_path.write_bytes(audio_bytes)
    return output_mp3_path


def unify_media_voice(
    *,
    api_key: str,
    voice_id: str,
    src_path: Path,
    dst_path: Path,
    sts_model: str = DEFAULT_STS_MODEL_ID,
    stability: float | None = None,
    similarity_boost: float | None = None,
    style: float | None = None,
) -> Path:
    """Replace vocal timbre on an audio file or MP4 video via Speech-to-Speech, keeping video & timing 1:1."""
    ensure_binaries()
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    if src_path.suffix.lower() not in VIDEO_EXTS:
        return convert_speech_to_speech(
            api_key=api_key,
            voice_id=voice_id,
            source_audio_path=src_path,
            output_mp3_path=dst_path,
            model_id=sts_model,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        raw_wav = tmp_dir / "src_audio.wav"
        sts_mp3 = tmp_dir / "sts_unified.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src_path), "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1", str(raw_wav)],
            check=True,
            capture_output=True,
        )
        convert_speech_to_speech(
            api_key=api_key,
            voice_id=voice_id,
            source_audio_path=raw_wav,
            output_mp3_path=sts_mp3,
            model_id=sts_model,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
        )
        tmp_out = tmp_dir / f"muxed{dst_path.suffix}"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(src_path),
                "-i", str(sts_mp3),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(tmp_out),
            ],
            check=True,
            capture_output=True,
        )
        shutil.move(str(tmp_out), str(dst_path))
    return dst_path


def _save_voice_id_to_env(env_path: Path | None, voice_id: str) -> Path:
    """Write or update ELEVENLABS_VOICE_ID in .env without losing other keys."""
    target = env_path if env_path is not None else (Path.cwd() / ".env")
    lines = target.read_text(encoding="utf-8").splitlines() if target.is_file() else []
    replaced = False
    new_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("ELEVENLABS_VOICE_ID="):
            new_lines.append(f"ELEVENLABS_VOICE_ID={voice_id}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"ELEVENLABS_VOICE_ID={voice_id}")
    target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return target


def export_black_video_whole_seconds(
    audio_path: Path,
    output_mp4: Path,
    *,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    min_seconds: int = 1,
) -> tuple[float, int, float]:
    """Pad audio with trailing silence to math.ceil(duration) and export 1280x720 H.264/AAC MP4."""
    ensure_binaries()
    raw_duration = get_audio_duration(audio_path)
    target_seconds = max(min_seconds, math.ceil(raw_duration))

    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={width}x{height}:r={fps}",
        "-i",
        str(audio_path),
        "-filter_complex",
        f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=0:{target_seconds},asetpts=PTS-STARTPTS[aout]",
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-t",
        str(target_seconds),
        "-movflags",
        "+faststart",
        str(output_mp4),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}):\n{proc.stderr}")

    verified_meta = probe_media(output_mp4)
    verified_duration = float(verified_meta["format"]["duration"])
    return raw_duration, target_seconds, verified_duration


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate ElevenLabs v4/v3 voice reference audio and whole-second 720p black-frame MP4."
    )
    parser.add_argument("--text", help="Tagged phonetic pangram text (with [audio tags]).")
    parser.add_argument("--text-file", help="Path to UTF-8 text file containing the tagged pangram.")
    parser.add_argument(
        "--audio-in",
        help="Existing audio file (.mp3/.wav) generated via ElevenLabs Web UI; skips TTS API call and exports MP4.",
    )
    parser.add_argument("--out-dir", default=".", help="Output directory (default: current directory).")
    parser.add_argument("--out-mp3", help="Output MP3 path (default: <out-dir>/reference_voce.mp3).")
    parser.add_argument("--out-mp4", help="Output MP4 path (default: <out-dir>/reference_voce.mp4).")
    parser.add_argument("--env", help="Explicit path to .env file.")
    parser.add_argument("--api-key", help="Override ELEVENLABS_API_KEY.")
    parser.add_argument("--voice-id", help="Override ELEVENLABS_VOICE_ID.")
    parser.add_argument(
        "--model",
        help=f"ElevenLabs model_id (default: ELEVENLABS_MODEL_ID or '{DEFAULT_MODEL_ID}', supports '{FALLBACK_MODEL_ID}').",
    )
    parser.add_argument(
        "--language",
        help="Optional ISO 639-1 language code for cross-language hint (e.g. 'it', 'en', 'es').",
    )
    parser.add_argument("--stability", type=float, help="Optional ElevenLabs stability (0.0-1.0).")
    parser.add_argument("--similarity", type=float, help="Optional ElevenLabs similarity_boost (0.0-1.0).")
    parser.add_argument("--style", type=float, help="Optional ElevenLabs style exaggeration (0.0-1.0).")
    parser.add_argument(
        "--min-seconds",
        type=int,
        default=1,
        help="Minimum whole-second duration for the exported MP4 (default: 1; use 5 for Voicesheet min).",
    )
    parser.add_argument("--list-voices", action="store_true", help="List available voices from ElevenLabs and exit.")
    parser.add_argument("--check-env", action="store_true", help="Check .env credentials and exit.")
    parser.add_argument(
        "--clone-voice",
        metavar="NAME",
        help="Clone a new ElevenLabs voice from --sample (defaults to resources/eva_voice_master.wav).",
    )
    parser.add_argument(
        "--sample",
        action="append",
        default=[],
        help="Audio sample path for --clone-voice (repeatable; defaults to resources/eva_voice_master.wav).",
    )
    parser.add_argument(
        "--save-env",
        action="store_true",
        help="Save cloned voice_id to .env as ELEVENLABS_VOICE_ID.",
    )
    parser.add_argument(
        "--s2s-in",
        help="Convert voice timbre of an audio or MP4 file via Speech-to-Speech while keeping lip timing.",
    )
    parser.add_argument("--s2s-out", help="Output path for --s2s-in (defaults to <stem>_unified<ext>).")
    parser.add_argument(
        "--unify-dir",
        help="Batch-unify all MP4 clips in a folder onto ELEVENLABS_VOICE_ID via Speech-to-Speech.",
    )
    parser.add_argument("--unify-out-dir", help="Output folder for --unify-dir (default: <DIR>/unified).")
    parser.add_argument("--in-place", action="store_true", help="Overwrite MP4s in place during --unify-dir.")
    parser.add_argument(
        "--sts-model",
        default=DEFAULT_STS_MODEL_ID,
        help=f"Speech-to-Speech model_id (default: {DEFAULT_STS_MODEL_ID}).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    api_key, voice_id, model_id, env_path = resolve_config(args)

    if args.check_env:
        print(f"dotenv_path={env_path or 'not found'}")
        print(f"ELEVENLABS_API_KEY={'SET' if api_key else 'MISSING'}")
        print(f"ELEVENLABS_VOICE_ID={voice_id if voice_id else 'MISSING'}")
        print(f"ELEVENLABS_MODEL_ID={model_id}")
        return 0 if (api_key and voice_id) else 2

    if args.list_voices:
        if not api_key:
            print(
                "MISSING CREDENTIALS: ELEVENLABS_API_KEY is missing in .env / environment.\n"
                "Add ELEVENLABS_API_KEY to your project .env file before listing voices.",
                file=sys.stderr,
            )
            return 2
        voices = fetch_voices(api_key)
        for v in voices:
            labels = v.get("labels") or {}
            print(f"{v.get('voice_id')} | {v.get('name')} | {labels}")
        return 0

    if args.clone_voice:
        if not api_key:
            print("MISSING CREDENTIALS: ELEVENLABS_API_KEY is required for --clone-voice.", file=sys.stderr)
            return 2
        samples = [Path(s).expanduser().resolve() for s in args.sample] if args.sample else [DEFAULT_VOICE_SAMPLE]
        new_id = clone_voice_from_sample(api_key=api_key, name=args.clone_voice, sample_paths=samples)
        print(f"[clone] Created voice '{args.clone_voice}' -> ELEVENLABS_VOICE_ID={new_id}")
        if args.save_env:
            saved_to = _save_voice_id_to_env(env_path, new_id)
            print(f"[env] Saved ELEVENLABS_VOICE_ID to {saved_to}")
        return 0

    if args.s2s_in or args.unify_dir:
        missing = [k for k, val in (("ELEVENLABS_API_KEY", api_key), ("ELEVENLABS_VOICE_ID", voice_id)) if not val]
        if missing:
            print(
                f"MISSING CREDENTIALS: {', '.join(missing)} required for Speech-to-Speech unification.",
                file=sys.stderr,
            )
            return 2
        if args.s2s_in:
            src = Path(args.s2s_in).expanduser().resolve()
            dst = (
                Path(args.s2s_out).expanduser().resolve()
                if args.s2s_out
                else src.with_name(f"{src.stem}_unified{src.suffix}")
            )
            unify_media_voice(
                api_key=api_key,
                voice_id=voice_id,
                src_path=src,
                dst_path=dst,
                sts_model=args.sts_model,
                stability=args.stability,
                similarity_boost=args.similarity,
                style=args.style,
            )
            print(f"[s2s] Unified voice -> {dst}")
            return 0

        src_dir = Path(args.unify_dir).expanduser().resolve()
        mp4s = sorted(p for p in src_dir.glob("*.mp4") if not p.name.endswith("_unified.mp4"))
        if not mp4s:
            print(f"No MP4 clips found in {src_dir}", file=sys.stderr)
            return 1
        out_folder = src_dir if args.in_place else (Path(args.unify_out_dir).expanduser().resolve() if args.unify_out_dir else (src_dir / "unified"))
        out_folder.mkdir(parents=True, exist_ok=True)
        for mp4 in mp4s:
            dst = mp4 if args.in_place else (out_folder / mp4.name)
            unify_media_voice(
                api_key=api_key,
                voice_id=voice_id,
                src_path=mp4,
                dst_path=dst,
                sts_model=args.sts_model,
                stability=args.stability,
                similarity_boost=args.similarity,
                style=args.style,
            )
            print(f"[unify] {mp4.name} -> {dst}")
        return 0

    out_dir = Path(args.out_dir)
    out_mp3 = Path(args.out_mp3) if args.out_mp3 else (out_dir / "reference_voce.mp3")
    out_mp4 = Path(args.out_mp4) if args.out_mp4 else (out_dir / "reference_voce.mp4")

    if args.audio_in:
        audio_src = Path(args.audio_in)
        if not audio_src.is_file():
            print(f"Audio input file not found: {audio_src}", file=sys.stderr)
            return 1
        print(f"[input] Using existing audio file: {audio_src}")
    else:
        missing: list[str] = []
        if not api_key:
            missing.append("ELEVENLABS_API_KEY")
        if not voice_id:
            missing.append("ELEVENLABS_VOICE_ID")
        if missing:
            print(
                f"MISSING CREDENTIALS: {', '.join(missing)} not configured"
                + (f" (checked {env_path})" if env_path else " (no .env found)")
                + ".\n"
                "Stop and ask the user to provide ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env "
                "(or paste the tagged pangram in the free ElevenLabs Web UI and re-run with --audio-in <file.mp3>).",
                file=sys.stderr,
            )
            return 2

        text = args.text
        if not text and args.text_file:
            text = Path(args.text_file).read_text(encoding="utf-8").strip()
        if not text:
            print("Provide --text or --text-file (or --audio-in for an existing MP3).", file=sys.stderr)
            return 1

        used_model = synthesize_tts(
            api_key=api_key,
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_mp3=out_mp3,
            language_code=args.language,
            stability=args.stability,
            similarity_boost=args.similarity,
            style=args.style,
        )
        print(f"[tts] Generated {out_mp3} using model={used_model}, voice_id={voice_id}")
        audio_src = out_mp3

    raw_dur, target_s, verified_dur = export_black_video_whole_seconds(
        audio_src,
        out_mp4,
        min_seconds=args.min_seconds,
    )
    print(f"[audio] Measured duration: {raw_dur:.3f}s -> padded/rounded up (math.ceil) to {target_s}.00s")
    print(f"[video] Exported {out_mp4} (1280x720, H.264, AAC, ffprobe duration={verified_dur:.3f}s, T={target_s}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
