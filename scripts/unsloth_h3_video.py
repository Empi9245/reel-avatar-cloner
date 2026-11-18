"""Local Unsloth Studio / stable-diffusion.cpp CLI bridge for MiniMax-H3 Ref2VA video generation.

Supports:
1. --check : Verify all local MiniMax-H3 Ref2VA weights, VAEs, Qwen3-VL encoder, sd-cli.exe,
             DLL search paths, and optional Unsloth Studio HTTP API (127.0.0.1:8888).
2. generate: Run MiniMax-H3 Ref2VA via sd-cli.exe (--mode vid_gen) or Unsloth Studio's
             VideoBackend with reference images (--ref-image), reference voice (--ref-audio),
             optional reference video (--ref-video), automatic frame-lattice snapping (17k + 5),
             and clean H.264/AAC MP4 transcode.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

DEFAULT_HF_HUB = Path(r"D:\AI\hf\hub")
H3_REPO_DIR = DEFAULT_HF_HUB / "models--unsloth--MiniMax-H3-GGUF" / "snapshots"
UNSLOTH_SD_CPP_DIR = Path(r"C:\Users\empi0\.unsloth\stable-diffusion.cpp")
UNSLOTH_STUDIO_SITE = Path(r"D:\UnslothStudio\unsloth_studio\Lib\site-packages")
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VOICE_REF = SKILL_ROOT / "resources" / "eva_voice_master.wav"


def find_h3_snapshot() -> Optional[Path]:
    """Return the latest MiniMax-H3 GGUF snapshot directory containing all required files."""
    if not H3_REPO_DIR.is_dir():
        return None
    candidates = sorted(
        (p for p in H3_REPO_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for snap in candidates:
        if (snap / "minimax_h3_ref2va_pruned-Q3_K.gguf").is_file():
            return snap
    return candidates[0] if candidates else None


def resolve_h3_assets(snapshot_dir: Optional[Path] = None) -> dict[str, Optional[Path]]:
    """Locate MiniMax-H3 Ref2VA weights, Qwen3-VL text encoder, video/audio VAEs, and sd-cli.exe."""
    snap = snapshot_dir or find_h3_snapshot()
    sd_cli = UNSLOTH_SD_CPP_DIR / "sd-cli.exe"
    if not sd_cli.is_file():
        found = shutil.which("sd-cli")
        sd_cli = Path(found) if found else None  # type: ignore[assignment]

    def _pick(pattern: str) -> Optional[Path]:
        if snap is None or not snap.is_dir():
            return None
        matches = sorted(snap.rglob(pattern))
        return matches[0] if matches else None

    return {
        "snapshot": snap,
        "sd_cli": sd_cli if sd_cli and sd_cli.is_file() else None,
        "diffusion_model": _pick("minimax_h3_ref2va*.gguf"),
        "text_encoder": _pick("qwen3vl_*minimax_h3*.gguf"),
        "video_vae": _pick("*video_vae*.safetensors"),
        "audio_vae": _pick("*audio_vae*.safetensors"),
        "default_voice_ref": DEFAULT_VOICE_REF if DEFAULT_VOICE_REF.is_file() else None,
    }


def build_sd_cpp_env() -> dict[str, str]:
    """Ensure sd-cli.exe finds bundled stable-diffusion.cpp and Unsloth ROCm DLLs on Windows."""
    env = os.environ.copy()
    extra_dirs = [
        UNSLOTH_SD_CPP_DIR,
        UNSLOTH_STUDIO_SITE / "_rocm_sdk_libraries" / "bin",
        UNSLOTH_STUDIO_SITE / "_rocm_sdk_core" / "bin",
    ]
    existing = env.get("PATH", "")
    prepend = [str(d) for d in extra_dirs if d.is_dir()]
    if prepend:
        env["PATH"] = os.pathsep.join(prepend) + os.pathsep + existing
    return env


def probe_sd_cli_help(sd_cli: Path, env: dict[str, str]) -> str:
    """Return sd-cli --help text or empty string on failure."""
    try:
        res = subprocess.run(
            [str(sd_cli), "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        return (res.stdout or "") + "\n" + (res.stderr or "")
    except Exception:
        return ""


def probe_studio_api(url: str = "http://127.0.0.1:8888/api/system") -> dict:
    """Check whether Unsloth Studio HTTP server is reachable."""
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return {"reachable": True, "status": resp.status, "url": url}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"reachable": False, "url": url, "detail": str(exc)}


def snap_h3_frames(seconds: float, fps: int = 24, allow_short: bool = False) -> int:
    """Snap target duration onto MiniMax-H3's temporal lattice (17k + 5, valid range 124..345)."""
    target = max(1, round(seconds * fps))
    # Lattice: n = 17*k + 5 -> k = round((target - 5) / 17)
    k = max(0, round((target - 5) / 17.0))
    snapped = 17 * k + 5
    if not allow_short:
        snapped = max(124, snapped)
    return min(345, snapped)


