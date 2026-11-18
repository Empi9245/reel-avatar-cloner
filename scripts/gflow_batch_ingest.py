"""Project-agnostic Google Flow & @Eva post-production utility for reel-avatar-cloner.

Subcommands:
  check            Verify gflow-cli auth session and Google Flow credits balance ($0 cost)
  trim             Trim leading/trailing silence (sample-accurate A/V) or concat split takes
  grade            Normalize LAB luminance/white balance & midtone gamma=1.10 (fixes "accesi" Flow outputs at $0 cost)
  popout-pip       Render 1036x850 true-alpha VP9 WebM (yuva420p) 3D pop-out PIP clip for Remotion <OffthreadVideo transparent />
  gen-room-anchor  Generate a face-locked Room B reference PNG via i2i relighting (Change-One-Variable rule)
  pick-anchor      Extract the sharpest relaxed-mouth, hand-free master anchor PNG from a generated video clip
  match-audio      Match clip vocal spectrum (highpass + 8-band EQ + acompressor + 2-pass -14 LUFS) to golden voice
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import cv2
import numpy as np

DEFAULT_CANONICAL_ANCHOR = Path(__file__).resolve().parent.parent / "resources" / "eva_canonical_warm_armadio.png"


def find_gflow_bin() -> str:
    """Locate gflow executable on PATH or uv's default Windows bin directory."""
    found = shutil.which("gflow")
    if found:
        return found
    uv_bin = Path.home() / ".local" / "bin" / ("gflow.exe" if os.name == "nt" else "gflow")
    if uv_bin.is_file():
        return str(uv_bin)
    raise FileNotFoundError("gflow executable not found. Install via: uv tool install gflow-cli")


def ffprobe_duration(path: str) -> float:
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nk=1:nw=1",
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(res.stdout.strip())


def has_audio(path: str) -> bool:
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(res.stdout.strip())


