# Artistic Direction, Natural Motion & 1:1 Reference Cloning Playbook

End-to-end guide for turning **any uploaded reference Reel/TikTok + user customizations** into a coherent, lifelike **`@Eva`** vertical video (`1080x1920 @ 30fps`) that looks **100% real (never AI)**, keeps `@Eva`'s face, wardrobe, room lighting, and voice locked across every cut, and minimizes Google Flow credit spend.

---

## 1. Standard Intake Workflow: Reference Video + `@Eva` + Custom Edits

Whenever the user sends a reference MP4 and asks to recreate it with `@Eva` (with optional changes like hiding a brand name, updating prices, or producing Instagram + TikTok variants), execute these steps in order:

### Step A — 1:1 Visual Concept & Framing Audit (Before Drafting Any Prompt)
1. **Generate a 1fps contact sheet of the original video (`sheet_orig.jpg`)** plus tight zoomed crops (`orig_pip_crop.jpg`) of any talking-head PIP overlays.
2. **Audit every structural element so the remake matches the original concept 1:1:**
   - **PIP Card Geometry & 3D Pop-Out:** Check whether the original speaker sits inside a rounded bottom PIP card (`y = 1206..1920`) OR whether the top of their head/hair breaks out 3D above the card border (`y = 1070..1206`). When it pops out, ALWAYS use `scripts/gflow_batch_ingest.py popout-pip` (`1036x850` VP9 `yuva420p` `.webm` + Remotion `<OffthreadVideo transparent />`) — never chop the hair flat with CSS `overflow: hidden`.
   - **Body & Gesture Framing Inside PIP:** Original creators show forehead to chest/hands inside the PIP card. Never crop forehead-to-chin; frame chest-up (`scale_w=720, scale_h=1280, y_offset=42`) so shoulders, matte black t-shirt, thin gold chain, and raised hands are clearly visible.
   - **Transition & Fullscreen Rhythm:** Do **NOT** invent flashy transitions (`WarmFlashTransition` / heavy orange light-leaks) that aren't clean in context, and avoid jarring sub-1s talking-head flashes (`0.5s–0.7s`). Widen short fullscreen speaker cuts cleanly to **`1.1s–2.3s`** while keeping kinetic captions locked to those boundaries.
   - **Original UI Graphics:** Reuse cleaned real B-roll via `temporal_4dof` when panning/handheld phone shots are great, OR rebuild vector UI/terminal/browser cards 1:1 in **Remotion** (`Cards.tsx`, `1080x1920`) so typography stays retina-sharp.

### Step B — Apply User Customizations (Brand Redaction & Platform CTAs)
Before generating any voice clip, lock a final shot-by-shot Italian script + UI redaction checklist with the user:
1. **Curiosity-Gap Brand Redaction (When Requested, e.g. Never Name `Freebuff`):**
   - **Audio & Flow prompt:** Replace `"Si chiama [App]..."` with `"È un nuovo strumento gratuito..."`.
   - **Kinetic captions:** Replace `'SI CHIAMA [APP]'` with `'È UN NUOVO STRUMENTO'`.
   - **Remotion UI Cards (`Cards.tsx`):** Replace browser URL bars (`freebuff.com` -> `••••••••.com`), brand squircle label (`Freebuff` -> `••••••••`), terminal install/run commands (`npm install -g ••••••••`), and DM notification cards (`Agente AI Gratis / il nome + il link`). Verify zero occurrences remain via `Select-String`.
