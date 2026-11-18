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

### Pillar 1 — Locked Dressed Identity Anchor (Never Head-Only)
- Keep one canonical portrait showing face, hair, eyewear, jewelry, AND exact top/neckline (`resources/eva_con_tshirt.png`), or a 3-panel neutral 18% gray `Cast Kit v1` sheet.
- Never contradict the anchor image inside the text prompt (e.g., don't ask for a different top when attaching `eva_con_tshirt.png`).

### Pillar 2 — Star Topology via Master Scene Stills (Never Daisy-Chain Clips)
- **Why daisy-chaining fails:** Feeding `Clip 1 -> Clip 2 -> Clip 3 -> Clip 4` compounds compression blur, color shift, and facial geometry drift after 2–3 hops.
- **How Star Topology works:**
  1. **Group by unique room/camera setup** (e.g., Reel 11 has only 2 setups: Setup A = *Pale-Grey Wall*, Setup B = *Warm Wooden Wardrobe*).
  2. **Phase A (Masters):** Generate **1 Master Clip per unique room setup** first (`eva_01`, `eva_04`). Inspect eyes, hands, wardrobe, framing, and Italian pronunciation.
  3. **Extract Clean Master Stills:** Grab one hand-free, neutral/mid-smile, sharp frame per setup (`master_muro_grigio.png`, `master_armadio.png`).
  4. **Phase B (Spokes):** Anchor **every remaining clip** directly to the immutable hub `(master_room.png + eva_con_tshirt.png)` — never from intermediate Phase B clips. Every spoke stays at generation distance `1` from the master room and character anchor.

### Pillar 3 — 2-Layer Voice Consistency Lock
1. **Layer 1 (In-Generation Acoustic Conditioning):**
   - **Local `MiniMax-H3 Ref2VA`:** Pass `--ref-audio resources/eva_voice_master.wav` (extracted directly from `eva_01.mp4`) so both timbre and room acoustics lock natively.
   - **Seedance 2.5 / Higgsfield:** Attach whole-second `reference_voce.mp4` (`Shot Caller v2`) as `@video1` / Element `@eva-voice-ref`.
   - **Google Flow:** Enable `@Voice` / `Add Voices` + include identical `Voice Lock:` block (`26-year-old female Northern Italian speaker, crisp warm mid-alto chest voice, natural conversational pitch around 195Hz, steady dynamic consistency, close-mic dry smartphone room acoustics, zero background music`).
2. **Layer 2 (Zero-Reroll Acoustic Unification via `scripts/elevenlabs_voice_ref.py`):**
   - If a generated clip has great face, eye contact, and hands, **do NOT burn credits regenerating it** just because vocal tone or room reverb drifted slightly.
   - Clone `resources/eva_voice_master.wav` once and batch-unify every generated `.mp4` via ElevenLabs Speech-to-Speech (`eleven_multilingual_sts_v2`, preserving exact millisecond syllable & lip-sync timing):
     ```bash
     # 1. Check .env (needs ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID)
     python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --check-env

     # 2. (Optional, one-time) Clone Eva's voice from eva_voice_master.wav and save voice_id to .env
     python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --clone-voice Eva --save-env

     # 3. Unify a single clip OR an entire folder of MP4 clips
     python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --s2s-in clip.mp4
     python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --unify-dir freebuff-export/11-eva-vibe-coding/eva_clips

     # 4. Or run end-to-end inside Reel 11 ingestion (ElevenLabs STS + LAB color match + loudnorm)
     python freebuff-export/11-eva-vibe-coding/ingest_eva_clips.py --dir freebuff-export/11-eva-vibe-coding/eva_clips --unify-elevenlabs
     ```

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