def measure_adaptive_silence_threshold(path: str, fallback: str = "-32dB") -> str:
    """Measure EBU R128 adaptive gating threshold (loudnorm input_thresh) with safe fallback."""
    if not has_audio(path):
        return fallback
    try:
        res = subprocess.run(
            [
                "ffmpeg",
                "-i",
                path,
                "-map",
                "0:a",
                "-af",
                "loudnorm=print_format=json",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        m = re.search(r"\{[^{}]*\"input_thresh\"[^{}]*\}", res.stderr, re.DOTALL)
        if not m:
            return fallback
        data = json.loads(m.group(0))
        thresh = float(data["input_thresh"])
        if not math.isfinite(thresh):
            return fallback
        thresh = max(-65.0, min(-15.0, thresh))
        return f"{thresh:.2f}dB"
    except Exception:
        return fallback


def detect_speech_bounds(
    path: str,
    *,
    pad_start: float = 0.07,
    pad_end: float = 0.09,
    noise_db: str = "-32dB",
    min_silence_dur: float = 0.12,
    adaptive_loudnorm: bool = False,
) -> tuple[float, float, float]:
    """Return (speech_start, speech_end, total_dur) using ffmpeg silencedetect."""
    total_dur = ffprobe_duration(path)
    if not has_audio(path):
        return 0.0, total_dur, total_dur

    eff_noise = measure_adaptive_silence_threshold(path, fallback=noise_db) if adaptive_loudnorm else noise_db
    res = subprocess.run(
        [
            "ffmpeg",
            "-i",
            path,
            "-af",
            f"silencedetect=noise={eff_noise}:d={min_silence_dur}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    events = re.findall(r"silence_(start|end):\s*([0-9.]+)", res.stderr)
    parsed = [(kind, float(ts)) for kind, ts in events]

    start_s = 0.0
    end_s = total_dur

    if len(parsed) >= 2 and parsed[0][0] == "start" and parsed[0][1] <= 0.08 and parsed[1][0] == "end":
        start_s = max(0.0, parsed[1][1] - pad_start)

    if len(parsed) >= 2 and parsed[-2][0] == "start" and parsed[-1][0] == "end":
        if abs(parsed[-1][1] - total_dur) <= 0.08 and parsed[-2][1] > start_s + 0.4:
            end_s = min(total_dur, parsed[-2][1] + pad_end)
    elif parsed and parsed[-1][0] == "start" and parsed[-1][1] > start_s + 0.4:
        end_s = min(total_dur, parsed[-1][1] + pad_end)

    if end_s - start_s < 0.5:
        return 0.0, total_dur, total_dur
    return start_s, end_s, total_dur


def trim_clip_to_speech(
    src_mp4: str,
    out_mp4: str,
    *,
    pad_start: float = 0.07,
    pad_end: float = 0.09,
    noise_db: str = "-32dB",
    adaptive_loudnorm: bool = False,
) -> float:
    """Trim leading/trailing silence sample-accurately on both video and audio streams."""
    start_s, end_s, total_dur = detect_speech_bounds(
        src_mp4,
        pad_start=pad_start,
        pad_end=pad_end,
        noise_db=noise_db,
        adaptive_loudnorm=adaptive_loudnorm,
    )
    if start_s <= 0.02 and (total_dur - end_s) <= 0.02:
        shutil.copy2(src_mp4, out_mp4)
        return total_dur

    if has_audio(src_mp4):
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            src_mp4,
            "-filter_complex",
            (
                f"[0:v]trim=start={start_s:.4f}:end={end_s:.4f},setpts=PTS-STARTPTS[v];"
                f"[0:a]atrim=start={start_s:.4f}:end={end_s:.4f},asetpts=PTS-STARTPTS[a]"
            ),
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "14",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "192k",
            out_mp4,
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            src_mp4,
            "-vf",
            f"trim=start={start_s:.4f}:end={end_s:.4f},setpts=PTS-STARTPTS",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "14",
            "-pix_fmt",
            "yuv420p",
            out_mp4,
        ]
    subprocess.run(cmd, check=True, capture_output=True)
    return ffprobe_duration(out_mp4)


def _compute_video_lab_stats(video_path: str, sample_frames: int = 12) -> tuple[np.ndarray, np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    total = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    indices = np.linspace(0, total - 1, min(sample_frames, total), dtype=int)
    labs = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, bgr = cap.read()
        if ok and bgr is not None:
            labs.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32))
    cap.release()
    stacked = np.concatenate([x.reshape(-1, 3) for x in labs], axis=0)
    return stacked.mean(axis=0), np.maximum(stacked.std(axis=0), 1e-3)


def apply_lab_color_match(
    src_mp4: str,
    out_mp4: str,
    *,
    room: str = "light-wall",
    target_l: float | None = None,
    gamma: float = 1.10,
) -> None:
    """Fix washed-out/bright ('accesi') Flow clips in LAB space + midtone gamma pull at $0 cost."""
    if room == "warm-wood":
        mean_l = target_l if target_l is not None else 100.0
        target_mean = np.array([mean_l, 133.4, 141.8], dtype=np.float32)
        target_std = np.array([50.0, 7.5, 11.0], dtype=np.float32)
    else:
        mean_l = target_l if target_l is not None else 104.0
        target_mean = np.array([mean_l, 130.2, 134.3], dtype=np.float32)
        target_std = np.array([52.0, 6.5, 9.5], dtype=np.float32)

    src_mean, src_std = _compute_video_lab_stats(src_mp4)
    scale = np.clip(target_std / src_std, 0.88, 1.12)
    strength_vec = np.array([0.70, 0.75, 0.75], dtype=np.float32)
    eff_mean = src_mean * (1.0 - strength_vec) + target_mean * strength_vec
    eff_scale = 1.0 * (1.0 - strength_vec) + scale * strength_vec

    cap = cv2.VideoCapture(src_mp4)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    video_only = out_mp4 + ".vid.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{w}x{h}",
        "-r",
        f"{fps:.6f}",
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "15",
        "-pix_fmt",
        "yuv420p",
        "-an",
        video_only,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdin is not None
    while True:
        ok, fr = cap.read()
        if not ok or fr is None:
            break
        lab = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB).astype(np.float32)
        matched = np.clip((lab - src_mean) * eff_scale + eff_mean, 0, 255)
        matched[:, :, 0] = np.clip(255.0 * ((matched[:, :, 0] / 255.0) ** gamma), 0, 255)
        proc.stdin.write(cv2.cvtColor(matched.astype(np.uint8), cv2.COLOR_LAB2BGR).tobytes())
    cap.release()
    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg LAB color encode failed for {src_mp4} (rc={rc})")

    if has_audio(src_mp4):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_only,
                "-i",
                src_mp4,
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                out_mp4,
            ],
            check=True,
            capture_output=True,
        )
        os.remove(video_only)
    else:
        os.replace(video_only, out_mp4)


