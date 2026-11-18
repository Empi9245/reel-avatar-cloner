# Reel Avatar Cloner (`@Eva` Edition)

An opinionated, production-hardened agent skill for **1:1 cloning viral Reels/TikToks** and generating **lifelike spoken AI avatar videos** with consistent identity (`@Eva` or custom avatars), natural human acting, pixel-sharp UI cards in Remotion, credit-safe Google Flow (`omni-1.2-flash`) workflows, and dual **Instagram + TikTok** deliverables.

Built to pair seamlessly with specialized companion agent skills (`reverse-any-video`, `motion-doctrine`, `cut-the-curve`, `seam-craft`, `oversized-cursor`, `captions-overlay`, `remotion-markup`, `remotion-captions`, `media-use`, `ig-reel`, `ig-human`) without reinventing motion, matting, or copywriting primitives.

---

## Key Capabilities

- **1:1 Concept & Framing Audit:** Keeps original visual grammar intact—including **true-alpha VP9 `.webm` (`yuva420p`) 3D head/hair pop-out above rounded PIP cards** (`gflow_batch_ingest.py popout-pip` + Remotion `<OffthreadVideo transparent />`), full chest/shoulders/hand-gesture framing, and widened fullscreen beats (`1.1s–2.3s`) without synthetic orange flash leaks.
- **Credit-Safe Single-Model Flow Pipeline:** Pre-flight credit check (`$0`), strict single-model coherence (`omni-1.2-flash @ 360p`), 2-phase Star Topology anchoring (`eva_con_tshirt.png` + room master plates), mid-batch user checkpoints, and **0-credit LAB luminance + `gamma=1.10` recovery** for bright `r2v` clips.
- **Anti-AI UGC Acting & Realism Direction:** 5-block smartphone UGC prompt architecture (15% bun headroom, pores/peach fuzz, asymmetrical window daylight, axial forward lean, spatial upward eye-glances toward top cards, varied female hand choreography per cut, dry close-mic voice lock).
- **Audio-First Piecewise-Linear Sync + J-Cuts:** 2-pass EBU R128 adaptive `loudnorm` silence trimming (`trim --adaptive-loudnorm`), natural `0.93x–1.06x` `mapEvaFrame` timeline mapping, `3–5f` audio J-cuts, and `-24..-28 dBFS` micro-SFX layering.
- **4-DOF Temporal Screen Reconstruction (`reel_cloner.py`):** Removes burned-in English captions from panning laptop/phone B-roll using `cv2.estimateAffinePartial2D` donor alignment + ring illumination matching with zero Voronoi smudges.
- **5-Phase Voice Consistency & Character Sheets (`Cast Kit v1` / `Voice Sheet v1` / `Shot Caller v2`):** Reusable pipelines for onboarding new avatars or unifying vocal timbre across rooms with ElevenLabs `eleven_v4` / `eleven_multilingual_sts_v2`.
- **Platform-Split Funnel & Brand Redaction:** Dedicated Instagram (`commenta "PROMO"` LinkDM flow) and TikTok (`seguici sul profilo e scrivi "PROMO" in DM`) cuts, curiosity-gap brand redaction, and safe phrasing calibrated against Google Flow's multilingual safety filter.

---

## Installation

### Option 1 — Clone directly into your workspace `.agents/skills/` or `.claude/skills/`

```bash
git clone https://github.com/Empi9245/reel-avatar-cloner.git .agents/skills/reel-avatar-cloner
```

*(For Claude Code users who read `.claude/skills/`:)*

```bash
git clone https://github.com/Empi9245/reel-avatar-cloner.git .claude/skills/reel-avatar-cloner
```

### Option 2 — Skills CLI (`npx skills`)

```bash
npx skills add Empi9245/reel-avatar-cloner
```

---

## Repository Structure