2. **Dual Final Clips for Instagram vs. TikTok (`eva_06_ig` + `eva_06_tiktok`):**
   - **Instagram cut (`FINAL-*-INSTAGRAM.mp4`):**
     - Spoken closing line (`omni-1.2-flash` safe wording): `"Seguici e scrivi promo nei commenti per provare subito questo agente gratuito."`
     - On-screen cards: `CommentBoxCard` (`title="Commenti"`, `keyword="PROMO"`) + `OutroBlackCard` (`leadText="seguici e commenta"`, `keyword="PROMO"`).
   - **TikTok cut (`FINAL-*-TIKTOK.mp4`):**
     - Spoken closing line (`omni-1.2-flash` safe wording): `"Seguici sul profilo e scrivi promo per provare subito questo agente gratuito."`
     - On-screen cards: `CommentBoxCard` (`title="Scrivi in DM"`, `keyword="PROMO"`), captions `SEGUICI SUL PROFILO / E SCRIVI "PROMO" / IN DM PER PROVARE`, and `OutroBlackCard` (`leadText="seguici e scrivici in DM"`, `keyword="PROMO"`).

### Step C — Single-Face Multi-Room Relighting & Credit-Minimizing Generation (`gflow-cli`)
1. **Strict Single-Model & Single-Face Anchor Rule:** Generate ALL spoken clips for one video using the **same model and resolution** (`--model omni-1.2-flash --resolution 360p`, **~5 Flow credits/clip**, never switch to `veo-fast` mid-reel). Start every room from `@Eva`'s preferred canonical smartphone UGC anchor ([resources/eva_canonical_warm_armadio.png](../resources/eva_canonical_warm_armadio.png)); for a secondary background, run **`gen-room-anchor`** (Joey `@noisygroup` *Stills-First Change-One-Variable & Relight* via `i2i`) instead of blending two conflicting face sheets in `r2v`.
2. **Pre-Flight Check (`$0` credits):**
   ```powershell
   python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py check
   ```
3. **2-Phase Star Topology + User Checkpoint:** Generate Phase A (1 master per room) first -> verify eyes/hands/speech via `read_file` -> extract clean closed-mouth rest stills via `gflow_batch_ingest.py pick-anchor` when needed -> generate Phase B anchored cleanly to its room hub -> pause for user check on raw clips if requested before final CTA clips.
4. **Never Spend Credits Fixing Brightness:** If raw `r2v` clips look slightly bright (*"accesi"*), correct exposure and contrast in post with `gflow_batch_ingest.py grade` (`gamma = 1.10`) at **0 credits**.

---

## 2. Artistic & Realism Direction ("Deve Sembrare Vero e Non AI")

### A. Visual & Optical Look (Anti-AI Slop)
Every `@Eva` prompt MUST replicate authentic smartphone UGC aesthetics rather than glossy studio CGI:
- **Camera & Framing:** `"Vertical 9:16 handheld smartphone front-camera medium-close chest-up portrait shot from arm's length with 15% clean wall headroom above her high dark-brown bun and full shoulders visible"` (NEVER `"selfie"`, `"studio"`, `"cinematic"`, `"8K"`, `"4K"`, or `"ring light"`).
- **Lighting & Sensor Grain:** `"matching the exact pale-grey plaster wall background / warm cream wardrobe corner daylight, uneven soft natural indoor window shadows, subtle organic handheld micro-movement, authentic smartphone sensor grain"`.
- **Biological Skin & Optics:** `"realistic natural skin pores and fine peach fuzz, genuine natural under-eye contours, organic blinking cadence, moist corneal catchlights behind her round tortoiseshell glasses, matte charcoal-black cotton fabric texture, delicate thin gold chain"`.
- **Anti-Drift Negatives:** `"No extra or warped fingers, no rings, no plastic or airbrushed skin, no beauty smoothing filters, no subtitles, no floating UI text, no wardrobe change, no CGI glow, no morph cuts."`

