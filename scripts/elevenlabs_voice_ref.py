"""Generate ElevenLabs v4/v3 voice reference audio and export a whole-second black-frame MP4 for Seedance / Higgsfield."""

from __future__ import annotations

import argparse
import array
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path


ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL_ID = "eleven_v4"
FALLBACK_MODEL_ID = "eleven_v3"
DEFAULT_STS_MODEL_ID = "eleven_multilingual_sts_v2"
DEFAULT_STABILITY = 0.78
DEFAULT_SIMILARITY = 0.86
DEFAULT_STYLE = 0.0
DEFAULT_SEED = 424242
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
    stability: float | None = DEFAULT_STABILITY,
    similarity_boost: float | None = DEFAULT_SIMILARITY,
    style: float | None = DEFAULT_STYLE,
    use_speaker_boost: bool = True,
    seed: int | None = DEFAULT_SEED,
    previous_request_ids: list[str] | None = None,
    previous_text: str | None = None,
    output_format: str = "mp3_44100_128",
) -> tuple[str, str | None]:
    """Call ElevenLabs Text-to-Speech API and save the resulting MP3. Returns (model_id, request_id)."""
    body: dict = {
        "text": text,
        "model_id": model_id,
    }
    if language_code:
        body["language_code"] = language_code
    if seed is not None:
        body["seed"] = int(seed)
    if previous_request_ids:
        body["previous_request_ids"] = list(previous_request_ids)[-3:]
    elif previous_text:
        body["previous_text"] = previous_text[-120:]

    voice_settings: dict[str, float | bool] = {"use_speaker_boost": bool(use_speaker_boost)}
    if stability is not None:
        voice_settings["stability"] = float(stability)
    if similarity_boost is not None:
        voice_settings["similarity_boost"] = float(similarity_boost)
    if style is not None:
        voice_settings["style"] = float(style)
    body["voice_settings"] = voice_settings

    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}?output_format={output_format}"

    def _post(payload_dict: dict) -> tuple[bytes, str | None]:
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
            req_id = resp.headers.get("request-id") or resp.headers.get("x-request-id")
            return resp.read(), req_id

    used_model = model_id
    req_id: str | None = None
    try:
        audio_bytes, req_id = _post(body)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        cleaned = dict(body)
        if exc.code in (400, 422) and "previous_request_ids" in cleaned and "request" in err_body.lower():
            cleaned.pop("previous_request_ids", None)
            if previous_text:
                cleaned["previous_text"] = previous_text[-120:]
        should_retry_lang = (
            exc.code in (400, 422)
            and "language_code" in cleaned
            and "language" in err_body.lower()
        )
        if should_retry_lang:
            cleaned.pop("language_code", None)
            print(
                f"[warn] Model {model_id} rejected explicit language_code; retrying with automatic language detection.",
                file=sys.stderr,
            )
            try:
                audio_bytes, req_id = _post(cleaned)
            except urllib.error.HTTPError as exc2:
                err_body2 = exc2.read().decode("utf-8", errors="ignore")
                if exc2.code in (400, 404, 422) and model_id == DEFAULT_MODEL_ID and "model" in err_body2.lower():
                    cleaned["model_id"] = FALLBACK_MODEL_ID
                    cleaned.pop("previous_request_ids", None)
                    used_model = FALLBACK_MODEL_ID
                    print(
                        f"[warn] {DEFAULT_MODEL_ID} unavailable on this account/endpoint; falling back to {FALLBACK_MODEL_ID}.",
                        file=sys.stderr,
                    )
                    audio_bytes, req_id = _post(cleaned)
                else:
                    raise RuntimeError(f"ElevenLabs API error {exc2.code}: {err_body2}") from exc2
        elif exc.code in (400, 422) and cleaned != body:
            audio_bytes, req_id = _post(cleaned)
        elif exc.code in (400, 404, 422) and model_id == DEFAULT_MODEL_ID and "model" in err_body.lower():
            cleaned["model_id"] = FALLBACK_MODEL_ID
            cleaned.pop("previous_request_ids", None)
            used_model = FALLBACK_MODEL_ID
            print(
                f"[warn] {DEFAULT_MODEL_ID} unavailable on this account/endpoint; falling back to {FALLBACK_MODEL_ID}.",
                file=sys.stderr,
            )
            audio_bytes, req_id = _post(cleaned)
        else:
            raise RuntimeError(f"ElevenLabs API error {exc.code}: {err_body}") from exc

    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    output_mp3.write_bytes(audio_bytes)
    return used_model, req_id


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
    stability: float | None = DEFAULT_STABILITY,
    similarity_boost: float | None = DEFAULT_SIMILARITY,
    style: float | None = DEFAULT_STYLE,
    use_speaker_boost: bool = True,
    seed: int | None = DEFAULT_SEED,
    remove_background_noise: bool = True,
    output_format: str = "mp3_44100_128",
) -> Path:
    """Convert audio timbre onto target ElevenLabs voice while preserving exact millisecond timing."""
    fields: list[tuple[str, str]] = [
        ("model_id", model_id),
        ("remove_background_noise", "true" if remove_background_noise else "false"),
    ]
    if seed is not None:
        fields.append(("seed", str(int(seed))))

    voice_settings: dict[str, float | bool] = {"use_speaker_boost": bool(use_speaker_boost)}
    if stability is not None:
        voice_settings["stability"] = float(stability)
    if similarity_boost is not None:
        voice_settings["similarity_boost"] = float(similarity_boost)
    if style is not None:
        voice_settings["style"] = float(style)
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
        with urllib.request.urlopen(req, timeout=180) as resp:
            audio_bytes = resp.read()
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"ElevenLabs STS error {exc.code}: {err_body}") from exc

    output_mp3_path.parent.mkdir(parents=True, exist_ok=True)
    output_mp3_path.write_bytes(audio_bytes)
    return output_mp3_path