```text
reel-avatar-cloner/
├── SKILL.md                                     # Core agent instructions, 6-step workflow & skill router
├── README.md                                    # Overview & installation guide
├── LICENSE                                      # MIT License
├── .env.example                                 # ElevenLabs credential template (copy to project .env)
├── .gitignore                                   # Keeps .env, __pycache__, *.pyc out of git
├── evals/
│   └── evals.json                               # Scenario regression tests for skill behavior
├── references/
│   ├── artistic-direction-and-realism.md        # 5-block UGC prompts, 5 acting laws, cross-skill doctrines & self-audit
│   ├── flow-prompts-and-safety.md               # Anti-filter & gaze-lock rules for Google Flow
│   ├── multi-clip-consistency-and-local-h3.md   # Star topology, gflow-cli, Gemini API & local MiniMax-H3 guide
│   ├── voice-and-character-reference.md         # Cast Kit v1 + Voice Sheet v1 + Shot Caller v2 templates
│   ├── cta-and-dm-funnel.md                     # Instagram vs TikTok CTA & LinkDM automation playbooks
│   └── audio-and-sound-matching.md              # Dual audio discovery (TikTok meme sounds + Shazam beat offsets)
├── resources/
│   ├── eva_con_tshirt.png                       # Dressed `@Eva` character anchor
│   ├── eva_front_single.png                     # Canonical frontal portrait reference
│   ├── eva_turnaround_1.jpg                     # Turnaround sheet
│   ├── eva_voice_master.wav                     # Clean `@Eva` master voice reference
│   └── emoji_*.png                              # High-DPI iOS emoji PNGs for caption pills
└── scripts/
    ├── gflow_batch_ingest.py                    # check, trim (--adaptive-loudnorm), grade (gamma=1.10), popout-pip (.webm)
    ├── reel_cloner.py                           # analyze, split, clean (temporal_4dof / pill_telea), caption, assemble, find-audio
    ├── elevenlabs_voice_ref.py                  # Phonetic pangram TTS, IVC cloning & STS multi-clip voice unification
    ├── gemini_veo_video.py                      # Direct Gemini API Veo generation bridge
    └── unsloth_h3_video.py                      # Local offline MiniMax-H3 Ref2VA CLI bridge
```

---

## Quick CLI Reference

```bash
# 1. Check Google Flow session & credits ($0 cost)
python scripts/gflow_batch_ingest.py check

# 2. Sample-accurate EBU R128 adaptive silence trimming
python scripts/gflow_batch_ingest.py trim raw_01.mp4 --out trim_01.mp4 --adaptive-loudnorm

# 3. 0-credit LAB luminance & midtone recovery for bright Flow clips
python scripts/gflow_batch_ingest.py grade trim_01.mp4 --out grade_01.mp4 --room light-wall --gamma 1.10

# 4. Export 1036x850 VP9 true-alpha (yuva420p) 3D pop-out PIP WebM for Remotion
python scripts/gflow_batch_ingest.py popout-pip grade_01.mp4 --start 0.0 --duration 2.333 --y-offset 42 --out speak_ig_01.webm

# 5. Analyze a reference Reel (cuts + OpenCV diff events) & clean panning B-roll with temporal_4dof
python scripts/reel_cloner.py analyze source.mp4 --workdir ./work
python scripts/reel_cloner.py clean ./work/clips/broll_raw.mp4 --out ./work/clips/broll_clean.mp4 --config ./work/clean.json
```

---

## Optional Companion Skills

When installed inside a workspace alongside these open-source skills, `reel-avatar-cloner` routes directly to their exact tools and specs (summary doctrines are also bundled in [`references/artistic-direction-and-realism.md`](./references/artistic-direction-and-realism.md)):
- **Measurement, Motion & Captions:** `reverse-any-video`, `motion-doctrine`, `cut-the-curve`, `seam-craft`, `oversized-cursor`, `captions-overlay`, `remotion-markup`, `remotion-captions`, `media-use`
- **Hooks, Pacing & De-Slop:** `Jakeschincariol/instagram-agent-skill` (`ig-reel`, `ig-human`)

---

## License

MIT — see [LICENSE](./LICENSE).