### B. The 5 Physical Acting Laws (Fixing Static / Robotic Delivery)
Generated talking heads feel "AI" when the head stays centered like a passport photo and nothing moves except the mouth. Force authentic human creator energy into every prompt:
1. **Headroom + Full Chest Visibility:** Keep ~15% clean wall space above her high bun so dynamic head movement and 3D pop-out cutouts never clip her hair, while keeping collar, chain, shoulders, and hands in frame.
2. **Axial Forward Lean on Key Beats:** Include *"leaning subtly forward toward the camera lens on key emphases with organic shoulder/torso breathing weight shifts, never frozen vertically"*.
3. **Spatial Eye/Card Awareness (When UI Graphics Sit Above Eva):** When `@Eva` appears in a bottom PIP below UI cards, add a micro-interaction beat: *"glancing briefly upward toward the upper-center frame before locking her dark-brown irises back onto the lens center"*.
4. **Varied Hand Choreography Per Clip (Never Repeat Consecutive Gestures):** Rotate across concrete, single-beat feminine gestures:
   - Clip 1: *counting two subtle beats lightly on fingers near the lower foreground before relaxing*
   - Clip 2: *raising one open graceful female palm briefly at chest height in a welcoming explanatory gesture*
   - Clip 3a: *tilting her head gently to camera-right with an amused knowing expression and casual shoulder drop*
   - Clip 3b/4: *pointing lightly upward once toward the upper frame with a graceful female index finger while nodding naturally*
   - Clip 5/6: *subtle open-hand palm turn at lower-chest level paired with a warm engaging smile*
5. **Post-Production Handheld Camera Motion in Remotion (`SpeakerPipAndFull.tsx`):**
   Even cleanly acted AI clips become noticeably more alive when composited with subtle real-camera physics:
   - **`PipSpeaker`:** `transformOrigin: '50% 100%'`, gentle breathing sway `translateX: Math.sin(local / 12) * 3.5`, subtle tilt `rotate: Math.sin(local / 9) * 0.35deg`, and slow push-in `scale: 1.0 -> 1.03`.
   - **`FullscreenSpeaker`:** Dynamic engagement zoom `scale: 1.0 -> 1.055` paired with smooth handheld drift `translate(Math.sin(local / 7) * 5, Math.cos(local / 9) * 4)`.

### C. Spoken Italian Diction & 4-Stage Broadcast Voice Lock
- Keep identical acoustic lock in every Flow prompt:
  `Voice Lock: 26-year-old female Northern Italian speaker, crisp warm mid-alto chest voice, natural conversational pitch around 195Hz, steady dynamic consistency, close-mic dry smartphone room acoustics, zero background music.`
- Write numbers and acronyms phonetically in Italian (`"cento euro"`, `"dalle dieci alle venti ore"`, `"cinque ore"`, `"GPT sei"`, `"G-L-M"`), punctuate commas intentionally, and use `"clear well-articulated Italian diction without rushing, pausing cleanly on every comma"`.
- **Zero-Drift Post-Production Voice Pipeline (`elevenlabs_voice_ref.py` + `match-audio`):**
  1. Clone `@Eva`'s `~34s` multi-inflection golden master (`resources/eva_voice_master.wav`, rebuildable via `--build-golden-sample`) once (`--clone-voice Eva --save-env`).
  2. Unify all generated `.mp4` clips in **ONE single concatenated Speech-to-Speech API call** (`--unify-dir`, default single-pass mode: de-rooms audio -> `eleven_multilingual_sts_v2` with `stability=0.78, similarity_boost=0.86, style=0.0, use_speaker_boost=True, seed=424242` -> slices at silence valleys -> locks exact millisecond lip-sync at `-14 LUFS`).
  3. Match spectral balance locally across rooms at **0 API cost** via `gflow_batch_ingest.py match-audio clip.mp4 --ref golden.mp4 --out matched.mp4` (`highpass=80Hz` + 8-band EQ + `2.5:1` gentle compression + 2-pass linear `-14 LUFS`).