def _ffprobe_duration(path: Path) -> float:
    return get_audio_duration(path) if path.suffix.lower() in {".wav", ".mp3"} else float(
        probe_media(path)["format"]["duration"]
    )


def _trim_and_clean_speech_wav(src_media: Path, out_wav: Path, *, target_lufs: float = -16.0) -> float:
    """Extract mono 44.1kHz cleaned speech WAV with leading/trailing silence trimmed & normalized."""
    ensure_binaries()
    total_dur = _ffprobe_duration(src_media)
    sil = subprocess.run(
        ["ffmpeg", "-i", str(src_media), "-af", "silencedetect=noise=-32dB:d=0.12", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    events = re.findall(r"silence_(start|end):\s*([0-9.]+)", sil.stderr)
    parsed = [(k, float(ts)) for k, ts in events]
    s0, s1 = 0.0, total_dur
    if len(parsed) >= 2 and parsed[0][0] == "start" and parsed[0][1] <= 0.08 and parsed[1][0] == "end":
        s0 = max(0.0, parsed[1][1] - 0.04)
    if len(parsed) >= 2 and parsed[-2][0] == "start" and parsed[-1][0] == "end":
        if abs(parsed[-1][1] - total_dur) <= 0.08 and parsed[-2][1] > s0 + 0.4:
            s1 = min(total_dur, parsed[-2][1] + 0.06)
    elif parsed and parsed[-1][0] == "start" and parsed[-1][1] > s0 + 0.4:
        s1 = min(total_dur, parsed[-1][1] + 0.06)
    if s1 - s0 < 0.4:
        s0, s1 = 0.0, total_dur

    af = (
        f"atrim=start={s0:.4f}:end={s1:.4f},asetpts=PTS-STARTPTS,"
        "highpass=f=80,lowpass=f=14000,equalizer=f=250:t=q:w=1.2:g=-2.0,"
        "acompressor=threshold=-18dB:ratio=2.5:attack=5:release=60,"
        f"loudnorm=I={target_lufs:.1f}:TP=-1.5:LRA=7"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src_media), "-vn", "-af", af, "-ar", "44100", "-ac", "1", "-acodec", "pcm_s16le", str(out_wav)],
        check=True,
    )
    return _ffprobe_duration(out_wav)


