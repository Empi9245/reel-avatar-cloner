# Multi-Clip Consistency Handbook (Model-Agnostic, Google Flow & Local Unsloth MiniMax-H3 Ref2VA)

Consolidated production playbook combining every lesson learned across Reel 08–11 (`@Eva`), 2025–2026 creator workflows (YouTube, Reddit `r/VEO3` / `r/aivideo` / `r/GoogleFlow` / `r/StableDiffusion`, X, GitHub), Google Flow automation, and local **Unsloth Studio / `sd-cli.exe` (`MiniMax-H3 Ref2VA`)**.

---

## 1. History & Lessons Learned (Reel 08–11 Post-Mortem)

Every failure mode hit during multi-clip production and the permanent engineering fix:

| Failure Hit in Production | Root Cause | Permanent Fix |
|---|---|---|
| **Wardrobe drift across cuts** | Using head/neck-only reference (`eva_front_single.png`) let the video model invent different shirts. | Always use the dressed waist-up anchor (`resources/eva_con_tshirt.png`) or a full 3-panel `Cast Kit v1` sheet. |
| **Voronoi / smeared aura around moving laptop text** | 2D `cv2.INPAINT_TELEA` across panning/handheld laptop screens pulled dark lines vertically. | Never use 2D `Telea` on moving screen B-roll. Use `temporal_4dof` (affine alignment + ring lighting match) OR rebuild all UI/charts 100% cleanly in **Remotion (`1080x1920 @ 30fps`)**. |
| **`support.google.com/flow?p=speech_edit` hard block** | Re-encoding a Flow-generated `@Eva` clip on PC (`ffmpeg`/`OpenCV`) stripped its origin signature; uploading it into Flow V2V with *new dialogue* triggered Flow's voice-tampering guard. | **NEVER** re-upload a PC-edited `@Eva` MP4 with new speech into Flow V2V. Anchor Phase B clips via clean still frames (`master_*.png`) + `eva_con_tshirt.png` in `Frames` / `Ingredients` (or Flow's native in-project `Save frame` / `Extend`). |
| **Male knuckles, rings & collar mic cloned onto `@Eva`** | Passing raw male-creator reference clips into V2V caused Flow to copy thick fingers, rings, and lavalier mics onto `@Eva`. | Never feed male-hand clips into V2V, omit `"hand gestures of the attached driving reference clip"`, and describe bespoke feminine gestures per clip (`graceful female hands and neat natural fingernails`, `no extra or warped fingers, no rings`). |
| **Buggy robotic motion + blurred chest (`"tutto buggato"`)** | Original Reel 11 talking-head cuts were only `0.6s–2.3s`; `boomerang`-looping `10–16` frames forward/backward + chest `Telea` inpainting looked mechanical and smeared. | **Strict ban on short-clip looping (`< 3s`) and chest `Telea` inpainting.** Play every prepared `.mp4` via `read_file` before delivery. |
| **V2V duration lock cuts off Italian sentences** | Uploading any V2V reference video locks Flow's output duration to that clip's exact length. | When source cuts are `< 3s`, use **Images-Only (`Frames` Start Frame / `Ingredients` / `Ref2VA`)** with **NO V2V video**, unlocking free manual duration (`5s–8s` in Flow, `5s–14.4s` in MiniMax-H3). |
| **Slurred acronyms/numbers (`"GPT-CGLM"`)** | Prompting `"brisk cadence"` over dense lists caused `Omni 1.2 Flash` to mash words together. | Spell numbers/acronyms phonetically (`"GPT sei, DeepSeek, G-L-M"`, `"cento euro"`, `"dalle dieci alle venti ore"`, `"cinque ore"`, `"D-M"`) and prompt `"clear well-articulated Italian diction without rushing, pausing distinctly on every comma"`. |
| **False-positive safety rejections** | Benign words (`small silver hoop earrings`, `chestnut`, `selfie`, `tight`, `lips`, `mouth`, `girl`, `bedroom`, `bed`, `tank top`, `collar`, `horn`, `exposure`, `raw`, `unretouched`, `glossy`, and Italian `"come"`) tripped Flow's text/policy classifier. | Always run prompts through the anti-trigger word check before submitting. |
| **Uncanny drifting AI eyes** | Prompting pure eyeball rotation with a still head or chaining multiple gaze targets in `< 2s`. | Apply **Head-Lead Rule** + **Single-Target Gaze Lock** + screen-space `camera-left / camera-right` coordinates. |

