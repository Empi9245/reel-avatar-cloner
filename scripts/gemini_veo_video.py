"""Direct Gemini API (Veo) video generator via official REST endpoints (zero browser automation).

Note: Uses pay-per-use GEMINI_API_KEY / GOOGLE_API_KEY from Google AI Studio (separate from
Google Flow web subscription credits and Omni 1.2 Flash).
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_VEO_MODEL = "veo-3.0-generate-preview"
PLACEHOLDER_VALUES = {"", "your_gemini_api_key_here", "changeme", "replace_me"}


def find_dotenv(explicit_path: str | None = None) -> Path | None:
    """Locate a .env file from explicit path, CWD parents, or script parents."""
    if explicit_path:
        candidate = Path(explicit_path).expanduser().resolve()
        return candidate if candidate.is_file() else None
    seen: set[Path] = set()
    for root in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for parent in (root, *root.parents):
            if parent in seen:
                continue
            seen.add(parent)
            env_file = parent / ".env"
            if env_file.is_file():
                return env_file
    return None


def load_dotenv(env_path: Path | None) -> dict[str, str]:
    """Parse simple KEY=VALUE lines from .env."""
    loaded: dict[str, str] = {}
    if env_path is None or not env_path.is_file():
        return loaded
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, val = line.split("=", 1)
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        loaded[key.strip()] = val
    return loaded


def resolve_api_key(args: argparse.Namespace) -> tuple[str, Path | None]:
    """Resolve GEMINI_API_KEY or GOOGLE_API_KEY from CLI, env, or .env."""
    env_path = find_dotenv(args.env)
    dotenv_vars = load_dotenv(env_path)
    for var_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = (args.api_key or os.environ.get(var_name) or dotenv_vars.get(var_name) or "").strip()
        if val and val.lower() not in PLACEHOLDER_VALUES:
            return val, env_path
    return "", env_path


def _api_request(url: str, api_key: str, payload: dict | None = None) -> dict:
    headers = {"x-goog-api-key": api_key, "Accept": "application/json"}
    data = None
    method = "GET"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini API error {exc.code}: {err_body}") from exc


def generate_veo_video(
    *,
    api_key: str,
    model: str,
    prompt: str,
    out_mp4: Path,
    image_path: Path | None = None,
    aspect_ratio: str = "9:16",
    duration_seconds: int | None = None,
    poll_interval_s: float = 10.0,
) -> Path:
    """Start a Veo predictLongRunning job, poll until done, and download the generated MP4."""
    instance: dict = {"prompt": prompt}
    if image_path is not None:
        if not image_path.is_file():
            raise FileNotFoundError(f"Start frame image not found: {image_path}")
        mime, _ = mimetypes.guess_type(str(image_path))
        instance["image"] = {
            "bytesBase64Encoded": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            "mimeType": mime or "image/png",
        }

    parameters: dict = {"aspectRatio": aspect_ratio}
    if duration_seconds is not None:
        parameters["durationSeconds"] = int(duration_seconds)

    start_url = f"{GEMINI_BASE_URL}/models/{model}:predictLongRunning"
    op = _api_request(start_url, api_key, {"instances": [instance], "parameters": parameters})
    op_name = op.get("name")
    if not op_name:
        raise RuntimeError(f"Unexpected predictLongRunning response: {op}")
    print(f"[veo] Operation started: {op_name}")

    while not op.get("done"):
        time.sleep(poll_interval_s)
        op = _api_request(f"{GEMINI_BASE_URL}/{op_name}", api_key)
        print("[veo] Waiting for render...", flush=True)

    if "error" in op:
        raise RuntimeError(f"Veo generation failed: {op['error']}")

    resp = op.get("response") or {}
    gen_resp = resp.get("generateVideoResponse") or {}
    samples = gen_resp.get("generatedSamples") or resp.get("generatedVideos") or []
    if not samples:
        raise RuntimeError(f"No video samples in Gemini API response: {json.dumps(op)[:800]}")

    video_uri = (samples[0].get("video") or {}).get("uri")
    if not video_uri:
        raise RuntimeError(f"Missing video URI in sample: {samples[0]}")

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(video_uri, headers={"x-goog-api-key": api_key}, method="GET")
    with urllib.request.urlopen(req, timeout=180) as dl:
        out_mp4.write_bytes(dl.read())
    return out_mp4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct Gemini API (Veo) video generator CLI")
    parser.add_argument("--check-env", action="store_true", help="Check GEMINI_API_KEY / GOOGLE_API_KEY and exit")
    parser.add_argument("--env", help="Explicit .env file path")
    parser.add_argument("--api-key", help="Override GEMINI_API_KEY")
    parser.add_argument("--model", default=DEFAULT_VEO_MODEL, help=f"Veo model ID (default: {DEFAULT_VEO_MODEL})")
    parser.add_argument("--prompt", help="Video generation prompt")
    parser.add_argument("--image", help="Optional Start Frame image path (e.g. master_muro_grigio.png)")
    parser.add_argument("--aspect-ratio", default="9:16", help="Aspect ratio (default: 9:16)")
    parser.add_argument("--duration-seconds", type=int, help="Optional clip length in seconds (e.g. 5, 6, 8)")
    parser.add_argument("--out", help="Output MP4 path")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    api_key, env_path = resolve_api_key(args)

    if args.check_env:
        print(f"dotenv_path={env_path or 'not found'}")
        print(f"GEMINI_API_KEY={'SET' if api_key else 'MISSING'}")
        print(f"DEFAULT_VEO_MODEL={DEFAULT_VEO_MODEL}")
        return 0 if api_key else 2

    if not api_key:
        print(
            "MISSING CREDENTIALS: Set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env or environment.",
            file=sys.stderr,
        )
        return 2
    if not args.prompt or not args.out:
        parser.error("Provide --check-env OR both --prompt and --out")

    saved = generate_veo_video(
        api_key=api_key,
        model=args.model,
        prompt=args.prompt,
        out_mp4=Path(args.out).expanduser().resolve(),
        image_path=Path(args.image).expanduser().resolve() if args.image else None,
        aspect_ratio=args.aspect_ratio,
        duration_seconds=args.duration_seconds,
    )
    print(f"[veo] Saved MP4 -> {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