def build_golden_voice_master(clips_dir: Path, out_wav: Path, *, gap_s: float = 0.35) -> tuple[float, list[str]]:
    """Build a multi-inflection ~30s golden voice sample from a folder of clean @Eva clips."""
    ensure_binaries()
    candidates = sorted(p for p in clips_dir.glob("*.mp4") if "_unified" not in p.stem.lower())
    if not candidates:
        candidates = sorted(p for p in clips_dir.glob("*.wav") if "_unified" not in p.stem.lower())
    if not candidates:
        raise FileNotFoundError(f"No .mp4 or .wav clips found in {clips_dir}")

    # Prefer golden warm-room delivery order first when available, excluding duplicate TikTok CTA if IG is present
    names = {p.name: p for p in candidates}
    ordered: list[Path] = []
    preferred = ["eva_04.mp4", "eva_03b.mp4", "eva_01.mp4", "eva_05b.mp4", "eva_02.mp4", "eva_06_ig.mp4"]
    for pref in preferred:
        if pref in names:
            ordered.append(names.pop(pref))
    for k in sorted(names):
        if "tiktok" in k and any("ig" in p.name for p in ordered):
            continue
        ordered.append(names[k])

    used_names: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        sil_wav = tmp_dir / "gap.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{gap_s:.3f}", "-acodec", "pcm_s16le", str(sil_wav)],
            check=True,
        )
        concat_list = tmp_dir / "concat.txt"
        lines: list[str] = []
        total_acc = 0.0
        for idx, clip in enumerate(ordered):
            part = tmp_dir / f"part_{idx:02d}.wav"
            dur = _trim_and_clean_speech_wav(clip, part, target_lufs=-16.0)
            used_names.append(f"{clip.name} ({dur:.2f}s)")
            lines.append(f"file '{part.as_posix()}'")
            total_acc += dur
            if idx < len(ordered) - 1:
                lines.append(f"file '{sil_wav.as_posix()}'")
                total_acc += gap_s
            if total_acc >= 34.0:
                break
        concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

        raw_joined = tmp_dir / "raw_joined.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(raw_joined)],
            check=True,
        )
        # 2-pass linear EBU R128 loudnorm (-16 LUFS master for IVC clarity without clipping)
        p1 = subprocess.run(
            ["ffmpeg", "-y", "-i", str(raw_joined), "-af", "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1.stderr, re.DOTALL)
        if m:
            ln = json.loads(m.group(0))
            af2 = (
                "loudnorm=I=-16:TP=-1.5:LRA=7:"
                f"measured_I={ln['input_i']}:measured_LRA={ln['input_lra']}:"
                f"measured_TP={ln['input_tp']}:measured_thresh={ln['input_thresh']}:linear=true"
            )
        else:
            af2 = "loudnorm=I=-16:TP=-1.5:LRA=7"
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_joined), "-af", af2, "-ar", "44100", "-ac", "1", "-acodec", "pcm_s16le", str(out_wav)],
            check=True,
        )
    return _ffprobe_duration(out_wav), used_names


def _find_silence_cut_time(samples: array.array, sr: int, nominal_s: float, search_half_s: float = 0.38) -> float:
    """Find the lowest-RMS center within nominal_s +/- search_half_s using a 40ms sliding window."""
    n = len(samples)
    win = max(1, int(0.04 * sr))
    step = max(1, int(0.005 * sr))
    lo = max(0, int((nominal_s - search_half_s) * sr))
    hi = min(n - win - 1, int((nominal_s + search_half_s) * sr))
    if hi <= lo:
        return max(0.0, min(n / float(sr), nominal_s))
    best_pos = int(nominal_s * sr)
    best_energy = float("inf")
    for pos in range(lo, hi + 1, step):
        chunk = samples[pos : pos + win]
        e = sum(x * x for x in chunk) / float(len(chunk))
        if e < best_energy:
            best_energy = e
            best_pos = pos + win // 2
    return best_pos / float(sr)