---

## 2. The 5 Universal Pillars of Multi-Clip Consistency (Model-Agnostic)

Works across **Google Flow (`Omni 1.2 Flash` / Veo)**, **MiniMax-H3 (`Ref2VA` / `FL2VA`)**, **Seedance 2.5 / Higgsfield**, **Wan 2.2**, and **Kling / Runway**:

### Pillar 1 — Locked Identity Anchor & The Single-Face Multi-Room Law (`v2.1.0`)
- **Primary Canonical Smartphone UGC Anchor (`resources/eva_canonical_warm_armadio.png`):** Natural `24mm` front-camera chest-up perspective, relaxed closed-mouth expression, round tortoiseshell glasses, matte charcoal-black crew-neck t-shirt, thin gold chain, and authentic skin texture. Prefer `eva_canonical_warm_armadio.png` over studio flat headshots (`eva_front_single.png`) or over-grinned frames (`master_muro_grigio.png`) whenever shooting handheld UGC Reels.
- **Why Room A vs. Room B Drifted Historically (`8–9/10` -> `10/10`):**
  1. Never pass **two different faces** (`eva_con_tshirt.png` studio look + `master_room_with_face.png`) together into `r2v`—the generator blends features differently whenever the second image changes room lighting or smile geometry.
  2. A wide toothy smile in a master still (`master_muro_grigio.png`) subtly alters jawline, cheek volume, and mouth proportions compared to relaxed neutral frames.
- **Stills-First Relighting (`gen-room-anchor`) — Joey (`@noisygroup`) `Banana Pro Director` & `higgsfield-ai/skills` `MCSLA` Method:**
  - Use the **"Change One Variable + Relight"** rule BEFORE generating video in Room B: run `gflow_batch_ingest.py gen-room-anchor` (`gflow image i2i` on `resources/eva_canonical_warm_armadio.png`) to place **the exact pixel-faithful `@Eva` identity** into the new room background (`grey-plaster`, `warm-cream`, or custom `--room-desc`) while matching directional window bounce light on hair/glasses/shoulders:
    ```bash
    python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py gen-room-anchor ^
      --room-preset grey-plaster --model nano2 --out work/anchor_room_grey.png
    ```
  - Then feed **ONE single face anchor** per room (`eva_canonical_warm_armadio.png` for Warm Wardrobe, `anchor_room_grey.png` for Grey Wall — optionally paired ONLY with an empty/person-free `Location Sheet`), keeping prompt prose crisp (`< 200` words, **MCSLA**: *Model/Lens · Camera · Subject · Look/Light · Action*).
  - Use `python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py pick-anchor <clip.mp4> --out anchor.png` to extract clean closed-mouth, hand-free rest stills automatically.

### Pillar 2 — Star Topology via Clean Rest Plates (Never Daisy-Chain Clips)
- **Why daisy-chaining fails:** Feeding `Clip 1 -> Clip 2 -> Clip 3 -> Clip 4` compounds compression blur, color shift, and facial geometry drift after 2–3 hops.
- **How Star Topology works:**
  1. **Group by unique room/camera setup** (e.g., Setup A = `anchor_room_grey.png`, Setup B = `eva_canonical_warm_armadio.png`).
  2. **Phase A (Masters):** Generate **1 Master Clip per unique room setup** first (`eva_01`, `eva_04`). Inspect eyes, hands, wardrobe, framing, and Italian pronunciation.
  3. **Verify Rest Anchors (`pick-anchor`):** Keep the clean neutral closed-mouth anchor (`eva_canonical_warm_armadio.png` / `anchor_room_grey.png`), or refine cleanly via `pick-anchor`.
  4. **Phase B (Spokes):** Anchor **every remaining clip** directly to its immutable room hub — never from intermediate Phase B clips. Every spoke stays at generation distance `1`.