### D. 5-Block Anti-AI UGC + `MCSLA` Prompt Architecture (YouTube `@noisygroup` / `higgsfield-ai` / Reddit Proven)
Keep total prompt length focused (`< 200` words core `MCSLA`: *Model/Optics · Camera · Subject · Look/Light · Action*) assembled in 5 clean blocks so identity never drifts into glossy AI:
1. **`[Shot & Optics]`:** Vertical 9:16 handheld smartphone front camera (`24mm`), arm's-length medium-close chest-up portrait (`15%` clean wall headroom above her dark-brown bun), subtle organic handheld micro-jitter.
2. **`[Environment & Relighting Direction]`:** Explicit room & directional light physics from the locked still (`"soft window daylight hitting the camera-left cheekbone and wrapping subtly around tortoiseshell glasses & wispy curls"`, matching `eva_canonical_warm_armadio.png` or `gen-room-anchor` output).
3. **`[Subject & Verbatim Biological Tokens]`:** Keep descriptive tokens 100% identical across all scenes: pores + peach fuzz, mild under-eye contour, small cheek beauty mark under left eye, dark-brown messy high bun, round tortoiseshell eyeglasses, matte charcoal-black crew-neck cotton t-shirt, thin gold chain.
4. **`[Physical Choreography]`:** One concrete action beat per clip: subtle axial forward lean on the hook (`"leaning gently toward the lens"`), brief upward spatial glance/point toward upper UI cards when in PIP (`"glancing briefly toward the upper frame before locking dark-brown eyes onto the lens"`), one varied chest-level female hand gesture, natural breath pause at commas.
5. **`[Dry Close-Mic Acoustics & Anti-CGI Negatives]`:** `"Voice Lock: 26-year-old female Northern Italian speaker..."` + spoken line verbatim with phonetic numerals + `"No extra or warped fingers, no rings, no plastic airbrushed skin, no beauty filter, no ring light, no subtitles, no music."`

### E. High-Retention Voiceover Counterpoint, Open-Loop & Expressive TTS Rhythm Law (`v2.2.0`)
Whenever adding a voiceover track over motion-graphics or UI screen videos (no talking head needed):
1. **Counterpoint vs. On-Screen Text (Zero Redundant Reading):** Never read the bottom kinetic caption word-for-word when the UI card above holds richer visual proof. While the viewer's eyes read the short subtitle (`"gli dai un bug e lui lo riproduce"`), let `@Eva`'s voice name concrete details inside the screen (`"venti test"`, `"due righe"`, `"in un minuto"`, `"gratis"`), creating dual-channel curiosity rather than sensory fatigue.
2. **High-Burstiness Expressive Cadence + Open Loops:** Avoid monotonous uniform 10-word sentences. Open an unresolved cost/curiosity loop in the first `0.0–1.5s`, slam the payoff at `1.5–3.2s`, mix 1–3 word micro-punches (`"Fermati."`, `"Poi?"`, `"La parte folle?"`) with sharp `8–12` word clauses, and insert ellipses (`...`) for organic breath pauses. Close on a **Zeigarnik micro-task** (`"Seguici e scrivimi promo in D-M..."` / `"scrivi promo nei commenti"`).
3. **Expressive TTS vs. STS Slider Law (`elevenlabs_voice_ref.py`):**
   - Speech-to-Speech (`--unify-dir`) keeps high stability (`0.78`, `style=0.0`) because human inflection already lives in the driving audio.
   - Pure Text-to-Speech voiceovers (`--expressive-tts`) MUST lower stability (`stability=0.42, similarity_boost=0.84, style=0.18, speed=0.98`) with inline `eleven_v4`/`eleven_v3` emotional tags (`[skeptical]`, `[excited]`, `[confident]`, `[warmly]`) and Request Stitching (`previous_request_ids`) so cadence sounds energetic, punchy, and human.
   - Sync scenes accurately to visual cut frames via `--timeline-json <scenes.json> --expressive-tts --video-in <src.mp4> --video-out <out.mp4>` (or `--timeline-audio-dir` for Web-generated MP3s), mastering at `-14.0 LUFS` without truncating words.

---