def unify_directory_single_pass(
    *,
    api_key: str,
    voice_id: str,
    mp4s: list[Path],
    out_folder: Path,
    in_place: bool,
    sts_model: str = DEFAULT_STS_MODEL_ID,
    stability: float | None = DEFAULT_STABILITY,
    similarity_boost: float | None = DEFAULT_SIMILARITY,
    style: float | None = DEFAULT_STYLE,
    use_speaker_boost: bool = True,
    seed: int | None = DEFAULT_SEED,
    gap_s: float = 0.65,
) -> list[tuple[str, Path]]:
    """Concatenate pre-cleaned clip audio with 0.65s gaps -> ONE single STS pass -> slice & lip-sync lock."""
    ensure_binaries()
    out_folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        sil_wav = tmp_dir / "gap.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", f"{gap_s:.3f}", "-acodec", "pcm_s16le", str(sil_wav)],
            check=True,
        )
        clip_durs: list[float] = []
        concat_lines: list[str] = []
        pre_af = (
            "highpass=f=80,lowpass=f=14000,equalizer=f=250:t=q:w=1.2:g=-2.0,"
            "acompressor=threshold=-18dB:ratio=2.5:attack=5:release=60,"
            "loudnorm=I=-16:TP=-1.5:LRA=7"
        )
        for idx, mp4 in enumerate(mp4s):
            dur = float(probe_media(mp4)["format"]["duration"])
            clip_durs.append(dur)
            pwav = tmp_dir / f"in_{idx:02d}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vn", "-af", f"{pre_af},apad,atrim=0:{dur:.4f}", "-ar", "48000", "-ac", "1", "-acodec", "pcm_s16le", str(pwav)],
                check=True,
            )
            concat_lines.append(f"file '{pwav.as_posix()}'")
            if idx < len(mp4s) - 1:
                concat_lines.append(f"file '{sil_wav.as_posix()}'")

        concat_txt = tmp_dir / "master_concat.txt"
        concat_txt.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
        master_in = tmp_dir / "master_in.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(master_in)],
            check=True,
        )
        t_in = get_audio_duration(master_in)

        master_sts_mp3 = tmp_dir / "master_sts.mp3"
        convert_speech_to_speech(
            api_key=api_key,
            voice_id=voice_id,
            source_audio_path=master_in,
            output_mp3_path=master_sts_mp3,
            model_id=sts_model,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
            seed=seed,
        )

        master_sts_wav = tmp_dir / "master_sts.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(master_sts_mp3), "-ar", "48000", "-ac", "1", "-acodec", "pcm_s16le", str(master_sts_wav)],
            check=True,
        )
        with wave.open(str(master_sts_wav), "rb") as wf:
            sr = wf.getframerate()
            samples = array.array("h")
            samples.frombytes(wf.readframes(wf.getnframes()))
        t_sts = len(samples) / float(sr)
        scale = t_sts / max(0.1, t_in)

        # Compute split midpoints cleanly inside every 0.65s separator gap
        cuts_s = [0.0]
        cum = 0.0
        for idx, dur in enumerate(clip_durs[:-1]):
            gap_mid_in = cum + dur + gap_s * 0.5
            cuts_s.append(_find_silence_cut_time(samples, sr, gap_mid_in * scale, search_half_s=gap_s * 0.48))
            cum += dur + gap_s
        cuts_s.append(t_sts)

        results: list[tuple[str, Path]] = []
        half_gap_trim = (gap_s * 0.5 * scale) * 0.72
        for idx, (mp4, target_dur) in enumerate(zip(mp4s, clip_durs)):
            seg_start = cuts_s[idx] + (half_gap_trim if idx > 0 else 0.0)
            seg_end = cuts_s[idx + 1] - (half_gap_trim if idx < len(clip_durs) - 1 else 0.0)
            seg_dur = max(0.2, seg_end - seg_start)
            rate = seg_dur / max(0.2, target_dur)
            tempo_chain = f"atempo={max(0.95, min(1.05, rate)):.5f}," if 0.95 <= rate <= 1.05 and abs(rate - 1.0) > 0.002 else ""
            af_seg = (
                f"atrim=start={seg_start:.4f}:end={seg_end:.4f},asetpts=PTS-STARTPTS,"
                f"{tempo_chain}"
                "loudnorm=I=-14.0:TP=-1.5:LRA=7,"
                f"apad,atrim=0:{target_dur:.4f},asetpts=PTS-STARTPTS"
            )
            dst = mp4 if in_place else (out_folder / mp4.name)
            tmp_out = tmp_dir / f"mux_{idx:02d}{dst.suffix}"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(mp4),
                    "-i", str(master_sts_wav),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-af", af_seg,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-ar", "48000",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    str(tmp_out),
                ],
                check=True,
            )
            shutil.move(str(tmp_out), str(dst))
            results.append((mp4.name, dst))
    return results