### Pillar 3 — 4-Stage Broadcast Voice & Lip-Sync Pipeline (`ElevenLabs` + `FFmpeg` + Local `H3`)
1. **Stage 1 (`~34s` Multi-Inflection Golden Master):** `resources/eva_voice_master.wav` (`34.11s`, `44.1kHz`, `-16 LUFS`, `highpass=80Hz`, `2.5:1` gentle compression) captures `@Eva`'s natural Italian chest timbre, commas, and expressive peaks across 6 clips. Rebuild or create new avatar masters locally with **0 API calls**:
   ```bash
   python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --build-golden-sample <clips_dir>
   ```
2. **Stage 2 & 3 (Zero-Reroll Single-Pass Concatenated ElevenLabs STS + Locked `voice_settings`):**
   - Calling TTS/STS per clip resets neural pitch/room conditioning on every request. Instead, `elevenlabs_voice_ref.py --unify-dir` (single-pass concatenated mode by default):
     1. Pre-cleans every clip's audio (`highpass=80Hz, lowpass=14kHz, -2dB@250Hz, acompressor 2.5:1, -16 LUFS`) to strip room reverb differences between backgrounds;
     2. Concatenates all clips with `0.65s` digital silence markers and sends **ONE single API call** to `eleven_multilingual_sts_v2` with locked high-consistency settings (`stability=0.78`, `similarity_boost=0.86`, `style=0.0`, `use_speaker_boost=True`, `seed=424242`);
     3. Slices back at the exact RMS silence valleys, locks each clip's duration within `±1ms` of its video stream (`0.95x–1.05x`), normalizes to `-14.0 LUFS`, and remuxes (`-c:v copy`).
   - For multi-chunk synthetic TTS lines, pass `--stitch-file lines.txt` to chain `previous_request_ids` (rolling window up to 3 IDs).
   ```bash
   python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --check-env
   python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --clone-voice Eva --save-env
   python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --unify-dir freebuff-export/11-eva-vibe-coding/eva_clips
   ```
3. **Stage 4 (8-Band Spectral EQ + Dynamic Compression + `-14 LUFS` Match — `0` API Credits):**
   - Even locally without calling ElevenLabs (or right after STS/H3), lock all clips to one golden vocal EQ curve:
     ```bash
     python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py match-audio clip_02.mp4 --ref golden_04.mp4 --out clip_02_matched.mp4
     ```
4. **In-Generation Conditioning:**
   - **Local `MiniMax-H3 Ref2VA`:** Pass `--ref-audio resources/eva_voice_master.wav` (`34s` master) for native timbre lock.
   - **Seedance 2.5 / Higgsfield:** Attach `reference_voce.mp4` (`Shot Caller v2`) or saved `Character Element`.
   - **Google Flow:** Enable `@Voice` + include the verbatim `Voice Lock:` block in every prompt.

### Pillar 4 — Free-Duration Motion Without Looped V2V
- **When source talking-head cuts are `< 3s`** (like UI-heavy Reels where B-roll cards interrupt the speaker), **never loop short fragments**.
- Instead use **Start Frame (`master_room.png`) + Character Ingredient (`eva_con_tshirt.png`)** (or `MiniMax-H3 Ref2VA` `--ref-image`). This unlocks exact phrase durations (`4.2s–7.2s`), creates natural blinking/micro-nods/feminine hand gestures, and eliminates V2V duration locks and male-hand cloning.
- **When true V2V motion transfer IS desired:** Record or supply a **genuine, continuous, unlooped `6–8s` acting clip** with zero cuts and zero hands blocking the face/collar.