## 3. Integrated Skill Ecosystem & Cross-Skill Doctrines (Never Reinvent from Scratch)

`reel-avatar-cloner` acts as the avatar & Flow/H3 orchestrator and directly integrates the specialized skills already installed in `.agents/skills/` rather than duplicating their logic:

### A. Frame-Exact Measurement & Rebuild (`reverse-any-video`)
Load [reverse-any-video/references/match.md](../../reverse-any-video/references/match.md) and [reverse-any-video/references/people.md](../../reverse-any-video/references/people.md) during Step A:
- **Exact cut & landing frames:** Read consecutive frames around every entrance, exit, and graphic switch (`frame / fps` rounded down). An element that lands in 1 frame is a `set`, not a tween; only tween what visibly moves across multiple frames.
- **Size text from its ink (not by eye):** Crop the text line in the original frame and compare pixel ink bounding-box width & height against your Remotion card snapshot; tune `fontSize` and `letterSpacing` until both agree within a few pixels.
- **Pixel-band caption timing:** Measure caption group switches from the caption band pixels (`npx hyperframes measure events <video> --roi <band>`), because captions often lead or trail spoken words by a few frames.
- **One shot per original shot:** Never generate a single AI video across a jump cut or punch-in; split cleanly at cut boundaries first.
- **Seeked-timeline optical recipes:** Use SVG directional `<feGaussianBlur stdDeviation="24 0">` along motion direction (never symmetric CSS `blur()`), `clip-path: inset()` progressive text sweeps, SVG `feTurbulence` + `feDisplacementMap` glass type, and stepped `feTurbulence` film grain on flat vector backgrounds.

### B. Continuity, Curves & Causal UI Ignition (`motion-doctrine`, `cut-the-curve`, `seam-craft`, `oversized-cursor`)
Load [motion-doctrine/SKILL.md](../../motion-doctrine/SKILL.md) and [cut-the-curve/SKILL.md](../../cut-the-curve/SKILL.md) before authoring any card transition or camera motion:
- **The Vector Law:** How Scene A exits dictates how Scene B enters — same axis (`X / Y / Z`), same signed direction (never mirror Z `grow` exit into `shrink` entry), matched mid-flight velocity via mirrored `power4.in` -> hard cut -> `power4.out` curves, landing cuts mid-motion rather than from/to dead rest.
- **The 5 Velocity-Matched Seams (`cut-the-curve` §1–5):**
  1. **Zoom-Through (forward push):** Within-scene text swap (`scale 1 -> 1.2` with linear opacity `1 -> 0.15` over `0.2s power3.in`, hard swap at peak blur `10px`, incoming `0.75 -> 1` in `0.5s expo.out`).
  2. **Inverse Zoom-Through (arrival pull):** Payoff/reveal beat (`scale 1 -> 0.8` out, hard swap at peak blur, incoming `1.25 -> 1` retracting into frame).
  3. **Cut-the-Curve (default scene boundary):** Partial travel `±230px` (`~12%` of 1920) along the film's current (`power4.in` exit fade completing by ~25–30% travel + `power4.out` entry igniting at `0.35` opacity).
  4. **Waterfall Cut (`cut-the-curve` §4):** Word-by-word `±230px` leftward stagger (`+0.022s` exit stagger, `0.05s × 0.84` decaying entry stagger) across text-to-text beats.
  5. **Rack-Focus Blur-Cut (`cut-the-curve` §5):** Handheld DSLR focus pull (`0px -> 8–12px` peak blur at swap `-> 0px` with `~1.06` lens breathing) for same-surface state switches (`<= 1` per ~8s). Blur wrappers, never `<video>` elements directly; keep peak blur `10px` on text vs `18–20px` on full-frame cards.