def snap_multiple_32(val: int) -> int:
    """Snap pixel dimension down/nearest to multiple of 32 (minimum 256)."""
    return max(256, round(val / 32) * 32)


def run_check(json_out: bool = False) -> int:
    """Validate all local MiniMax-H3 assets, sd-cli execution, and Studio API reachability."""
    assets = resolve_h3_assets()
    env = build_sd_cpp_env()
    help_txt = probe_sd_cli_help(assets["sd_cli"], env) if assets["sd_cli"] else ""
    studio_status = probe_studio_api()

    required_keys = ("sd_cli", "diffusion_model", "text_encoder", "video_vae", "audio_vae")
    missing = [k for k in required_keys if assets[k] is None]
    cli_ok = bool(help_txt and "--mode" in help_txt and "--ref-image" in help_txt)

    report = {
        "ok": len(missing) == 0 and cli_ok,
        "missing": missing,
        "sd_cli_help_ok": cli_ok,
        "supports_ref_audio": "--ref-audio" in help_txt,
        "supports_audio_flow_shift": "--audio-flow-shift" in help_txt,
        "supports_lossless_video": "--lossless-video" in help_txt,
        "studio_api": studio_status,
        "assets": {k: (str(v) if v is not None else None) for k, v in assets.items()},
    }
    if json_out:
        print(json.dumps(report, indent=2))
    else:
        print("=== Unsloth Local MiniMax-H3 Ref2VA Check ===")
        for k, v in assets.items():
            mark = "OK" if v is not None else "MISSING"
            print(f"  [{mark}] {k}: {v}")
        print(f"  [{'OK' if cli_ok else 'FAIL'}] sd-cli --help vid_gen + --ref-image + --ref-audio={report['supports_ref_audio']}")
        print(f"  [INFO] Studio HTTP API ({studio_status['url']}): {'ONLINE' if studio_status['reachable'] else 'OFFLINE (sd-cli works standalone)'}")
    return 0 if report["ok"] else 1


def build_h3_command(
    assets: dict[str, Optional[Path]],
    help_txt: str,
    *,
    prompt: str,
    out_avi: Path,
    ref_images: list[Path],
    ref_audios: list[Path],
    ref_videos: list[Path],
    width: int,
    height: int,
    num_frames: int,
    fps: int,
    steps: int,
    cfg_scale: float,
    flow_shift: float,
    seed: int,
    max_vram: Optional[str],
    offload_to_cpu: bool,
) -> list[str]:
    """Construct the exact sd-cli --mode vid_gen argv verified against sd-cli --help."""
    sd_cli = assets["sd_cli"]
    assert sd_cli is not None
    cmd = [
        str(sd_cli),
        "--mode",
        "vid_gen",
        "--diffusion-model",
        str(assets["diffusion_model"]),
        "--vae",
        str(assets["video_vae"]),
        "--audio-vae",
        str(assets["audio_vae"]),
        "--llm",
        str(assets["text_encoder"]),
    ]
    for img in ref_images:
        cmd += ["--ref-image", str(img)]
    if ref_images and "--ref-image-args" in help_txt:
        cmd += ["--ref-image-args", "ref_image_size=max"]
    for vid in ref_videos:
        cmd += ["--ref-video", str(vid)]
    for aud in ref_audios:
        cmd += ["--ref-audio", str(aud)]

    cmd += [
        "--prompt",
        prompt,
        "--cfg-scale",
        f"{cfg_scale:g}",
        "--width",
        str(snap_multiple_32(width)),
        "--height",
        str(snap_multiple_32(height)),
        "--rng",
        "cpu",
        "--fps",
        str(fps),
        "--video-frames",
        str(num_frames),
        "--steps",
        str(steps),
        "--sampling-method",
        "res_multistep",
        "--scheduler",
        "simple",
        "--flow-shift",
        f"{flow_shift:g}",
        "--seed",
        str(seed),
        "--vae-tiling",
        "--output",
        str(out_avi),
    ]
    if re.search(r"(?<![\w-])--audio-flow-shift\b", help_txt):
        cmd += ["--audio-flow-shift", "3"]
    if offload_to_cpu:
        cmd.append("--offload-to-cpu")
    if max_vram:
        cmd += ["--max-vram", str(max_vram)]
    return cmd