def render_popout_pip_frame(
    fr: np.ndarray,
    *,
    width: int = 1036,
    height: int = 850,
    card_top: int = 136,
    radius: int = 165,
    scale_w: int = 720,
    scale_h: int = 1280,
    y_offset: int = 42,
) -> np.ndarray:
    """Render BGRA 3D pop-out PIP frame: chest-up + shoulders/hands inside rounded card + keyed hair above card_top."""
    scaled = cv2.resize(fr, (scale_w, scale_h), interpolation=cv2.INTER_LANCZOS4)
    top_wall_bgr = cv2.GaussianBlur(
        np.median(scaled[:14, :, :], axis=0).astype(np.uint8)[None, :, :], (25, 1), 0
    )

    y0 = max(0, min(scale_h - height, y_offset))
    crop = scaled[y0 : y0 + height, :]
    x0 = (width - scale_w) // 2

    left_edge = np.median(crop[:, :10, :], axis=1).astype(np.float32)
    right_edge = np.median(crop[:, -10:, :], axis=1).astype(np.float32)
    left_edge = cv2.GaussianBlur(left_edge[:, None, :], (1, 35), 0)[:, 0, :].astype(np.uint8)
    right_edge = cv2.GaussianBlur(right_edge[:, None, :], (1, 35), 0)[:, 0, :].astype(np.uint8)

    full_room = np.zeros((height, width, 3), dtype=np.uint8)
    full_room[:, :x0, :] = left_edge[:, None, :]
    full_room[:, x0 + scale_w :, :] = right_edge[:, None, :]
    full_room[:, x0 : x0 + scale_w, :] = crop

    feather = 26
    for dx in range(feather):
        a = dx / float(feather)
        full_room[:, x0 + dx, :] = (left_edge * (1.0 - a) + crop[:, dx, :] * a).astype(np.uint8)
        full_room[:, x0 + scale_w - 1 - dx, :] = (
            right_edge * (1.0 - a) + crop[:, scale_w - 1 - dx, :] * a
        ).astype(np.uint8)

    card_mask = np.zeros((height, width), dtype=np.float32)
    card_mask[card_top:, :] = 1.0
    card_mask[card_top : card_top + radius, :radius] = 0.0
    card_mask[card_top : card_top + radius, width - radius :] = 0.0
    yy, xx = np.ogrid[:radius, :radius]
    card_mask[card_top : card_top + radius, :radius] = np.clip(
        radius + 0.5 - np.sqrt((xx - radius) ** 2 + (yy - radius) ** 2), 0.0, 1.0
    )
    card_mask[card_top : card_top + radius, width - radius :] = np.clip(
        radius + 0.5 - np.sqrt(xx**2 + (yy - radius) ** 2), 0.0, 1.0
    )

    full_wall_row = np.zeros((1, width, 3), dtype=np.uint8)
    full_wall_row[0, :x0, :] = top_wall_bgr[0, 0, :]
    full_wall_row[0, x0 : x0 + scale_w, :] = top_wall_bgr[0, :, :]
    full_wall_row[0, x0 + scale_w :, :] = top_wall_bgr[0, -1, :]
    full_wall_lab = cv2.cvtColor(full_wall_row, cv2.COLOR_BGR2LAB).astype(np.float32)

    top_h = card_top + 45
    top_lab = cv2.cvtColor(full_room[:top_h, :, :], cv2.COLOR_BGR2LAB).astype(np.float32)
    score = (
        np.maximum(0.0, full_wall_lab[:, :, 0] - top_lab[:, :, 0])
        + np.sqrt(
            (top_lab[:, :, 1] - full_wall_lab[:, :, 1]) ** 2
            + (top_lab[:, :, 2] - full_wall_lab[:, :, 2]) ** 2
        )
        * 1.9
    )
    raw_hair = np.clip((score - 16.0) / 14.0, 0.0, 1.0)
    binary = (raw_hair > 0.15).astype(np.uint8)
    binary[:, : x0 + 60] = 0
    binary[:, x0 + scale_w - 60 :] = 0
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    keep = np.zeros_like(binary, dtype=np.float32)
    seed_label = labels[card_top, width // 2]
    for lbl in range(1, num_labels):
        if lbl == seed_label or (
            stats[lbl, cv2.CC_STAT_AREA] > 80
            and stats[lbl, cv2.CC_STAT_TOP] + stats[lbl, cv2.CC_STAT_HEIGHT] >= card_top - 25
        ):
            keep[labels == lbl] = 1.0
    keep = cv2.dilate(keep, np.ones((3, 3), np.uint8), iterations=1)
    head_mask = np.zeros((height, width), dtype=np.float32)
    head_mask[:top_h, :] = cv2.GaussianBlur(raw_hair * keep, (3, 3), 0)

    fg = full_room.astype(np.float32)
    pop = (card_mask < 0.5) & (head_mask > 0.01)
    fg[pop] = np.minimum(
        fg[pop], fg[pop] * 0.65 + np.array([34.0, 46.0, 62.0], dtype=np.float32) * 0.35
    )

    bgr_u8 = np.clip(fg, 0, 255).astype(np.uint8)
    alpha_u8 = np.clip(np.maximum(card_mask, head_mask) * 255.0, 0, 255).astype(np.uint8)
    return np.dstack([bgr_u8, alpha_u8])


def export_popout_webm(
    src_mp4: str,
    out_webm: str,
    *,
    start_s: float = 0.0,
    dur_s: float | None = None,
    fps: int = 30,
    y_offset: int = 42,
) -> int:
    """Slice src_mp4 and encode 1036x850 VP9 yuva420p (alpha_mode=1) WebM for Remotion <OffthreadVideo transparent />."""
    total_dur = ffprobe_duration(src_mp4)
    eff_dur = dur_s if dur_s is not None else max(0.1, total_dur - start_s)
    slice_tmp = out_webm + ".slice.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start_s:.4f}",
            "-i",
            src_mp4,
            "-t",
            f"{eff_dur:.4f}",
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "12",
            "-an",
            slice_tmp,
        ],
        check=True,
        capture_output=True,
    )

    cap = cv2.VideoCapture(slice_tmp)
    W, H = 1036, 850
    target_frames = max(1, int(round(eff_dur * fps)))
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "bgra",
        "-s",
        f"{W}x{H}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        "-b:v",
        "2M",
        "-crf",
        "18",
        "-row-mt",
        "1",
        "-speed",
        "2",
        "-auto-alt-ref",
        "0",
        "-an",
        out_webm,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdin is not None
    written = 0
    last_out: np.ndarray | None = None
    while written < target_frames:
        ok, fr = cap.read()
        if not ok or fr is None:
            break
        last_out = render_popout_pip_frame(fr, y_offset=y_offset)
        proc.stdin.write(last_out.tobytes())
        written += 1
    while written < target_frames and last_out is not None:
        proc.stdin.write(last_out.tobytes())
        written += 1
    cap.release()
    proc.stdin.close()
    rc = proc.wait()
    if os.path.exists(slice_tmp):
        os.remove(slice_tmp)
    if rc != 0:
        raise RuntimeError(f"ffmpeg alpha WebM encode failed for {out_webm} (rc={rc})")
    return written