- **In-Scene Arrival & Repositioning (`cut-the-curve` §6–7):**
  - **Waterfall Entry (§6):** Binary `0 -> 1` opacity (`tl.set` / immediate frame visibility — never opacity-fade an arrival), weighted `Y` slide from below (`60–80px` anchor in `0.16–0.20s`, `40–50px` word in `0.13–0.16s`, `30–48px` punctuation in `0.10–0.13s`), `power4.out` / `expo.out`, overlapping by `1–2 frames`.
  - **Nudge Curve (§7):** Three-phase `slow-fast-slow` group slide so cards stay readable instead of smacking on `inOut`: Ramp-in `~10%` distance / `~20%` time (`power3.in`) -> Burst `~65%` distance / `~18%` time (`linear`) -> Tail `~25%` distance / `~62%` time (`power4.out`, tail >= 3x ramp-in duration).
- **Ban on Idle Wobble & Stillness-Before-Climax (`motion-doctrine`):** Never add pointless sine glow/float loops on static UI cards; keep scenes performing (staged reveals, camera travel, sequenced UI ticks, or cursor-led triggers) and insert a **`0.3–0.75s` stillness comma** right before the climax card or CTA payoff.
- **Causal UI Clicks ([oversized-cursor/SKILL.md](../../oversized-cursor/SKILL.md)):** Use a **`7cqw` full-frame** (`4.6–5.5cqw` inside mock UI) macOS arrow or brand cursor entering from off-screen (`top: 115%`) along one clean vector, pivoting tip-tap compress/release (`1:2` `scale: 0.84 -> 1.0`, `transformOrigin: '21% 14%'`) to ignite UI morphs, typing runs, or toggles on the exact click frame, then exiting physically off-edge.
- **White-Flash Guard ([seam-craft/SKILL.md](../../seam-craft/SKILL.md)):** Always keep `#root` painted with an opaque canvas background (`background: var(--canvas-deep, #0B0D13)`) so mid-transition opacity dips never flash white, and never flash orange/white light leaks across a persistent PIP speaker.

### C. `drop / rail / embed` Captions & 3-Layer Depth Sandwich (`captions-overlay`, `remotion-captions`, `@remotion/video-matting`)
Load [captions-overlay/SKILL.md](../../captions-overlay/SKILL.md), [remotion-captions/SKILL.md](../../remotion-captions/SKILL.md), and [remotion-markup/video-matting.md](../../remotion-markup/video-matting.md):
- **The `drop / rail / embed` Hierarchy:**
  - **`drop`:** Silence, breaths, and stutters show zero text.
  - **`rail` (default):** Verbatim spoken captions on a clean lower-third/center overlay in front (`@remotion/captions` word timing), using accent word pops (`emphasis`) rather than shrinking or shoving scene layouts upward.
  - **`embed` (scarce climax):** At most `<= 1` promoted punch word per beat (never two adjacent), scaled bold and **composited BEHIND `@Eva`'s cutout silhouette**!
- **3-Layer Depth Sandwich (Text Behind `@Eva`):**
  For fullscreen or PIP depth beats, reuse either `gflow_batch_ingest.py popout-pip` (VP9 `yuva420p` `.webm`) or `@remotion/video-matting` (`separateVideoLayers({src, model: 'modnet'})`) and stack in Remotion (`remotion-markup/video-matting.md`):
  1. Back: `Background / Base Shot / UI Card`
  2. Middle: `Embedded Climax Headline` (occluded behind shoulders/hair!)
  3. Front: `Transparent WebM @Eva Foreground` (`<OffthreadVideo transparent />` muted)
  4. Top Overlay: `Verbatim Rail Caption` (`y = H / 2` layout respected; captions never carve a dead bottom zone)

