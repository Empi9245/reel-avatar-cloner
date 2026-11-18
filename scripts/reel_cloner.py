"""Reusable CLI toolkit for cloning Reels/TikToks with AI avatar @Eva, 4-DOF temporal B-roll cleaning, and Italian captions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


SKILL_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = SKILL_DIR / "resources"
DEFAULT_FONT = "C:/Windows/Fonts/segoeuib.ttf"
ARIAL_BOLD = "C:/Windows/Fonts/arialbd.ttf"
RNG = np.random.default_rng(2026)


def probe_video(video_path: Path) -> dict:
    """Return video resolution, fps, duration, and stream types via ffprobe."""
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ],
        text=True,
    )
    return json.loads(out)


def scan_frame_diffs(src: Path, fps: float) -> list[dict]:
    """Detect subtle screen-to-screen cuts, whip-pan transitions, and top-pill updates via OpenCV diffs."""
    cap = cv2.VideoCapture(str(src))
    prev: np.ndarray | None = None
    events: list[dict] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        if prev is not None:
            f32 = frame.astype(np.float32)
            p32 = prev.astype(np.float32)
            full_diff = float(np.mean(np.abs(f32 - p32)))
            top_diff = float(np.mean(np.abs(f32[: int(h * 0.25), int(w * 0.1) : int(w * 0.9)] - p32[: int(h * 0.25), int(w * 0.1) : int(w * 0.9)])))
            mid_diff = float(np.mean(np.abs(f32[int(h * 0.35) : int(h * 0.7), int(w * 0.08) : int(w * 0.92)] - p32[int(h * 0.35) : int(h * 0.7), int(w * 0.08) : int(w * 0.92)])))
            if full_diff > 12.0 or top_diff > 8.0 or mid_diff > 15.0:
                events.append(
                    {
                        "frame_1based": idx + 1,
                        "time_s": round(idx / max(1.0, fps), 4),
                        "full_diff": round(full_diff, 2),
                        "top_diff": round(top_diff, 2),
                        "mid_diff": round(mid_diff, 2),
                    }
                )
        prev = frame
        idx += 1
    cap.release()
    return events


def cmd_analyze(args: argparse.Namespace) -> None:
    """Detect scene cuts + subtle frame diffs, extract representative keyframes, and separate audio track."""
    src = Path(args.video)
    workdir = Path(args.workdir)
    frames_dir = workdir / "frames_raw"
    clips_dir = workdir / "clips"
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    meta = probe_video(src)
    duration = float(meta["format"]["duration"])
    vstream = next(s for s in meta["streams"] if s["codec_type"] == "video")
    num, den = (int(x) for x in vstream["r_frame_rate"].split("/"))
    fps = num / max(1, den)
    print(f"Video: {vstream['width']}x{vstream['height']} @ {fps:.3f}fps, duration={duration:.3f}s")

    proc = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(src),
            "-vf",
            f"select='gt(scene,{args.threshold})',showinfo",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    cuts = [0.0]
    for line in proc.stderr.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            t = float(m.group(1))
            if t - cuts[-1] > 0.35:
                cuts.append(round(t, 4))
    cuts.append(round(duration, 4))
    print("FFmpeg scene cuts:", cuts)

    diff_events = scan_frame_diffs(src, fps)
    print(f"OpenCV diff events (>threshold): {len(diff_events)} recorded in analysis.json")

    for idx in range(len(cuts) - 1):
        t0, t1 = cuts[idx], cuts[idx + 1]
        mid = round((t0 + t1) / 2.0, 3)
        out_png = frames_dir / f"scene_{idx + 1:02d}_{t0:.2f}s.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(mid), "-i", str(src), "-frames:v", "1", str(out_png)],
            check=True,
            stderr=subprocess.DEVNULL,
        )

    has_audio = any(s["codec_type"] == "audio" for s in meta["streams"])
    if has_audio:
        audio_out = clips_dir / "audio_originale.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(audio_out)],
            check=True,
            stderr=subprocess.DEVNULL,
        )
        print("Extracted audio guide:", audio_out)

    (workdir / "analysis.json").write_text(
        json.dumps(
            {
                "source": str(src),
                "width": int(vstream["width"]),
                "height": int(vstream["height"]),
                "fps": round(fps, 4),
                "duration": duration,
                "cuts": cuts,
                "diff_events": diff_events,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Keyframes & analysis.json saved to {workdir}")


def cmd_split(args: argparse.Namespace) -> None:
    """Split video into mute (`-an`), frame-accurate MP4 segments normalized cleanly at the requested ranges."""
    src = Path(args.video)
    clips_dir = Path(args.workdir) / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    meta = probe_video(src)
    duration = float(meta["format"]["duration"])

    parts = [p.strip() for p in args.cuts.split(",") if p.strip()]
    for idx, spec in enumerate(parts, start=1):
        start_s, end_s = spec.split(":")
        t0 = float(start_s)
        t1 = duration if end_s.lower() == "end" else float(end_s)
        out_mp4 = clips_dir / f"parte{idx}_ref_raw.mp4"
        cmd = ["ffmpeg", "-y", "-ss", f"{t0:.4f}", "-to", f"{t1:.4f}", "-i", str(src)]
        if args.scale:
            w, h = args.scale.split("x")
            cmd.extend(["-vf", f"scale={w}:{h}:flags=lanczos,fps=30"])
        cmd.extend(["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(out_mp4)])
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
        print(f"Split mute clip: {out_mp4} ({t0:.2f}s -> {t1:.2f}s)")


def dilate_ellipse(mask: np.ndarray, rx: int, ry: int) -> np.ndarray:
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rx + 1, 2 * ry + 1))
    return cv2.dilate(mask, k)


def rounded_rect_mask(shape: tuple[int, int], rect: tuple[int, int, int, int], radius: int = 18) -> np.ndarray:
    """Draw a filled rounded-rectangle mask in grayscale uint8."""
    h, w = shape
    x1, y1, x2, y2 = rect
    mask = np.zeros((h, w), dtype=np.uint8)
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    cv2.rectangle(mask, (x1 + r, y1), (x2 - r, y2), 255, -1)
    cv2.rectangle(mask, (x1, y1 + r), (x2, y2 - r), 255, -1)
    for cx, cy in ((x1 + r, y1 + r), (x2 - r, y1 + r), (x1 + r, y2 - r), (x2 - r, y2 - r)):
        cv2.circle(mask, (cx, cy), r, 255, -1)
    return mask


def build_letter_silhouette_mask(
    bgr: np.ndarray,
    box: tuple[int, int, int, int],
    white_thresh: int = 165,
    diff_thresh: int = 60,
    emoji_x_min: int | None = None,
    emoji_mode: str = "none",
    dilate_px: int = 7,
    max_y: int | None = None,
    extra_circle: tuple[int, int, int] | None = None,
) -> np.ndarray:
    """Create a tight silhouette mask hugging white outlined letters, dark strokes, and emojis."""
    h, w = bgr.shape[:2]
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    roi = bgr[y0:y1, x0:x1]
    b, g, r = roi[:, :, 0].astype(np.int16), roi[:, :, 1].astype(np.int16), roi[:, :, 2].astype(np.int16)
    mn = np.minimum(np.minimum(r, g), b)
    mx = np.maximum(np.maximum(r, g), b)
    diff = mx - mn

    roi_mask = (mn > white_thresh) & (diff < diff_thresh)

    if emoji_x_min is not None and emoji_x_min < x1:
        ex0 = max(0, emoji_x_min - x0)
        sub_r, sub_g, sub_b = r[:, ex0:], g[:, ex0:], b[:, ex0:]
        sub_mn, sub_mx = mn[:, ex0:], mx[:, ex0:]
        if emoji_mode == "skulls":
            roi_mask[:, ex0:] |= sub_mn > 125
        elif emoji_mode == "crying":
            roi_mask[:, ex0:] |= (
                ((sub_g - sub_b) > 30)
                | ((sub_b - sub_r) > 45)
                | ((sub_mn > 160) & (sub_mx - sub_mn < 50))
            )

    full_mask = np.zeros((h, w), dtype=np.uint8)
    full_mask[y0:y1, x0:x1] = roi_mask.astype(np.uint8) * 255

    if dilate_px > 0:
        k = dilate_px * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        full_mask = cv2.dilate(full_mask, kernel)

    if extra_circle is not None:
        cx, cy, rad = extra_circle
        cv2.circle(full_mask, (cx, cy), rad, 255, -1)

    if max_y is not None:
        full_mask[max_y:, :] = 0
    return full_mask


def telea_inpaint_with_grain(bgr: np.ndarray, mask: np.ndarray, radius: int = 5, grain_sigma: float = 1.3) -> np.ndarray:
    """Inpaint masked silhouettes via OpenCV Telea and restore subtle sensor grain inside the mask."""
    if not np.any(mask):
        return bgr
    inpainted = cv2.inpaint(bgr, mask, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)
    if grain_sigma > 0:
        noise = RNG.normal(0.0, grain_sigma, size=bgr.shape).astype(np.float32)
        m = (mask > 0)[:, :, None]
        noisy = np.clip(inpainted.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        inpainted = np.where(m, noisy, inpainted)
    return inpainted


def get_temporal_white_core(
    frames: list[np.ndarray],
    s0: int,
    e0: int,
    boxes: list[tuple[int, int, int, int]],
    white_thresh: int = 170,
) -> np.ndarray:
    """Detect static temporal-invariant bright letter cores across 0-based inclusive frame range [s0..e0]."""
    h, w = frames[0].shape[:2]
    full = np.zeros((h, w), dtype=np.uint8)
    for x1, y1, x2, y2 in boxes:
        stack = np.stack([frames[i][y1:y2, x1:x2] for i in range(s0, e0 + 1)], axis=0)
        min_bgr = np.min(stack, axis=0)
        white = (np.min(min_bgr, axis=2) > white_thresh).astype(np.uint8) * 255
        full[y1:y2, x1:x2] |= white
    return full


def horizontal_scanline_inpaint(img_f: np.ndarray, mask_bool: np.ndarray) -> np.ndarray:
    """Interpolate residual pixels strictly along horizontal scanlines to preserve crisp UI borders."""
    out = img_f.copy()
    ys, _ = np.where(mask_bool)
    if len(ys) == 0:
        return out
    for y in np.unique(ys):
        row_m = mask_bool[y]
        valid_x = np.where(~row_m)[0]
        if len(valid_x) == 0:
            continue
        missing_x = np.where(row_m)[0]
        for c in range(3):
            out[y, missing_x, c] = np.interp(missing_x, valid_x, out[y, valid_x, c])
    blurred = cv2.GaussianBlur(out, (11, 3), 2.5)
    out[mask_bool] = blurred[mask_bool]
    return out


def reconstruct_segment_temporal_4dof(
    frames: list[np.ndarray],
    grays: list[np.ndarray],
    s0: int,
    e0: int,
    core_mask: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    track_y: tuple[int, int] | None = None,
    target_rx: int = 11,
    target_ry: int = 10,
    donor_rx: int = 14,
    donor_ry: int = 13,
    min_y: int | None = None,
    max_y: int | None = None,
    force_horiz_x_lt_1based: dict[int, int] | None = None,
) -> dict[int, np.ndarray]:
    """Reconstruct text-occluded B-roll screen pixels from adjacent frames via 4-DOF affine tracking."""
    h, w = frames[0].shape[:2]
    y_box_min = min(b[1] for b in boxes)
    y_box_max = max(b[3] for b in boxes)
    cy0 = max(0, y_box_min - 75)
    cy1 = min(h, y_box_max + 75)
    ch = cy1 - cy0

    if track_y is None:
        track_y = (int(h * 0.24), int(h * 0.67))

    text_mask = dilate_ellipse(core_mask, target_rx, target_ry)
    donor_excl = dilate_ellipse(core_mask, donor_rx, donor_ry)
    if min_y is not None:
        text_mask[:min_y, :] = 0
        donor_excl[:min_y, :] = 0
    if max_y is not None:
        text_mask[max_y:, :] = 0
        donor_excl[max_y:, :] = 0

    track_base = np.zeros((h, w), dtype=np.uint8)
    track_base[track_y[0] : track_y[1], int(w * 0.05) : int(w * 0.95)] = 255
    track_mask = cv2.bitwise_and(track_base, cv2.bitwise_not(donor_excl))

    M_step: dict[int, np.ndarray] = {}
    for i in range(s0, e0):
        pts0 = cv2.goodFeaturesToTrack(grays[i], maxCorners=500, qualityLevel=0.005, minDistance=5, mask=track_mask)
        if pts0 is None or len(pts0) < 12:
            M_step[i] = np.eye(3, dtype=np.float64)
            continue
        pts1, st, _ = cv2.calcOpticalFlowPyrLK(grays[i], grays[i + 1], pts0, None, winSize=(25, 25), maxLevel=4)
        good0 = pts0[st.flatten() == 1]
        good1 = pts1[st.flatten() == 1]
        if len(good0) < 12:
            M_step[i] = np.eye(3, dtype=np.float64)
            continue
        M, _ = cv2.estimateAffinePartial2D(good0, good1, method=cv2.RANSAC, ransacReprojThreshold=1.5)
        M_step[i] = np.vstack([M, [0.0, 0.0, 1.0]]) if M is not None else np.eye(3, dtype=np.float64)

    def get_M_src_to_t(src: int, t: int) -> np.ndarray:
        M3 = np.eye(3, dtype=np.float64)
        if src < t:
            for k in range(src, t):
                M3 = M_step[k] @ M3
        elif src > t:
            for k in range(t, src):
                M3 = M_step[k] @ M3
            M3 = np.linalg.inv(M3)
        M_crop = M3[:2, :].copy()
        M_crop[1, 2] -= float(cy0)
        return M_crop

    clean_donor_valid = cv2.GaussianBlur((donor_excl == 0).astype(np.float32), (5, 5), 1.0)
    text_mask_c = text_mask[cy0:cy1, :] > 0
    target_valid_c = (donor_excl[cy0:cy1, :] == 0).astype(np.float32)
    outer_ring_c = (dilate_ellipse(core_mask, target_rx + 5, target_ry + 5)[cy0:cy1, :] > 0) & (
        donor_excl[cy0:cy1, :] == 0
    )
    alpha_c = cv2.GaussianBlur(text_mask_c.astype(np.float32), (7, 7), 1.5)

    results: dict[int, np.ndarray] = {}
    for t in range(s0, e0 + 1):
        full_out = frames[t].copy()
        target_c = full_out[cy0:cy1, :].astype(np.float32)
        horiz_init = horizontal_scanline_inpaint(target_c, text_mask_c)

        acc_color = np.zeros((ch, w, 3), dtype=np.float64)
        acc_weight = np.zeros((ch, w), dtype=np.float64)

        for src in range(s0, e0 + 1):
            if src == t:
                continue
            M_crop = get_M_src_to_t(src, t)
            warped_bgr = cv2.warpAffine(frames[src], M_crop, (w, ch), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
            warped_valid = cv2.warpAffine(
                clean_donor_valid, M_crop, (w, ch), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0
            )

            ring_valid = outer_ring_c & (warped_valid > 0.9)
            if np.sum(ring_valid) > 80:
                diff_med = np.median(target_c[ring_valid] - warped_bgr[ring_valid], axis=0)
                warped_bgr = np.clip(warped_bgr + diff_med, 0, 255)

            both_valid = target_valid_c * (warped_valid > 0.85).astype(np.float32)
            abs_diff = np.mean(np.abs(target_c - warped_bgr), axis=2) * both_valid
            local_err_num = cv2.GaussianBlur(abs_diff, (41, 41), 12.0)
            local_err_den = cv2.GaussianBlur(both_valid, (41, 41), 12.0) + 1e-4
            local_match_w = np.exp(-(((local_err_num / local_err_den) / 6.5) ** 2))

            valid_w = np.clip((warped_valid - 0.75) * 4.0, 0.0, 1.0) ** 2
            temporal_w = 1.0 / (1.0 + 0.12 * abs(src - t))
            w_map = valid_w * temporal_w * local_match_w
            acc_color += warped_bgr.astype(np.float64) * w_map[:, :, None]
            acc_weight += w_map

        if force_horiz_x_lt_1based and (t + 1) in force_horiz_x_lt_1based:
            acc_weight[:, : int(force_horiz_x_lt_1based[t + 1])] = 0.0

        has_donor = acc_weight > 0.02
        donor_rgb = np.where(has_donor[:, :, None], acc_color / np.maximum(acc_weight[:, :, None], 1e-4), horiz_init)
        donor_conf = np.clip(acc_weight / 0.12, 0.0, 1.0)[:, :, None]
        prelim = donor_conf * donor_rgb + (1.0 - donor_conf) * horiz_init
        prelim = np.clip(prelim + RNG.normal(0.0, 1.15, prelim.shape).astype(np.float32), 0, 255)

        blended_c = target_c * (1.0 - alpha_c[:, :, None]) + prelim * alpha_c[:, :, None]
        full_out[cy0:cy1, :] = np.clip(blended_c, 0, 255).astype(np.uint8)
        results[t] = full_out
    return results


def encode_bgr_frames(frames: list[np.ndarray], out_mp4: Path, fps: float = 30.0) -> None:
    h, w = frames[0].shape[:2]
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", "bgr24", "-r", str(fps),
        "-i", "-",
        "-an", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for fr in frames:
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {out_mp4}:\n{err}")


def cmd_clean(args: argparse.Namespace) -> None:
    """Clean text overlays via 4-DOF temporal screen reconstruction (`temporal_4dof`) or Telea silhouette (`telea`).

    Rule JSON format (all frame numbers 1-based inclusive):
    [
      {"mode": "temporal_4dof", "start_frame": 3, "end_frame": 31,
       "boxes": [[64,612,656,660]], "track_y": [320,840],
       "target_rx": 11, "target_ry": 9, "donor_rx": 14, "donor_ry": 11,
       "min_y": 609, "force_horiz_x_lt": {"68": 215}},
      {"mode": "pill_telea", "start_frame": 1, "end_frame": 115,
       "rects": [[150,135,573,207], [43,203,676,290]], "radius": 6},
      {"mode": "telea", "start_frame": 1, "end_frame": 164, "static_mask": false,
       "boxes": [[92,740,630,862]], "extra_circle": [563,825,29], "dilate_px": 6}
    ]
    """
    src = Path(args.input)
    out = Path(args.out)
    rules = json.loads(Path(args.config).read_text(encoding="utf-8"))

    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames: list[np.ndarray] = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()

    h, w = frames[0].shape[:2]
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    work_frames = [f.copy() for f in frames]

    # Pass 1: Temporal 4-DOF screen reconstruction rules on clean unmodified source frames
    for rule in rules:
        if rule.get("mode", "telea") != "temporal_4dof":
            continue
        s0 = max(0, int(rule["start_frame"]) - 1)
        e0 = min(len(frames) - 1, int(rule["end_frame"]) - 1)
        boxes = [tuple(int(v) for v in b) for b in rule["boxes"]]
        core = get_temporal_white_core(frames, s0, e0, boxes, white_thresh=int(rule.get("white_thresh", 170)))
        force_horiz = {int(k): int(v) for k, v in rule.get("force_horiz_x_lt", {}).items()}
        rec = reconstruct_segment_temporal_4dof(
            frames,
            grays,
            s0,
            e0,
            core,
            boxes,
            track_y=tuple(rule["track_y"]) if rule.get("track_y") else None,
            target_rx=int(rule.get("target_rx", 11)),
            target_ry=int(rule.get("target_ry", 10)),
            donor_rx=int(rule.get("donor_rx", 14)),
            donor_ry=int(rule.get("donor_ry", 13)),
            min_y=rule.get("min_y"),
            max_y=rule.get("max_y"),
            force_horiz_x_lt_1based=force_horiz or None,
        )
        y_box_min = max(0, min(b[1] for b in boxes) - 75)
        y_box_max = min(h, max(b[3] for b in boxes) + 75)
        for t_idx, repaired in rec.items():
            work_frames[t_idx][y_box_min:y_box_max, :] = repaired[y_box_min:y_box_max, :]

    # Pass 2: Pill / Telea rules applied onto work_frames
    static_masks: dict[int, np.ndarray] = {}
    for r_idx, rule in enumerate(rules):
        mode = rule.get("mode", "telea")
        if mode == "temporal_4dof":
            continue
        if mode == "pill_telea":
            m = np.zeros((h, w), dtype=np.uint8)
            for rect in rule["rects"]:
                m |= rounded_rect_mask((h, w), tuple(int(v) for v in rect), radius=int(rule.get("corner_radius", 18)))
            static_masks[r_idx] = m
        elif rule.get("static_mask", True):
            ref_idx = max(0, min(len(frames) - 1, int(rule.get("ref_frame", rule["start_frame"])) - 1))
            m = np.zeros((h, w), dtype=np.uint8)
            for box in rule["boxes"]:
                m |= build_letter_silhouette_mask(
                    frames[ref_idx],
                    tuple(box),
                    white_thresh=int(rule.get("white_thresh", 165)),
                    diff_thresh=int(rule.get("diff_thresh", 60)),
                    emoji_x_min=rule.get("emoji_x_min"),
                    emoji_mode=rule.get("emoji_mode", "none"),
                    dilate_px=int(rule.get("dilate_px", 7)),
                    max_y=rule.get("max_y"),
                    extra_circle=tuple(rule["extra_circle"]) if rule.get("extra_circle") else None,
                )
            static_masks[r_idx] = m

    for idx0 in range(len(work_frames)):
        f1 = idx0 + 1
        m_telea = np.zeros((h, w), dtype=np.uint8)
        rad = 5
        for r_idx, rule in enumerate(rules):
            if rule.get("mode", "telea") == "temporal_4dof":
                continue
            if int(rule["start_frame"]) <= f1 <= int(rule["end_frame"]):
                rad = max(rad, int(rule.get("radius", 5)))
                if r_idx in static_masks:
                    m_telea |= static_masks[r_idx]
                else:
                    for box in rule["boxes"]:
                        m_telea |= build_letter_silhouette_mask(
                            work_frames[idx0],
                            tuple(box),
                            white_thresh=int(rule.get("white_thresh", 185)),
                            diff_thresh=int(rule.get("diff_thresh", 55)),
                            emoji_x_min=rule.get("emoji_x_min"),
                            emoji_mode=rule.get("emoji_mode", "none"),
                            dilate_px=int(rule.get("dilate_px", 6)),
                            max_y=rule.get("max_y"),
                            extra_circle=tuple(rule["extra_circle"]) if rule.get("extra_circle") else None,
                        )
        if np.any(m_telea):
            work_frames[idx0] = telea_inpaint_with_grain(work_frames[idx0], m_telea, radius=rad)

    encode_bgr_frames(work_frames, out, fps=fps)
    print(f"Cleaned silent video saved to {out}")


def load_emoji_sprite(name: str | None) -> Image.Image | None:
    """Load a bundled PNG emoji sprite from resources/ by key or filename."""
    if not name:
        return None
    mapping = {
        "crying": RESOURCES_DIR / "emoji_crying_pair.png",
        "skulls": RESOURCES_DIR / "emoji_skull_pair.png",
        "stars_trio": RESOURCES_DIR / "emoji_stars_trio.png",
        "persevere": RESOURCES_DIR / "emoji_persevere.png",
    }
    p = mapping.get(name, Path(name))
    return Image.open(p).convert("RGBA") if p.exists() else None


def resolve_font(font_choice: str | None, size: int) -> ImageFont.FreeTypeFont:
    path = ARIAL_BOLD if font_choice == "arialbd" and Path(ARIAL_BOLD).exists() else DEFAULT_FONT
    return ImageFont.truetype(path, size)


def render_top_pill_overlay(pill_cfg: dict, canvas_size: tuple[int, int] = (720, 1280)) -> Image.Image:
    """Render stepped two-row black rounded pill ('Genio: ⭐⭐⭐ / <line2>') at 2x supersampling."""
    scale = 2
    cw, ch = canvas_size
    layer = Image.new("RGBA", (cw * scale, ch * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    r1 = tuple(v * scale for v in pill_cfg.get("r1", [146, 132, 577, 208]))
    r2 = tuple(v * scale for v in pill_cfg.get("r2", [40, 202, 679, 291]))
    draw.rounded_rectangle(r1, radius=42, fill=(0, 0, 0, 255))
    draw.rounded_rectangle(r2, radius=44, fill=(0, 0, 0, 255))
    draw.rectangle((r1[0] + 36, r1[3] - 18, r1[2] - 36, r2[1] + 18), fill=(0, 0, 0, 255))

    font_name = pill_cfg.get("font", "arialbd")
    f_r1 = resolve_font(font_name, 88)
    label1 = pill_cfg["line1"]
    b1 = draw.textbbox((0, 0), label1, font=f_r1)
    lw1, lh1 = b1[2] - b1[0], b1[3] - b1[1]

    emoji1 = load_emoji_sprite(pill_cfg.get("emoji1"))
    if emoji1 is not None:
        target_h = 92
        target_w = int(round(emoji1.width * (target_h / max(1, emoji1.height))))
        emo_2x = emoji1.resize((target_w, target_h), Image.Resampling.LANCZOS)
        gap = 18
        total_w1 = lw1 + gap + target_w
        sx1 = (r1[0] + r1[2]) // 2 - total_w1 // 2
        cy1 = (r1[1] + r1[3]) // 2
        draw.text((sx1 - b1[0], cy1 - lh1 // 2 - b1[1]), label1, font=f_r1, fill=(255, 255, 255, 255))
        layer.alpha_composite(emo_2x, (sx1 + lw1 + gap, cy1 - target_h // 2 - 2))
    else:
        cy1 = (r1[1] + r1[3]) // 2
        draw.text(((r1[0] + r1[2]) // 2 - lw1 // 2 - b1[0], cy1 - lh1 // 2 - b1[1]), label1, font=f_r1, fill=(255, 255, 255, 255))

    line2 = pill_cfg["line2"]
    f_r2 = resolve_font(font_name, 88)
    b2 = draw.textbbox((0, 0), line2, font=f_r2)
    max_w2 = (r2[2] - r2[0]) - 64
    if (b2[2] - b2[0]) > max_w2:
        f_r2 = resolve_font(font_name, int(88 * max_w2 / (b2[2] - b2[0])))
        b2 = draw.textbbox((0, 0), line2, font=f_r2)
    lw2, lh2 = b2[2] - b2[0], b2[3] - b2[1]
    draw.text(((r2[0] + r2[2]) // 2 - lw2 // 2 - b2[0], (r2[1] + r2[3]) // 2 - lh2 // 2 - b2[1]), line2, font=f_r2, fill=(255, 255, 255, 255))

    return layer.resize(canvas_size, Image.Resampling.LANCZOS)


def render_tiktok_overlay(
    lines: list[dict],
    y_start: int | None = None,
    cy_center: int | None = None,
    font_size: int = 36,
    line_gap: int = 6,
    stroke_w: int = 4,
    font_choice: str | None = None,
    canvas_size: tuple[int, int] = (720, 1280),
) -> Image.Image:
    """Render supersampled 2x TikTok-style bold white text with black border + optional emoji & suffix."""
    scale = 2
    cw, ch = canvas_size
    layer = Image.new("RGBA", (cw * scale, ch * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = resolve_font(font_choice, font_size * scale)
    sw = stroke_w * scale

    # Measure total block height first if vertically centering around cy_center
    line_metrics = []
    for item in lines:
        bbox = draw.textbbox((0, 0), item["text"], font=font, stroke_width=sw)
        line_metrics.append((item, bbox, bbox[2] - bbox[0], bbox[3] - bbox[1]))
    total_h = sum(m[3] for m in line_metrics) + line_gap * scale * max(0, len(line_metrics) - 1)
    cy = (cy_center * scale - total_h // 2) if cy_center is not None else (y_start or 310) * scale

    for item, bbox, tw, th in line_metrics:
        text = item["text"]
        suffix = item.get("suffix", "")
        emoji_sprite = load_emoji_sprite(item.get("emoji"))

        ew, eh = 0, 0
        scaled_emoji = None
        if emoji_sprite is not None:
            target_h = int(font_size * scale * 1.04)
            ratio = target_h / max(1, emoji_sprite.height)
            ew = int(emoji_sprite.width * ratio)
            eh = target_h
            scaled_emoji = emoji_sprite.resize((ew, eh), Image.Resampling.LANCZOS)

        b_suf = draw.textbbox((0, 0), suffix, font=font, stroke_width=sw) if suffix else None
        sw_suf = (b_suf[2] - b_suf[0]) if b_suf else 0
        sh_suf = (b_suf[3] - b_suf[1]) if b_suf else 0

        # Snug kerning (-6px in 2x space) compensates for bilateral stroke width padding around adjacent glyphs
        gap_pre = int(item.get("emoji_gap_2x", -6 if suffix else 8 * scale)) if scaled_emoji is not None else 0
        gap_post = int(item.get("suffix_gap_2x", -6)) if (scaled_emoji is not None and suffix) else 0
        total_w = tw + gap_pre + ew + gap_post + sw_suf

        sx = (cw * scale - total_w) // 2
        draw.text((sx - bbox[0], cy - bbox[1]), text, font=font, fill=(255, 255, 255, 255), stroke_width=sw, stroke_fill=(0, 0, 0, 255))

        if scaled_emoji is not None:
            ex = sx + tw + gap_pre
            ey = cy + (th - eh) // 2
            layer.alpha_composite(scaled_emoji, (ex, ey))
            if suffix and b_suf is not None:
                sx2 = ex + ew + gap_post
                draw.text((sx2 - b_suf[0], cy + (th - sh_suf) // 2 - b_suf[1]), suffix, font=font, fill=(255, 255, 255, 255), stroke_width=sw, stroke_fill=(0, 0, 0, 255))

        cy += th + line_gap * scale

    return layer.resize(canvas_size, Image.Resampling.LANCZOS)


def cmd_caption(args: argparse.Namespace) -> None:
    """Apply TikTok-style Italian captions & stepped black pills from JSON onto a video, normalized 720x1280 30fps (`-an`)."""
    src = Path(args.input)
    out = Path(args.out)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    w, h = cfg.get("target_size", [720, 1280])

    cards = []
    for c in cfg["cards"]:
        if "pill" in c:
            ov = render_top_pill_overlay(c["pill"], canvas_size=(w, h))
        else:
            ov = render_tiktok_overlay(
                c["lines"],
                y_start=c.get("y_start"),
                cy_center=c.get("cy_center"),
                font_size=int(c.get("font_size", 36)),
                line_gap=int(c.get("line_gap", 6)),
                stroke_w=int(c.get("stroke_w", 4)),
                font_choice=c.get("font"),
                canvas_size=(w, h),
            )
        cards.append((int(c["start_frame"]), int(c["end_frame"]), ov))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        raw_frames = tmp_path / "raw"
        out_frames = tmp_path / "out"
        raw_frames.mkdir()
        out_frames.mkdir()

        vf = f"scale={w}:{h}:flags=lanczos:force_original_aspect_ratio=increase,crop={w}:{h},fps=30"
        subprocess.run(["ffmpeg", "-y", "-i", str(src), "-vf", vf, str(raw_frames / "frame_%04d.bmp")], check=True, stderr=subprocess.DEVNULL)
        for idx, fpath in enumerate(sorted(raw_frames.glob("frame_*.bmp")), start=1):
            im = Image.open(fpath).convert("RGBA")
            for s_f, e_f, ov in cards:
                if s_f <= idx <= e_f:
                    im = Image.alpha_composite(im, ov)
            im.convert("RGB").save(out_frames / fpath.name)

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-framerate", "30",
                "-i", str(out_frames / "frame_%04d.bmp"),
                "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-an",
                str(out),
            ],
            check=True,
            stderr=subprocess.DEVNULL,
        )
    print(f"Captioned silent clip saved to {out}")


def cmd_find_audio(args: argparse.Namespace) -> None:
    """Identify exact song/remix and TikTok start timestamp offset from audio_originale.mp3 using Shazam + output direct sound search suggestions."""
    import warnings
    warnings.filterwarnings("ignore")
    hook = getattr(args, "hook", None)

    print("=" * 70)
    print("STRATEGIA DOPPIA AUDIO TIKTOK & INSTAGRAM")
    print("=" * 70)

    # Metodo 1: Ricerca Diretta Suoni con Testo del Meme
    print("\n[METODO 1 - RICERCA DIRETTA SUONI CON TESTO DEL MEME (CONSIGLIATO)]")
    print("Spesso su TikTok/IG il suono del trend è già stato caricato dalla community")
    print("con il titolo del meme o dell'hook. Trovarlo così è istantaneo e già tagliato!")
    print("Istruzioni:")
    print("  1. Apri la barra di ricerca nell'app di TikTok o Instagram")
    print("  2. Seleziona espressamente la scheda 'Suoni' / 'Audio' (non 'Top' o 'Video')")
    if hook:
        print(f"  3. Cerca esattamente: \"{hook}\"")
        variants = []
        if "3" in hook:
            variants.append(hook.replace("3", "tre"))
        elif "tre" in hook.lower():
            variants.append(hook.lower().replace("tre", "3"))
        for v in variants:
            print(f"     oppure: \"{v}\"")
    else:
        print("  3. Cerca il testo del parlato/hook del video (es. 'genio tre desideri', 'guy next to me')")
    print("  4. Clicca sul suono corrispondente e tocca 'Usa questo suono' / 'Aggiungi ai Preferiti'.")

    # Metodo 2: Shazam Fingerprint + Forbici
    print("\n[METODO 2 - BRANO UFFICIALE + FORBICI ✂️ (SHAZAM FINGERPRINT)]")
    import asyncio
    try:
        from shazamio import Shazam
    except ImportError:
        print("NOTA: 'shazamio' non è installato (esegui: pip install shazamio per abilitare il fingerprint).")
        print("=" * 70)
        return

    aud_path = Path(args.audio)
    if not aud_path.exists():
        print(f"File audio non trovato: {aud_path}")
        print("=" * 70)
        return

    async def _run() -> dict:
        shazam = Shazam()
        return await asyncio.wait_for(shazam.recognize(str(aud_path)), timeout=10.0)

    try:
        res = asyncio.run(_run())
        track = res.get("track")
        matches = res.get("matches", [])
        if not track:
            print("Nessun match diretto con Shazam. Se l'audio è rallentato/modificato, prova con:")
            print("ffmpeg -i audio.mp3 -af asetrate=48000*1.23,aresample=48000 audio_fast.mp3")
        else:
            title = track.get("title")
            subtitle = track.get("subtitle")
            url = track.get("url")
            offset = matches[0].get("offset") if matches else None
            timeskew = matches[0].get("timeskew") if matches else None
            print(f"Titolo Ufficiale: {title}")
            print(f"Artista: {subtitle}")
            print(f"Shazam URL: {url}")
            if offset is not None:
                m, s = divmod(float(offset), 60.0)
                print(f"Offset Inizio Forbici TikTok: {int(m):02d}:{s:05.2f} ({float(offset):.2f}s) | timeskew={timeskew}")
                print(f"Istruzioni: Cerca '{title}' nei suoni ufficiali, tocca l'icona Forbici ✂️ e posiziona l'inizio a {int(m):02d}:{s:05.2f}.")
    except Exception as e:
        print(f"Errore durante l'interrogazione Shazam: {e}")
    print("=" * 70)


def cmd_assemble(args: argparse.Namespace) -> None:
    """Concatenate captioned clips into final silent MP4 (and optional audio-muxed MP4 preserving all video frames)."""
    parts = [Path(p).resolve() for p in args.parts]
    out_mute = Path(args.out).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        concat_txt = Path(tmp) / "concat.txt"
        concat_txt.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts) + "\n", encoding="utf-8")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
                str(out_mute),
            ],
            check=True,
            stderr=subprocess.DEVNULL,
        )
    print(f"Final silent reel saved to {out_mute}")

    if args.audio and args.out_audio:
        out_audio = Path(args.out_audio).resolve()
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(out_mute), "-i", str(Path(args.audio).resolve()),
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                str(out_audio),
            ],
            check=True,
            stderr=subprocess.DEVNULL,
        )
        print(f"Final reel with audio saved to {out_audio}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reel Avatar Cloner pipeline helper.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Detect scene cuts, frame diffs, keyframes and audio.")
    p_an.add_argument("video")
    p_an.add_argument("--workdir", required=True)
    p_an.add_argument("--threshold", type=float, default=0.25)
    p_an.set_defaults(func=cmd_analyze)

    p_sp = sub.add_parser("split", help="Split video into mute frame-accurate segments.")
    p_sp.add_argument("video")
    p_sp.add_argument("--cuts", required=True, help='Comma-separated "start:end" pairs, e.g. "0:6.0,6.0:end"')
    p_sp.add_argument("--workdir", required=True)
    p_sp.add_argument("--scale", default=None, help='Optional target size e.g. "720x1280" at 30fps')
    p_sp.set_defaults(func=cmd_split)

    p_cl = sub.add_parser("clean", help="Remove text overlays cleanly via 4-DOF temporal reconstruction or Telea silhouette.")
    p_cl.add_argument("input")
    p_cl.add_argument("--out", required=True)
    p_cl.add_argument("--config", required=True, help="JSON rules file")
    p_cl.set_defaults(func=cmd_clean)

    p_ca = sub.add_parser("caption", help="Render TikTok-style Italian captions & pills normalized 720x1280 30fps.")
    p_ca.add_argument("input")
    p_ca.add_argument("--out", required=True)
    p_ca.add_argument("--config", required=True, help="JSON cards file")
    p_ca.set_defaults(func=cmd_caption)

    p_as = sub.add_parser("assemble", help="Concatenate final clips into mute (+ optional audio) reel.")
    p_as.add_argument("--parts", nargs="+", required=True)
    p_as.add_argument("--out", required=True)
    p_as.add_argument("--audio", default=None)
    p_as.add_argument("--out-audio", default=None)
    p_as.set_defaults(func=cmd_assemble)

    p_au = sub.add_parser("find-audio", help="Identify exact track/remix, Scissors offset and direct meme sound queries.")
    p_au.add_argument("audio")
    p_au.add_argument("--hook", type=str, default=None, help="Spoken hook / meme text to generate direct sound search queries (e.g. 'genio tre desideri')")
    p_au.set_defaults(func=cmd_find_audio)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