def unify_media_voice(
    *,
    api_key: str,
    voice_id: str,
    src_path: Path,
    dst_path: Path,
    sts_model: str = DEFAULT_STS_MODEL_ID,
    stability: float | None = DEFAULT_STABILITY,
    similarity_boost: float | None = DEFAULT_SIMILARITY,
    style: float | None = DEFAULT_STYLE,
    use_speaker_boost: bool = True,
    seed: int | None = DEFAULT_SEED,
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
            use_speaker_boost=use_speaker_boost,
            seed=seed,
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        raw_wav = tmp_dir / "src_audio.wav"
        sts_mp3 = tmp_dir / "sts_unified.mp3"
        target_dur = float(probe_media(src_path)["format"]["duration"])
        pre_af = (
            "highpass=f=80,lowpass=f=14000,equalizer=f=250:t=q:w=1.2:g=-2.0,"
            "acompressor=threshold=-18dB:ratio=2.5:attack=5:release=60,"
            "loudnorm=I=-16:TP=-1.5:LRA=7"
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src_path), "-vn",
                "-af", pre_af,
                "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1", str(raw_wav),
            ],
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
            use_speaker_boost=use_speaker_boost,
            seed=seed,
        )
        tmp_out = tmp_dir / f"muxed{dst_path.suffix}"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(src_path),
                "-i", str(sts_mp3),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-af", f"loudnorm=I=-14.0:TP=-1.5:LRA=7,apad,atrim=0:{target_dur:.4f},asetpts=PTS-STARTPTS",
                "-c:v", "copy",
                "-c:a", "aac",
                "-ar", "48000",
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
    parser.add_argument(
        "--stability",
        type=float,
        default=DEFAULT_STABILITY,
        help=f"ElevenLabs voice stability (0.0-1.0, default: {DEFAULT_STABILITY} for cross-clip lock).",
    )
    parser.add_argument(
        "--similarity",
        type=float,
        default=DEFAULT_SIMILARITY,
        help=f"ElevenLabs similarity_boost (0.0-1.0, default: {DEFAULT_SIMILARITY}).",
    )
    parser.add_argument(
        "--style",
        type=float,
        default=DEFAULT_STYLE,
        help=f"ElevenLabs style exaggeration (0.0-1.0, default: {DEFAULT_STYLE} to avoid pitch drift).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic seed for cross-clip reproducibility (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--no-speaker-boost",
        action="store_true",
        help="Disable ElevenLabs use_speaker_boost (enabled by default for voice lock).",
    )
    parser.add_argument(
        "--stitch-file",
        help="Text file (one spoken chunk per line) to synthesize sequentially with previous_request_ids request stitching.",
    )
    parser.add_argument(
        "--min-seconds",
        type=int,
        default=1,
        help="Minimum whole-second duration for the exported MP4 (default: 1; use 5 for Voicesheet min).",
    )
    parser.add_argument("--list-voices", action="store_true", help="List available voices from ElevenLabs and exit.")
    parser.add_argument("--check-env", action="store_true", help="Check .env credentials and exit.")
    parser.add_argument(
        "--build-golden-sample",
        metavar="CLIPS_DIR",
        help="Build ~30s multi-inflection golden voice master WAV from clean @Eva MP4s (no API key needed).",
    )
    parser.add_argument(
        "--golden-out",
        default=str(DEFAULT_VOICE_SAMPLE),
        help=f"Output WAV path for --build-golden-sample (default: {DEFAULT_VOICE_SAMPLE}).",
    )
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
        help="Batch-unify all MP4 clips in a folder onto ELEVENLABS_VOICE_ID (single-pass concatenated STS by default).",
    )
    parser.add_argument(
        "--per-clip-sts",
        action="store_true",
        help="Call Speech-to-Speech separately per clip instead of single-pass concatenated STS.",
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

    if args.build_golden_sample:
        clips_dir = Path(args.build_golden_sample).expanduser().resolve()
        out_wav = Path(args.golden_out).expanduser().resolve()
        dur_s, used = build_golden_voice_master(clips_dir, out_wav)
        print(f"[golden] Built {out_wav} ({dur_s:.2f}s, -16 LUFS) from {len(used)} clips: {', '.join(used)}")
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
        speaker_boost = not args.no_speaker_boost
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
                use_speaker_boost=speaker_boost,
                seed=args.seed,
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
        if not args.per_clip_sts:
            res_list = unify_directory_single_pass(
                api_key=api_key,
                voice_id=voice_id,
                mp4s=mp4s,
                out_folder=out_folder,
                in_place=args.in_place,
                sts_model=args.sts_model,
                stability=args.stability,
                similarity_boost=args.similarity,
                style=args.style,
                use_speaker_boost=speaker_boost,
                seed=args.seed,
            )
            for name, dst in res_list:
                print(f"[unify single-pass] {name} -> {dst}")
            return 0
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
                use_speaker_boost=speaker_boost,
                seed=args.seed,
            )
            print(f"[unify per-clip] {mp4.name} -> {dst}")
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

        speaker_boost = not args.no_speaker_boost
        if args.stitch_file:
            ensure_binaries()
            chunk_lines = [ln.strip() for ln in Path(args.stitch_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            if not chunk_lines:
                print(f"No lines found in --stitch-file: {args.stitch_file}", file=sys.stderr)
                return 1
            out_dir.mkdir(parents=True, exist_ok=True)
            prev_ids: list[str] = []
            prev_txt: str | None = None
            chunk_mp3s: list[Path] = []
            for idx, chunk in enumerate(chunk_lines):
                chunk_mp3 = out_dir / f"stitch_{idx:02d}.mp3"
                used_model, rid = synthesize_tts(
                    api_key=api_key,
                    voice_id=voice_id,
                    text=chunk,
                    model_id=model_id,
                    output_mp3=chunk_mp3,
                    language_code=args.language,
                    stability=args.stability,
                    similarity_boost=args.similarity,
                    style=args.style,
                    use_speaker_boost=speaker_boost,
                    seed=args.seed,
                    previous_request_ids=prev_ids,
                    previous_text=prev_txt,
                )
                chunk_mp3s.append(chunk_mp3)
                if rid:
                    prev_ids.append(rid)
                prev_txt = chunk
                print(f"[stitch {idx:02d}] model={used_model} rid={rid or 'none'} -> {chunk_mp3}")
            concat_txt = out_dir / "_stitch_concat.txt"
            concat_txt.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in chunk_mp3s) + "\n", encoding="utf-8")
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)],
                check=True,
            )
            concat_txt.unlink(missing_ok=True)
            audio_src = out_mp3
        else:
            text = args.text
            if not text and args.text_file:
                text = Path(args.text_file).read_text(encoding="utf-8").strip()
            if not text:
                print("Provide --text, --text-file, --stitch-file (or --audio-in for an existing MP3).", file=sys.stderr)
                return 1

            used_model, rid = synthesize_tts(
                api_key=api_key,
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_mp3=out_mp3,
                language_code=args.language,
                stability=args.stability,
                similarity_boost=args.similarity,
                style=args.style,
                use_speaker_boost=speaker_boost,
                seed=args.seed,
            )
            print(f"[tts] Generated {out_mp3} using model={used_model}, voice_id={voice_id}, request_id={rid or 'none'}")
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