### D. Sound Design, J-Cuts & Adaptive Silence (`remotion-markup`, `media-use`)
Load [remotion-markup/sfx.md](../../remotion-markup/sfx.md), [remotion-markup/silence-detection.md](../../remotion-markup/silence-detection.md), and [media-use/SKILL.md](../../media-use/SKILL.md):
- **Adaptive 2-Pass Silence Trim:** Run `python scripts/gflow_batch_ingest.py trim <clip.mp4> --out <trimmed.mp4> --adaptive-loudnorm` to compute EBU R128 `input_thresh` dynamically before trimming leading/trailing silence (safe fallback `-32dB`).
- **Audio J-Cuts & L-Cuts Across Scene Cuts:** In Remotion, separate `<Audio>` and `<Video>` offsets by **`3–5 frames` (`0.10–0.16s` at 30fps)** on hard cuts (incoming clause audio starts 3 frames *before* the visual cut onto `@Eva` or the UI card) to erase robotic stop-start pacing.
- **Micro-SFX Layering & Loudness Discipline:** Sweeten card reveals, cursor clicks, text sweeps, and ding notifications with crisp `<Audio>` SFX (`whoosh.wav`, `whip.wav`, `mouse-click.wav`, `switch.wav`, `ding.wav`, `page-turn.wav`, `shutter-modern.wav`) mixed around **`-24 to -28 dBFS`** so `@Eva`'s **`-14 LUFS`** speech remains crisp and forward. Always normalize levels and mix cleanly via `media-use` rules when BGM is present.

### E. High-Retention Hooks & Humanized Italian Copy (`ig-reel`, `ig-human`)
Load [ig-reel/SKILL.md](../../ig-reel/SKILL.md) and [ig-human/SKILL.md](../../ig-human/SKILL.md) whenever writing or adapting the script and post copy:
- **Hook Scoring & Beat Pacing:** Classify and score spoken + on-screen hooks (`6` words max on-screen at frame 1 inside `y = 230..1440`, clear of right `230px` UI rail) with `python .agents/skills/ig-reel/hookscore.py` against the 26 formulas in [hooks.json](../../ig-reel/hooks.json), and validate beat transitions (`<= 4s` per beat, loop echo on last line) with `python .agents/skills/ig-reel/beats.py --target <sec>`.
- **Zero-Slop De-AI Pass:** Run every script, caption, and CTA through `python .agents/skills/ig-human/humanize.py --report` and `detect.py` (target overall score **`>= 70 PASS`**, zero em-dashes, zero hidden characters, zero cliché triads or `"Stop scrolling"` / `"Non è X, è Y"` AI structures).

---

## 4. Reusable Pipeline & Remotion Patterns