def _detect_portrait_face(bgr: np.ndarray) -> tuple[int, int, int, int]:
    """Locate primary central face box (x, y, w, h) via YCrCb skin segmentation (headless OpenCV safe)."""
    h, w = bgr.shape[:2]
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y0, y1 = int(0.14 * h), int(0.66 * h)
    x0, x1 = int(0.20 * w), int(0.80 * w)
    roi = ycrcb[y0:y1, x0:x1]
    skin = (
        (roi[:, :, 0] > 55)
        & (roi[:, :, 1] >= 134)
        & (roi[:, :, 1] <= 174)
        & (roi[:, :, 2] >= 78)
        & (roi[:, :, 2] <= 128)
    ).astype(np.uint8)
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    skin = cv2.morphologyEx(skin, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n_lbl, _, stats, centroids = cv2.connectedComponentsWithStats(skin, connectivity=8)
    best_idx = -1
    best_area = 0
    for lbl in range(1, n_lbl):
        area = int(stats[lbl, cv2.CC_STAT_AREA])
        cx_rel = float(centroids[lbl][0]) / max(1.0, float(x1 - x0))
        if area > best_area and 0.15 <= cx_rel <= 0.85:
            best_area = area
            best_idx = lbl
    if best_idx > 0 and best_area > int(0.015 * h * w):
        bx = x0 + int(stats[best_idx, cv2.CC_STAT_LEFT])
        by = y0 + int(stats[best_idx, cv2.CC_STAT_TOP])
        bw = int(stats[best_idx, cv2.CC_STAT_WIDTH])
        bh = min(int(stats[best_idx, cv2.CC_STAT_HEIGHT]), int(bw * 1.25))
        return bx, by, bw, max(bw, bh)
    return int(w * 0.28), int(h * 0.24), int(w * 0.44), int(h * 0.28)


ROOM_PRESET_DESCRIPTIONS = {
    "grey-plaster": (
        "Clean matte pale-grey interior plaster bedroom wall with a vertical wall corner seam on the camera-right "
        "third, soft cool overcast natural indoor window daylight coming from camera-left onto her face and hair, "
        "removing the yellow wall and wooden wardrobe completely"
    ),
    "warm-cream": (
        "Soft neutral-warm plastered apartment wall with diffused indoor daylight and subtle corner shadow falloff, "
        "clean minimalist room background with no furniture clutter"
    ),
    "modern-office": (
        "Minimalist neutral-toned creative studio wall in soft natural indoor daylight with subtle shallow depth blur, "
        "no bright neon lights, keeping authentic smartphone UGC lighting"
    ),
}


def build_room_anchor_prompt(room_preset: str = "grey-plaster", room_desc: str | None = None) -> str:
    """Build a Stills-First Change-One-Variable + Relight prompt keeping exact character identity."""
    env = (room_desc or ROOM_PRESET_DESCRIPTIONS[room_preset]).strip()
    return (
        "Exact same person from the attached reference photo (100% identical facial structure, nose, eyebrows, "
        "chin, ear shape, light skin freckles, small cheek beauty mark under left eye, relaxed closed-mouth serene "
        "expression, high messy dark-brown bun hairstyle with loose wispy face-framing curls, round tortoiseshell "
        "eyeglasses, matte charcoal-black crew-neck cotton t-shirt, and delicate thin gold necklace). "
        "Identical 9:16 arm's-length smartphone front-camera chest-up framing, focal length (~24mm), and camera height "
        "with 15% clean wall headroom above her hair bun. "
        f"Change ONLY the room background and ambient room light to: {env}. "
        "Natural soft environmental daylight wraps subtly around her hair strands, tortoiseshell frame, and shoulders "
        "so the portrait belongs naturally to the new room with authentic smartphone grain, zero studio gloss, zero "
        "airbrushing, zero jewelry changes, zero extra props or text."
    )


def gen_room_anchor(
    src_path: str,
    out_path: str,
    *,
    room_preset: str = "grey-plaster",
    room_desc: str | None = None,
    model: str = "nano2",
    project: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Generate a face-locked Room B still anchor via gflow image i2i using Stills-First relighting."""
    src = Path(src_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Canonical anchor image not found: {src}")
    out = Path(out_path).expanduser().resolve()
    prompt = build_room_anchor_prompt(room_preset=room_preset, room_desc=room_desc)
    gflow = find_gflow_bin()
    cmd = [
        gflow,
        "image",
        "i2i",
        prompt,
        "--ref",
        str(src),
        "--model",
        model,
        "--aspect",
        "9:16",
        "-n",
        "1",
        "--out-file",
        str(out),
    ]
    if project:
        cmd += ["--project", project]
    if dry_run:
        return cmd
    out.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise RuntimeError(f"gflow image i2i failed with exit code {res.returncode}")
    return cmd


def pick_neutral_anchor(
    video_path: str,
    out_png: str,
    *,
    max_samples: int = 45,
) -> tuple[float, float]:
    """Scan generated MP4 and extract the sharpest relaxed closed-mouth, hand-free anchor PNG."""
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if total <= 0:
        cap.release()
        raise RuntimeError(f"Could not read frames from {video_path}")

    lo = 0
    hi = max(1, total - 1)
    indices = np.unique(np.linspace(lo, hi, min(max(max_samples, 60), total), dtype=int))

    best_score = -1e9
    best_frame: np.ndarray | None = None
    best_ts = 0.0

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, fr = cap.read()
        if not ok or fr is None:
            continue
        h, w = fr.shape[:2]
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        fx, fy, fw, fh = _detect_portrait_face(fr)

        face_gray = gray[fy : fy + fh, fx : fx + fw]
        sharpness = float(cv2.Laplacian(face_gray, cv2.CV_64F).var()) if face_gray.size else 0.0

        # Mouth closed / relaxed score: penalize visible bright teeth and dark open mouth interior
        m_y0, m_y1 = fy + int(0.65 * fh), min(h, fy + int(0.84 * fh))
        m_x0, m_x1 = fx + int(0.32 * fw), min(w, fx + int(0.68 * fw))
        mouth = gray[m_y0:m_y1, m_x0:m_x1]
        if mouth.size:
            bright_teeth = float(np.mean(mouth > 168))
            dark_cavity = float(np.mean(mouth < 65))
            teeth_penalty = bright_teeth * 600.0 + dark_cavity * 450.0 + float(np.std(mouth)) * 1.8
        else:
            teeth_penalty = 80.0

        # Lower chest ROI check for hands/arms blocking t-shirt & necklace
        torso = fr[int(0.72 * h) :, int(0.15 * w) : int(0.85 * w)]
        ycrcb = cv2.cvtColor(torso, cv2.COLOR_BGR2YCrCb)
        skin_mask = (ycrcb[:, :, 1] > 135) & (ycrcb[:, :, 1] < 173) & (ycrcb[:, :, 2] > 80) & (ycrcb[:, :, 2] < 126)
        hand_penalty = float(np.mean(skin_mask) * 320.0)

        score = sharpness * 0.35 - teeth_penalty - hand_penalty
        if score > best_score:
            best_score = score
            best_frame = fr
            best_ts = float(idx) / float(fps)

    cap.release()
    if best_frame is None:
        raise RuntimeError(f"Failed to pick anchor frame from {video_path}")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out_png, best_frame)
    return best_ts, best_score


def _extract_mono_wav_48k(media_path: str, out_wav: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", media_path, "-vn", "-ac", "1", "-ar", "48000", "-acodec", "pcm_s16le", out_wav],
        check=True,
    )


def _voiced_band_energies_db(wav_path: str, centers_hz: list[float]) -> np.ndarray:
    """Measure average vocal energy across 8 frequency bands on voiced frames (stdlib wave + numpy)."""
    with wave.open(wav_path, "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    n_fft = 2048
    hop = 1024
    if len(samples) < n_fft:
        return np.zeros(len(centers_hz), dtype=np.float32)
    win = np.hanning(n_fft).astype(np.float32)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
    frames = [samples[i : i + n_fft] for i in range(0, len(samples) - n_fft + 1, hop)]
    rms = np.array([math.sqrt(float(np.mean(fr * fr)) + 1e-12) for fr in frames])
    thresh = max(1e-4, float(np.max(rms)) * 0.08)
    mags = [np.abs(np.fft.rfft(fr * win)) for fr, r in zip(frames, rms) if r >= thresh]
    if not mags:
        mags = [np.abs(np.fft.rfft(frames[0] * win))]
    mean_mag = np.mean(mags, axis=0) + 1e-8

    band_db: list[float] = []
    for fc in centers_hz:
        lo = fc / 1.38
        hi = fc * 1.38
        sel = (freqs >= lo) & (freqs <= hi)
        energy = float(np.mean(mean_mag[sel])) if np.any(sel) else 1e-8
        band_db.append(20.0 * math.log10(max(1e-8, energy)))
    return np.array(band_db, dtype=np.float32)


def match_audio_spectrum(
    src_media: str,
    ref_media: str,
    out_media: str,
    *,
    target_lufs: float = -14.0,
) -> dict[str, float]:
    """Match vocal spectral envelope (8-band EQ) + EBU R128 loudness of src_media to ref_media."""
    if not has_audio(src_media):
        raise RuntimeError(f"Input file has no audio stream: {src_media}")
    if not has_audio(ref_media):
        raise RuntimeError(f"Reference file has no audio stream: {ref_media}")

    centers = [120.0, 240.0, 480.0, 960.0, 1920.0, 3200.0, 5200.0, 8200.0]
    with tempfile.TemporaryDirectory() as tmp:
        src_wav = os.path.join(tmp, "src.wav")
        ref_wav = os.path.join(tmp, "ref.wav")
        _extract_mono_wav_48k(src_media, src_wav)
        _extract_mono_wav_48k(ref_media, ref_wav)
        src_db = _voiced_band_energies_db(src_wav, centers)
        ref_db = _voiced_band_energies_db(ref_wav, centers)

    src_db = src_db - float(np.mean(src_db))
    ref_db = ref_db - float(np.mean(ref_db))
    gains = np.clip((ref_db - src_db) * 0.72, -4.5, 4.5)

    eq_parts = ["highpass=f=80"]
    for fc, g in zip(centers, gains):
        eq_parts.append(f"equalizer=f={int(fc)}:t=q:w=1.2:g={float(g):.2f}")
    eq_parts.append("acompressor=threshold=-18dB:ratio=2.5:attack=5:release=60")
    eq_chain = ",".join(eq_parts)

    # 2-pass loudnorm measurement after spectral EQ
    probe_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src_media,
        "-af",
        f"{eq_chain},loudnorm=I={target_lufs:.1f}:TP=-1.5:LRA=7:print_format=json",
        "-f",
        "null",
        "-",
    ]
    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", probe_res.stderr, re.DOTALL)
    if m:
        ln = json.loads(m.group(0))
        norm_filter = (
            f"{eq_chain},"
            f"loudnorm=I={target_lufs:.1f}:TP=-1.5:LRA=7:"
            f"measured_I={ln['input_i']}:measured_LRA={ln['input_lra']}:"
            f"measured_TP={ln['input_tp']}:measured_thresh={ln['input_thresh']}:linear=true"
        )
    else:
        norm_filter = f"{eq_chain},loudnorm=I={target_lufs:.1f}:TP=-1.5:LRA=7"

    Path(out_media).parent.mkdir(parents=True, exist_ok=True)
    is_video = Path(src_media).suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src_media, "-af", norm_filter]
    if is_video and Path(out_media).suffix.lower() in {".mp4", ".mov", ".mkv"}:
        cmd += ["-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-movflags", "+faststart", out_media]
    else:
        cmd += ["-ar", "48000", out_media]
    subprocess.run(cmd, check=True)
    return {str(int(fc)): round(float(g), 2) for fc, g in zip(centers, gains)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Google Flow & @Eva post-production toolkit")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Check gflow-cli auth session and remaining Google Flow credits")

    p_trim = sub.add_parser("trim", help="Sample-accurate silence trimming on an MP4 clip")
    p_trim.add_argument("input", help="Input MP4 path")
    p_trim.add_argument("--out", required=True, help="Output trimmed MP4 path")
    p_trim.add_argument("--pad-start", type=float, default=0.07)
    p_trim.add_argument("--pad-end", type=float, default=0.09)
    p_trim.add_argument(
        "--adaptive-loudnorm",
        action="store_true",
        help="Use 2-pass EBU R128 loudnorm input_thresh as adaptive silence noise threshold (fallback -32dB)",
    )

    p_grade = sub.add_parser("grade", help="Fix over-bright ('accesi') Flow clips via LAB + gamma=1.10")
    p_grade.add_argument("input", help="Input MP4 path")
    p_grade.add_argument("--out", required=True, help="Output graded MP4 path")
    p_grade.add_argument("--room", choices=["light-wall", "warm-wood"], default="light-wall")
    p_grade.add_argument("--target-l", type=float, default=None)
    p_grade.add_argument("--gamma", type=float, default=1.10)

    p_pip = sub.add_parser("popout-pip", help="Render 1036x850 VP9 yuva420p alpha 3D pop-out PIP WebM")
    p_pip.add_argument("input", help="Input 9:16 MP4 clip")
    p_pip.add_argument("--out", required=True, help="Output .webm path (yuva420p alpha_mode=1)")
    p_pip.add_argument("--start", type=float, default=0.0, help="Start offset in seconds")
    p_pip.add_argument("--duration", type=float, default=None, help="Duration in seconds")
    p_pip.add_argument("--y-offset", type=int, default=42, help="Vertical crop offset inside 720x1280")

    p_room = sub.add_parser(
        "gen-room-anchor",
        help="Generate face-locked Room B reference PNG via i2i relighting (Stills-First rule)",
    )
    p_room.add_argument(
        "input",
        nargs="?",
        default=str(DEFAULT_CANONICAL_ANCHOR),
        help="Canonical avatar portrait PNG (defaults to resources/eva_canonical_warm_armadio.png)",
    )
    p_room.add_argument("--out", required=True, help="Output room-locked PNG anchor path")
    p_room.add_argument("--room-preset", choices=["grey-plaster", "warm-cream", "modern-office"], default="grey-plaster")
    p_room.add_argument("--room-desc", default=None, help="Custom natural room background & lighting description")
    p_room.add_argument("--model", choices=["nano2", "nano21", "nano-pro", "nano2-lite"], default="nano2")
    p_room.add_argument("--project", default=None, help="Optional Flow project UUID")
    p_room.add_argument("--dry-run", action="store_true", help="Print the exact i2i command without executing")

    p_pick = sub.add_parser("pick-anchor", help="Extract sharpest relaxed closed-mouth, hand-free anchor PNG from video")
    p_pick.add_argument("input", help="Input MP4 clip")
    p_pick.add_argument("--out", required=True, help="Output PNG path")
    p_pick.add_argument("--samples", type=int, default=45)

    p_aud = sub.add_parser("match-audio", help="Match 8-band vocal EQ & EBU R128 loudness to golden voice reference")
    p_aud.add_argument("input", help="Input MP4/WAV/MP3 clip")
    p_aud.add_argument("--ref", required=True, help="Golden reference MP4/WAV/MP3 file")
    p_aud.add_argument("--out", required=True, help="Output audio-matched MP4/WAV path")
    p_aud.add_argument("--target-lufs", type=float, default=-14.0)

    args = parser.parse_args()

    if args.cmd == "check":
        gflow = find_gflow_bin()
        rc1 = subprocess.call([gflow, "auth", "status"])
        rc2 = subprocess.call([gflow, "credits", "user"])
        return 0 if (rc1 == 0 and rc2 == 0) else 1

    if args.cmd == "trim":
        new_d = trim_clip_to_speech(
            args.input,
            args.out,
            pad_start=args.pad_start,
            pad_end=args.pad_end,
            adaptive_loudnorm=args.adaptive_loudnorm,
        )
        print(f"Trimmed {args.input} -> {args.out} ({new_d:.3f}s)")
        return 0

    if args.cmd == "grade":
        apply_lab_color_match(args.input, args.out, room=args.room, target_l=args.target_l, gamma=args.gamma)
        print(f"LAB/gamma graded {args.input} -> {args.out}")
        return 0

    if args.cmd == "popout-pip":
        n = export_popout_webm(
            args.input, args.out, start_s=args.start, dur_s=args.duration, y_offset=args.y_offset
        )
        print(f"Exported VP9 alpha 3D pop-out PIP -> {args.out} ({n} frames)")
        return 0

    if args.cmd == "gen-room-anchor":
        cmd = gen_room_anchor(
            args.input,
            args.out,
            room_preset=args.room_preset,
            room_desc=args.room_desc,
            model=args.model,
            project=args.project,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print("[dry-run]", " ".join(f'"{c[:72]}..."' if len(c) > 85 else (f'"{c}"' if " " in c else c) for c in cmd))
        else:
            print(f"Generated face-locked room anchor -> {args.out}")
        return 0

    if args.cmd == "pick-anchor":
        ts, sc = pick_neutral_anchor(args.input, args.out, max_samples=args.samples)
        print(f"Picked neutral anchor @ {ts:.2f}s (score={sc:.1f}) -> {args.out}")
        return 0

    if args.cmd == "match-audio":
        gains = match_audio_spectrum(args.input, args.ref, args.out, target_lufs=args.target_lufs)
        print(f"Matched vocal EQ/LUFS ({args.target_lufs:.1f} LUFS) -> {args.out} | band_db={gains}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