### Pillar 5 — Post-Production Visual & Timeline Cohesion
- **LAB Color/Luminance Matching:** Before editing in Remotion, normalize brightness and A/B skin/wall tones of Setup A clips to `master_muro_grigio.png` and Setup B clips to `master_armadio.png` (handled automatically in `ingest_eva_clips.py`).
- **Audio-First Remotion Timing:** Never crush natural Italian clips with `atempo > 1.08`; adapt Remotion `<Sequence>` durations, card animations, `KineticCaption.tsx`, and `OutroBlackCard` to Eva's real spoken beats, masking visual cuts under B-roll cards and J-cuts.

---

## 3. Google Flow Multi-Clip Workflow & Direct Automation

### Manual / UI Best Practices (`Omni 1.2 Flash`, `9:16`, `x1`)
- **Mode Choice:**
  - **Best for Star-Topology Consistency (Phase B):** Use **`Frames`** (upload `master_muro_grigio.png` or `master_armadio.png` as **Start Frame**, and optionally attach `eva_con_tshirt.png` in **Ingredients** if available in the active Flow build) OR **`Ingredients` (Images Only: `eva_con_tshirt.png` + `master_room.png`)** + **`Add Voices` (`@Voice`)**.
  - **Extend vs. New Clip:** Use **`Extend`** only to finish a single uninterrupted sentence in the *same* camera framing (`<= 1` hop). For new scenes, camera angles, or separate sentences, always start a fresh Star-Topology generation from `(master_room.png + eva_con_tshirt.png)` so facial geometry never drifts.
  - **One Beat Per Clip (`4.2s–7.2s`):** Never cram two rooms or complex multi-step physical actions into one prompt.

### Direct Automation: Subscription Credits (`gflow-cli`) vs Official Gemini API (`GEMINI_API_KEY`)
1. **Using Your Existing Google AI Pro / Ultra / Flow Subscription ($0 Extra Deposit — Recommended):**
   - **Why Gemini API asks for money even with Google AI Pro/Ultra:** Google AI Pro ($10/mo developer credit) and Ultra ($40–$100/mo developer credit) include monthly Google Developer Program credits, **but Google AI Studio requires an initial $5 USD prepaid Cloud Billing deposit** to activate API keys.
   - **Your Google Flow web credits (`labs.google/fx/tools/flow`) require $0 extra deposit.** To automate Flow cleanly from the terminal without the slow visual browser agent, install and use **`gflow-cli`** (`uv tool install gflow-cli` — verified installed `0.101.2` at `C:\Users\empi0\.local\bin\gflow.exe`):
     ```powershell
     # One-time login in a real Chrome window on the user's visible Windows desktop:
     # Note: terminal tool shells may run in an isolated desktop (`exebox`), so for the very first login have the user run via Win+R:
     C:\Users\empi0\.local\bin\gflow.exe auth login --browser chrome

     # Pre-flight session & balance check ($0 cost — note command is `credits user`, not bare `credits`)
     gflow auth status
     gflow credits user

     # Strict Single-Model Rule: pin ONE model & lowest credit tier (--model omni-1.2-flash --resolution 360p, ~5 credits/clip)
     # Never auto-fallback to veo-fast mid-video (breaks visual/voice coherence). Rejected status-4 runs spend 0 credits.
     gflow video r2v "<PROMPT>" `
       --ref "freebuff-export/11-eva-vibe-coding/eva_con_tshirt.png" `
       --ref "freebuff-export/11-eva-vibe-coding/master_muro_grigio.png" `
       --model omni-1.2-flash --aspect 9:16 --duration 5 --resolution 360p --count 1 `
       --out-file "freebuff-export/11-eva-vibe-coding/eva_clips/eva_02.mp4"

     # Reusable skill post-production toolkit (trim silence, fix over-bright Flow clips with gamma=1.10 at 0 credits, build true-alpha 3D pop-out PIP):
     python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py check
     python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py trim raw.mp4 --out trimmed.mp4
     python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py grade trimmed.mp4 --out graded.mp4 --room light-wall
     python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py popout-pip graded.mp4 --out pip.webm
     ```
   - *(Note: `gflow` also includes an MCP server via `gflow mcp setup` / `gflow mcp run stdio`, plus alternative bridges `kodelyx/flow-agent` and `TMSSS05/google-flow-browser-mcp`. For Reel 11, run `python freebuff-export/11-eva-vibe-coding/run_gflow_reel11.py`.)*