### A. True-Alpha 3D Pop-Out PIP (`gflow_batch_ingest.py` + Remotion `OffthreadVideo transparent`)
Never use a solid rectangular `overflow: hidden` crop when the original Reel has head/hair extending above a rounded card. Instead:
1. Run `gflow_batch_ingest.py` (`trim` -> `grade` -> `popout-pip`) so each PIP clip becomes a `1036x850` VP9 `.webm` (`-pix_fmt yuva420p -auto-alt-ref 0`) with true alpha transparency around the top of the bun:
   ```powershell
   python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py popout-pip `
     clip_01_norm.mp4 --start 1.233 --duration 2.333 --y-offset 42 --out speak_ig_01.webm
   ```
2. Render in Remotion (`SpeakerPipAndFull.tsx`) at `left: 22, top: 1070, width: 1036, height: 850` with `overflow: 'visible'` and:
   ```tsx
   <OffthreadVideo
     src={staticFile(src)}
     muted
     transparent={src.endsWith('.webm')}
     style={{width: '100%', height: '100%', objectFit: 'cover'}}
   />
   ```
   True alpha composites Eva's hair curls directly over `DARK_NAVY`, `CREAM_PAPER` (including SVG grain), and `WHITE` with **0 halo** and **0 background mismatch**.

### B. Piecewise-Linear Audio-First Timeline Sync (`mapEvaFrame`)
Because calm spoken Italian clauses naturally vary slightly vs English/fast original cuts (`clip_01` ~`1.00x`, `clip_05` ~`1.24x`), **never apply aggressive global `atempo > 1.08`**. Instead:
1. Measure true speech length of every clip after `silencedetect` trimming.
2. Adjust each sentence boundary `[EVA_BOUNDS]` independently in Remotion so every clip stays in natural speed (`0.93x–1.06x`), and map all `<Sequence>` + `KineticCaption` frames through piecewise-linear `mapEvaFrame`:
   ```ts
   // Example from Reel 11 (total 1032 orig -> 1180 Eva frames @ 30fps)
   const ORIG_BOUNDS = [0, 152, 267, 498, 671, 906, 1004, 1032];
   const EVA_BOUNDS  = [0, 152, 284, 542, 738, 1014, 1152, 1180];

   export const mapEvaFrame = (origFrame: number, useEvaTiming = true): number => {
     if (!useEvaTiming) return origFrame;
     if (origFrame <= ORIG_BOUNDS[0]) return EVA_BOUNDS[0];
     for (let i = 0; i < ORIG_BOUNDS.length - 1; i++) {
       const s0 = ORIG_BOUNDS[i], s1 = ORIG_BOUNDS[i + 1];
       if (origFrame <= s1) {
         const d0 = EVA_BOUNDS[i], d1 = EVA_BOUNDS[i + 1];
         return Math.round(d0 + ((origFrame - s0) * (d1 - d0)) / (s1 - s0));
       }
     }
     return EVA_BOUNDS[EVA_BOUNDS.length - 1];
   };
   ```

### C. Micro-SFX & Audio J-Cut Recipe in Remotion
- Pre-trim every clip with adaptive EBU R128 noise gating:
  ```powershell
  python .agents/skills/reel-avatar-cloner/scripts/gflow_batch_ingest.py trim `
    eva_01.mp4 --out eva_01_trim.mp4 --adaptive-loudnorm
  ```
- Layer subtle tactile SFX (`volume={0.14}` to `0.22` -> `-24 to -28 dBFS`) inside `<Sequence>` blocks aligned to card Waterfall Entries (`cut-the-curve` §6), oversized cursor click frames, and J-cut (`from={cutFrame - 4}`) audio lead-ins so cuts breathe like human-edited reels.

---

## 5. Final Self-Audit Checklist Before Delivering to User
Verify every box using actual `ffprobe`, contact sheets, and `read_file` full MP4 playback:
- [ ] **Concept Match:** PIP 3D head pop-out intact, shoulders + t-shirt + hand gestures visible, zero flat head chop, typography ink-sized (`reverse-any-video` parity).
- [ ] **Natural Tempo, J-Cuts & Lip-Sync:** Every clip plays at `0.93x–1.06x` (`atempo`), adaptive silences trimmed, smooth 3–5f audio lead-ins where natural, A/V lip-sync locked end-to-end.
- [ ] **Seamless Brightness & Exposure:** All Setup A/B clips graded (`gamma = 1.10`) to matched `L*` with zero washed-out/over-bright cuts.
- [ ] **Alpha & Depth Cleanliness:** Zero faint grey rectangular boxes above PIP cards on `WHITE` or `CREAM_PAPER` backgrounds; any `embed` climax text cleanly behind matte foreground (`captions-overlay`).
- [ ] **Motion & Seam Craft:** Zero artificial orange light flashes, zero `< 1.0s` speaker flashes (`1.1s–2.3s` fullscreen beats), opaque `#root` stage (`seam-craft`), zero idle wobble loops, clean `0.3–0.75s` pre-climax stillness (`motion-doctrine`).
- [ ] **Hook, Sound & Copy Polish:** Hook scored (`ig-reel`), subtle UI micro-SFX mixed `-24..-28 dBFS` (`sfx.md`), social copy de-slopped (`ig-human` `>= 70 PASS`), brand spoilers scrubbed when requested, Instagram (`commenta "PROMO"`) and TikTok (`scrivici in DM "PROMO"`) variants both rendered and verified.