def transcode_to_mp4(src_avi: Path, dst_mp4: Path, fps: int = 24) -> None:
    """Convert raw/MJPG AVI + audio from sd-cli into standard H.264/AAC MP4."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src_avi),
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(dst_mp4),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local Unsloth MiniMax-H3 Ref2VA CLI helper & health check"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify local MiniMax-H3 files, sd-cli.exe, and Studio status without running inference",
    )
    parser.add_argument("--json", action="store_true", help="Output --check result as JSON")
    parser.add_argument("--prompt", help="Full Ref2VA generation prompt (use <Subject 1>, Image 1, Audio 1)")
    parser.add_argument("--out", help="Output MP4 path")
    parser.add_argument("--ref-image", action="append", default=[], help="Reference image path (repeatable, up to 9)")
    parser.add_argument("--ref-audio", action="append", default=[], help="Reference WAV audio path (repeatable, up to 3)")
    parser.add_argument("--ref-video", action="append", default=[], help="Reference video 24fps frame dir (repeatable)")
    parser.add_argument("--seconds", type=float, default=5.17, help="Target clip length in seconds (snaps to 17k+5)")
    parser.add_argument("--width", type=int, default=480, help="Output width (multiple of 32; 480 recommended for 9:16 on 8GB GPU)")
    parser.add_argument("--height", type=int, default=864, help="Output height (multiple of 32; 864 recommended for 9:16 on 8GB GPU)")
    parser.add_argument("--steps", type=int, default=20, help="Denoising steps (default 20)")
    parser.add_argument("--cfg-scale", type=float, default=1.0, help="Guidance scale (default 1.0)")
    parser.add_argument("--flow-shift", type=float, default=12.0, help="Flow shift (default 12.0)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-vram", default="-1", help="Per-device --max-vram passed to sd-cli (default -1 auto reserve)")
    parser.add_argument("--no-offload", action="store_true", help="Disable --offload-to-cpu")
    parser.add_argument("--dry-run", action="store_true", help="Print the exact sd-cli command without running it")
    args = parser.parse_args()

    if args.check:
        sys.exit(run_check(json_out=args.json))

    if not args.prompt or not args.out:
        parser.error("Provide --check OR both --prompt and --out")

    assets = resolve_h3_assets()
    missing = [k for k in ("sd_cli", "diffusion_model", "text_encoder", "video_vae", "audio_vae") if assets[k] is None]
    if missing:
        raise SystemExit(f"Missing MiniMax-H3 local assets: {missing}")

    env = build_sd_cpp_env()
    help_txt = probe_sd_cli_help(assets["sd_cli"], env)  # type: ignore[arg-type]

    out_mp4 = Path(args.out).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    out_avi = out_mp4.with_suffix(".avi")

    num_frames = snap_h3_frames(args.seconds, fps=24)
    ref_images = [Path(p).resolve() for p in args.ref_image]
    ref_audios = [Path(p).resolve() for p in args.ref_audio]
    ref_videos = [Path(p).resolve() for p in args.ref_video]

    cmd = build_h3_command(
        assets,
        help_txt,
        prompt=args.prompt,
        out_avi=out_avi,
        ref_images=ref_images,
        ref_audios=ref_audios,
        ref_videos=ref_videos,
        width=args.width,
        height=args.height,
        num_frames=num_frames,
        fps=24,
        steps=args.steps,
        cfg_scale=args.cfg_scale,
        flow_shift=args.flow_shift,
        seed=args.seed,
        max_vram=args.max_vram,
        offload_to_cpu=not args.no_offload,
    )

    print(f"Target frames: {num_frames} ({num_frames / 24.0:.2f}s @ 24fps) | Canvas: {snap_multiple_32(args.width)}x{snap_multiple_32(args.height)}")
    print("CMD:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    if args.dry_run:
        return

    res = subprocess.run(cmd, env=env)
    if res.returncode != 0:
        raise SystemExit(f"sd-cli exited with code {res.returncode}")
    transcode_to_mp4(out_avi, out_mp4, fps=24)
    print(f"Saved MP4 -> {out_mp4}")


if __name__ == "__main__":
    main()