2. **Official Gemini API `Gemini Omni 1.2 Flash` (`gemini-omni-1.2-flash` via `GEMINI_API_KEY`):** Installed via the **`Gemini API`** plugin (`gemini-omni-flash-api` skill + `google-genai >= 2.30.1` Interactions API, or `gemini-api video -m gemini-omni-1.2-flash`), using **`GEMINI_API_KEY`** (requires AI Studio billing + monthly Developer Program credits if claimed):
  - Supports `--first-frame` (`master_muro_grigio.png` / `master_armadio.png`), `--image` (`eva_con_tshirt.png`, up to 6 reference images), `--aspect-ratio 9:16`, `--resolution` (`360p` / `720p` / `1080p` / `4k`), `--duration 3..15`, and **`--batch jobs.json --concurrency 3`** for parallel multi-clip generation!
  - **EEA / UK / Switzerland note:** Uploading *videos* (`--video-reference` / `--video`) via the Omni Flash API is restricted in the EEA/CH/UK, **whereas `--first-frame` + `--image` (our Star Topology PNG workflow) uses images only** and avoids video uploads completely.
  - **Command example:**
    ```bash
    python "C:\Users\empi0\.gemini\config\plugins\gemini-api\skills\gemini-omni-flash-api\scripts\video\generate_video.py" ^
      "Use the first image as the starting frame and keep the exact woman shown in the second image..." ^
      --first-frame "freebuff-export/11-eva-vibe-coding/master_muro_grigio.png" ^
      --image "freebuff-export/11-eva-vibe-coding/eva_con_tshirt.png" ^
      --aspect-ratio 9:16 --resolution 720p --duration 5 ^
      --output "freebuff-export/11-eva-vibe-coding/eva_clips/eva_02.mp4"
    ```
- **Official Gemini API `Veo` fallback (`scripts/gemini_veo_video.py`):** Calls `veo-3.0-generate-preview` / `veo-2.0-generate-001` via `predictLongRunning` using `GEMINI_API_KEY` (`python .agents/skills/reel-avatar-cloner/scripts/gemini_veo_video.py --check-env`).

---

## 4. Local Generation on PC: Unsloth Studio + `MiniMax-H3 Ref2VA`

This workstation has **Unsloth Studio** + **`sd-cli.exe`** (`stable-diffusion.cpp`) + complete **`unsloth/MiniMax-H3-GGUF`** multimodal audio-video weights installed locally on `D:\AI\hf\hub\`:

- **Verified Installed Components:**
  - `minimax_h3_ref2va_pruned-Q3_K.gguf` (`8.12 GiB` — Ref2VA multimodal denoiser)
  - `qwen3vl_32b_minimax_h3-Q4_K_M.gguf` (`16.97 GiB` — Qwen3-VL multimodal text/image/audio conditioner)
  - `minimax_h3_video_vae_fp16.safetensors` (`4.85 GiB`)
  - `minimax_h3_audio_vae_fp32.safetensors` (`0.56 GiB`)
  - `C:\Users\empi0\.unsloth\stable-diffusion.cpp\sd-cli.exe`
  - Master Italian voice reference: `resources/eva_voice_master.wav` (`5.2s` extracted from `eva_01.mp4`)

### How `MiniMax-H3 Ref2VA` Solves Consistency Locally
- **Inputs supported simultaneously:** Up to **9 reference images** (`--ref-image`), **3 reference audio tracks** (`--ref-audio`), and **3 reference videos** (`--ref-video`).
- **Role tagging in prompt:**
  - `<Subject 1>` / `Image 1`: `resources/eva_con_tshirt.png` (locks Eva's face, glasses, bun, charcoal t-shirt, gold chain).
  - `Image 2`: `master_muro_grigio.png` or `master_armadio.png` (locks exact room wall/wardrobe, window daylight, framing).
  - `Audio 1`: `resources/eva_voice_master.wav` (locks Eva's Italian vocal timbre & room acoustics — `MiniMax-H3` generates synchronized **video + stereo Italian speech audio natively in one pass!**).
- **Mandatory Temporal & Resolution Rules (from `video_families.py` / `video_minimax_h3.py`):**
  - **Temporal Lattice (`17k + 5` frames @ `24fps`):** Valid frame counts are `124` (`5.17s`), `141` (`5.88s`), `158` (`6.58s`), `175` (`7.29s`), `192` (`8.00s`), up to `345` (`14.38s`).
  - **Canvas Multiple:** Width and height must be multiples of `32`. For vertical `9:16` on an **AMD RX 6600 (8 GB VRAM)** with `--offload-to-cpu` + `--vae-tiling`, use **`480x864`** (fast) or **`544x960`** (higher detail), `steps = 20` (or `8–12` for rapid test iterations), `cfg-scale = 1.0`, `flow-shift = 12`, `sampling-method = res_multistep`, `scheduler = simple`.
  - **Never mix keyframes and references:** `minimax_h3_ref2va_pruned` uses `--ref-image` / `--ref-audio` / `--ref-video` (NOT `--init-img` / `--end-img`, which belong to the separate `fl2va` partition).

### Local CLI Bridge (`scripts/unsloth_h3_video.py`)
```bash
# 1. Verify all local MiniMax-H3 weights, VAEs, voice ref, and sd-cli DLL paths
python .agents/skills/reel-avatar-cloner/scripts/unsloth_h3_video.py --check

# 2. Generate a consistent 9:16 spoken clip locally with Eva's face + room still + voice WAV
python .agents/skills/reel-avatar-cloner/scripts/unsloth_h3_video.py ^
  --ref-image "freebuff-export/11-eva-vibe-coding/eva_con_tshirt.png" ^
  --ref-image "freebuff-export/11-eva-vibe-coding/master_muro_grigio.png" ^
  --ref-audio ".agents/skills/reel-avatar-cloner/resources/eva_voice_master.wav" ^
  --seconds 5.17 --width 480 --height 864 --steps 20 --seed 102 ^
  --prompt "Vertical 9:16 handheld smartphone front-camera portrait of <Subject 1> from Image 1 in the exact room from Image 2, speaking Italian in the exact voice of Audio 1: 'Si chiama Freebuff, ed è un agente di coding proprio uguale a Claude Code.'" ^
  --out "freebuff-export/11-eva-vibe-coding/eva_clips/eva_02_h3.mp4"
```

### Hybrid Workflow Recommendation (Best Quality + Speed on RX 6600)
- **Fastest high-res talking head:** Run **Google Flow (`Omni 1.2 Flash`)** using **Star Topology** (`master_muro_grigio.png` / `master_armadio.png` + `eva_con_tshirt.png` in `Frames`/`Ingredients`, automated via `browser` subagent or `gflow-cli` if logged in, or copy-paste).
- **100% offline / zero-filter / unlimited retries:** Run **`unsloth_h3_video.py` (`MiniMax-H3 Ref2VA`)** locally overnight or in background batches with `eva_con_tshirt.png` + `master_*.png` + `eva_voice_master.wav` (no NSFW false positives, no `?p=speech_edit`, native voice cloning).
- **Consistent Keyframe / Room Stills (`FLUX.3 Klein Q5_K_M`):** When creating a brand-new background room for Eva before generating video, use `FLUX.3 Klein` (`workflow="reference"`, up to 10 condition images) in Unsloth Studio to render sharp `768x1344` master room plates first, then animate them in Flow or MiniMax-H3!
