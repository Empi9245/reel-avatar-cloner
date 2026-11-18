# Voice Consistency & Character Reference Pipeline (Joey `@noisygroup` 5-Phase Workflow)

Adapted from Joey's (`@noisygroup`) official **Castkit v1**, **Voicesheet v1**, and **Shotcaller v2** pipeline for **Nano Banana Pro**, **ElevenLabs v4/v3**, and **Seedance 2.5 / Higgsfield**.

Run this 5-phase pipeline whenever:
1. Creating a new avatar,
2. Updating an avatar's voice, outfit, or character reference sheet, or
3. Generating any spoken avatar video clip where voice timbre, cadence, and facial expressiveness must stay locked across every scene.

---

## Fase A — Scheda Personaggio a 3 Pannelli (`Cast Kit v1`)

A character is anchored on a **single flat 18% neutral gray field** (`shadowless`, zero cast shadow, zero lighting baked in) so skin tones render true and downstream video models never fight baked-in shadows.

### Status of `@Eva`
`@Eva` currently has:
- **Face Lock:** `resources/eva_front_single.png`
- **3-Angle Head Turnaround:** `resources/eva_turnaround_1.jpg`

When starting a full-body/spoken Seedance 2.5 pipeline for `@Eva` (or any new avatar), ensure she has a complete **3-panel character reference sheet**:
1. **LEFT PANEL — Full body front, headless** (dead-on frontal, square shoulders/hips, even weight; head removed by neckline test so proportions & wardrobe read cleanly).
2. **CENTER PANEL — Full body rear, head attached** (dead-on from directly behind, showing hair fall, back garment cut, hem, footwear).
3. **RIGHT PANEL — Tight chest-up face lock** (just above crown to collarbones, dead-on frontal, neutral expression, lips closed and relaxed).

### Neckline Test for the Left Panel (Headless Cut)
- **Variant A (Ghost Mannequin — no head, no neck, no hair):** Use when the top has a collar/opening (crew-neck sweatshirt like `@Eva`, mock neck, turtleneck, shirt/jacket collar, hoodie, ribbed tank). Name the specific collar (e.g., `"the white ribbed crew-neck collar"`).
- **Variant B (Clean Neck Cut — no head, no hair, crisp horizontal neck termination):** Use for strapless, spaghetti-strap camisole, wide scoop, or plunge necklines.

### Mandatory `PHOTOREAL FLAT CLOSE` (Verbatim)
Always append this exact block to every photoreal Castkit plate or 3-panel sheet:
```text
The background is a single flat 18% neutral gray field — one uniform value at every pixel corner to corner, identical directly beside the subject and in the far corners, with no seam line, no gradient, no hotspot, no vignette, and no falloff to lighter or darker anywhere in the frame. It is a flat color field, not a photographed backdrop — no surface, no floor, no wall, no corner, no horizon, and no plane the figure stands on or in front of.

Relight from scratch overriding any reference lighting: completely flat shadowless illumination — one enormous soft frontal source at camera position wrapping the subject evenly, matched equal fill from camera-left and camera-right at identical intensity, matched fill from above and below, so both sides of the face read at exactly the same brightness. No key-and-fill ratio, no modelling, no shadow side, no cheek triangle, no nose shadow, no under-chin shadow, no rim light, no hair light, no kicker, no specular hotspot. Extremely low contrast, even, milky, catalogue-flat. Form is described by bone structure, hair strands, and fabric folds alone, not by light and shadow.

Absolutely zero shadow anywhere outside the subject. No cast shadow, no contact shadow, no floor shadow, no drop shadow, no ambient occlusion where the body meets the background, no soft darkening behind the shoulders or beneath the hem, no halo, no edge darkening, and no rim separating the figure from the field. Shading exists only on the subject and stops cleanly at the silhouette. Absolutely zero light bleed outside the subject — no spill, no glow, no bounce, no reflected color cast thrown from the skin or the wardrobe onto the background, and no brightening anywhere behind the figure.

Skin reads matte and velvety — zero shine on forehead, nose bridge, cheekbones, and chin, no oily T-zone. Skin renders at its true natural skin tone and wardrobe at its true natural color, warmth preserved and natural against the neutral gray, never pale or washed-out or cool-shifted by the background. Real peach fuzz at the jaw and hairline, real soft fine even pore texture, subsurface scattering reading as semi-translucent biology, real hair rendered strand by strand with fine flyaways at the hairline, real fabric weave and drape, real metal surface detail on any jewelry, never plastic, never waxy, never glass-skin, never harsh — fine flattering texture that keeps the face looking good, no acne, no blemishes, no rough pores.

Even sharpness edge to edge across the entire frame. No depth-of-field falloff, no bokeh, no background blur, no lens vignette, no lens distortion, no flare, no bloom, no chromatic aberration, no atmosphere, no air between the subject and the background. Photographed on a 50mm prime, soft natural film grain. Photographed not generated.
```

### Ready-to-Use 3-Panel Sheet Prompt Template (Nano Banana Pro — Landscape 16:9 / 3:2)
*(Do NOT write aspect ratio or character names inside the code block; set the ratio in the tool UI.)*
```text
A three-panel character reference sheet composed as one horizontal frame, divided into three equal vertical panels side by side with thin clean separation, the same figure and the same outfit rendered identically across all three. No text, no labels, no numbering anywhere in the image.

The face, bone structure, freckles, dark-brown hair, and tortoiseshell glasses come from the attached character face reference; the full-body proportions and outfit follow the wardrobe specification below.

Identity: slim adult female build, warm natural fair-olive skin tone with light natural freckles across nose bridge and cheeks, a small beauty mark below the left eye, dark-brown eyebrows, warm brown eyes behind round thin tortoiseshell eyeglasses, small double silver hoop earrings in each ear, high messy dark-brown bun with soft face-framing tendrils, natural lips, clean unpolished nails.

Wardrobe: loose-fitting off-white heavyweight cotton long-sleeve crew-neck sweatshirt with ribbed crew collar, cuffs, and hem; high-waisted straight-leg medium-indigo denim jeans; clean white leather low-top sneakers with matching crew socks.

LEFT PANEL — full body front view, no head, no neck, and no hair. The body faces the camera dead-on from the shoulders down to the white sneakers — shoulders and hips both square to the lens and level, both sides of the figure equally visible, arms relaxed at the sides, hands open and loose, feet planted parallel and pointing straight at camera, weight even across both feet. This is a flat frontal view regardless of how the figure stands in any reference: no three-quarter turn, no rotation of the torso or hips away from the lens, no twist at the waist, no contrapposto, no weight shifted onto one hip, no shoulder dropped or pushed forward, no foot turned out. There is no head, no neck, and no hair at all — nothing rises above the shoulder line, and no hair falls across the chest or shoulders. The white ribbed crew-neck collar holds its own three-dimensional shape at the top of the sweatshirt and its opening is an empty dark hollow looking down into the inside of the garment, with the inner back of the cotton fabric faintly visible inside the opening. The garment reads as worn by an invisible body — full volume, natural drape, real fabric tension across the chest and shoulders, but nothing emerging from the neckline. No stump, no skin, no cut edge, no anatomy, no blood, not blurred, not faded, not dissolving, no wisps, no smoke, no ghosting, no transparency in the body. The panel keeps full headroom — generous empty field above the shoulders where the head would be — so the figure sits at the same scale and position in the frame as a normal full-body portrait.

CENTER PANEL — full body rear, head attached. The complete figure from above the messy bun crown down to the white sneaker heels, seen dead-on from directly behind — shoulders and hips square to the lens and level, the spine centered in the panel, arms relaxed at the sides, feet parallel, weight even. This is a flat rear view: no three-quarter turn, no rotation, no twist at the waist, no weight shifted onto one hip, no glance back over the shoulder. High messy dark-brown bun with loose nape tendrils, back of the off-white crew-neck sweatshirt, straight-leg indigo denim back pockets and hem, clean white sneaker heels.

RIGHT PANEL — tight chest-up face lock. Framed from just above the top of the bun down to the collarbones with the face filling the panel. The head is dead-on to camera, squared and level, both ears with small silver hoops equally visible, the nose centered between the eyes behind the round tortoiseshell eyeglasses, eyes directly into the lens, neutral expression, lips closed and relaxed. This is a flat frontal view: no three-quarter turn, no head rotation, no chin lifted or dropped, no tilt to either side. The white ribbed crew collar enters at the bottom of frame. Every facial plane, the eyes, brows, nose, lips, freckles, and hairline read at maximum detail.

Skin renders at its true natural tone, identical in value and hue across the face, arms, hands, back, and body in every panel, never darkened, never pale or cool-shifted.

[INSERT PHOTOREAL FLAT CLOSE VERBATIM HERE, stating flatness applies uniformly across all three panels]
```

---

## Fase B — Pangramma Fonetico + ElevenLabs v4 Audio Tags (`Voice Sheet v1`)

### 1. Gather Inputs (from User or Reference Video)
Before writing the pangram, confirm or deduce:
1. **Language** spoken by the avatar (e.g., `it` Italian, `en` English, `ko` Korean, `es` Spanish, etc.).
2. **Personality & emotional range** (2–3 adjectives, e.g., `natural, playful, sharp-witted`, or `cool, measured, dry`, or `warm, energetic, expressive`).

### 2. Phonetic Pangram Rules
- **Phonetic, not orthographic:** Every *sound* of the language (consonants, all vowels, diphthongs, double consonants/geminates, palatal/velar clusters) must appear in real spoken words.
- **Closed-lip consonants (`b, p, m`):** Pack them generously so Seedance gets unmistakable bilabial lip seals.
- **2–4 natural clauses landing at 8–15 seconds** when spoken. Never use nonsense tongue-twisters that trip TTS pronunciation.
- **Lock the base text per language;** only swap the `[audio tags]` per character/mood.

### 3. Stock & Verified Pangrams

#### Italian (Custom Phonetic Pangram — `@Eva` Default)
*(Recommend a native Italian speaker review once if customized.)*
Base text (38 words, ~12–13s):
```text
Ma guarda un po'... chi ha preso gli zaini blu sul banco? Non scherzare! Bussa piano alla porta — mamma dorme già — lascia ogni dubbio, posa i funghi giù sul piatto e vieni qui che ci facciamo una bella risata!
```
Tagged for `@Eva` (natural, warm, playfully expressive):
```text
[curious] Ma guarda un po'... chi ha preso gli zaini blu sul banco? [playfully annoyed] Non scherzare! [whispers] Bussa piano alla porta — mamma dorme già — [softly] lascia ogni dubbio, posa i funghi giù sul piatto... [laughs] e vieni qui che ci facciamo una bella risata!
```

**Italian Phonetic Coverage Table:**
| Sound Category | Target Phonemes | Covered Words |
|---|---|---|
| Closed-lip seals | `/p/, /b/, /m/` | `po'`, `preso`, `piano`, `porta`, `piatto`, `blu`, `banco`, `bussa`, `dubbio`, `bella`, `Ma`, `mamma`, `facciamo` |
| 7 Italian vowels | `/a, ɛ, e, i, ɔ, o, u/` | `Ma`, `bella`, `che`, `chi`, `po'`, `non`, `blu` |
| Geminates (doppie) | `mm, ss, ll, bb, tt, cc` | `mamma`, `bussa`, `alla`, `bella`, `dubbio`, `piatto`, `facciamo` |
| Clusters & affricates | `gl /ʎ/`, `gn /ɲ/`, `sc /ʃ/`, `gh /ɡ/`, `ch /k/`, `qu /kw/` | `gli`, `ogni`, `lascia`, `funghi`, `chi/che`, `qui` |
| Sweet / hard & sibilants | `c/g` dolce, `z` sonora/sorda, `s/z` | `ci/facciamo`, `già/giù`, `zaini`, `scherzare`, `sul`, `preso` |
| Glides & liquids | `/j, w, r, l, n, f, v, t, d/` | `vieni`, `guarda`, `risata`, `porta`, `dorme`, `funghi`, `zaini` |

#### English (Stock Phonetic Pangram)
Base text:
```text
The beige hue on the waters of the loch impressed all, including the French queen, before she heard that symphony again, just as young Arthur wanted.
```
Example tagged (natural & expressive):
```text
[curious] The beige hue on the waters of the loch impressed all, [softly] including the French queen... [laughs] before she heard that symphony again, [warm, settled] just as young Arthur wanted.
```

#### Korean (Tested Stock Pangram)
```text
[curious] 키스의 고유 조건은... [mischievously] 입술끼리 만나야 하고, [laughs softly] 특별한 기술은 [whispers] 필요치 않다. [gasps] 얘, 도대체 왜 뛰어? [shouting] 뭐?! 예쁜 쥐가 내 짬뽕 훔쳐 갔대! [sighs] 봐, 저기 있네.
```

### 4. ElevenLabs v4 Audio Tag Rules & Voice Design Description
- **Model:** Always use **`eleven_v4`** (or **`eleven_v3`** fallback; older models read `[tags]` aloud!).
- **One tag per clause** in square brackets (`[curious]`, `[excited]`, `[whispers]`, `[laughs]`, `[sighs]`, `[pause]`, `[softly]`, `[serious]`, `[gasps]`, `[playfully annoyed]`) plus expressive punctuation (`...`, `—`). Never stack multiple conflicting tags back-to-back.
- **Full emotional range in one take:** Cover curious/neutral -> playful/amused -> whisper/soft -> surprise/peak -> laugh/sigh/settle.
- **Voice Design Prompt Template** (for ElevenLabs Voice Design or Voice Library selection):
  ```text
  A young adult Italian woman in her late twenties with a warm, clear, natural mid-register voice. Conversational and agile pace with crisp consonants, subtle playful warmth, easy micro-smiles audible in the phrasing, and natural close-mic intimacy. Native standard Italian diction, recorded close in a quiet room.
  ```

---

## Fase C — Generazione Audio ElevenLabs + Export MP4 in Secondi Interi

Run `scripts/elevenlabs_voice_ref.py`:

```bash
# Check .env first
python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py --check-env

# Generate MP3 via ElevenLabs API (cross-language supported) + export 1280x720 whole-second MP4
python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py \
  --text-file <workdir>/pangram_tagged.txt \
  --language it \
  --min-seconds 5 \
  --out-dir <workdir>

# Or if user generated the MP3 manually in the ElevenLabs Web UI:
python .agents/skills/reel-avatar-cloner/scripts/elevenlabs_voice_ref.py \
  --audio-in <workdir>/downloaded_from_web.mp3 \
  --min-seconds 5 \
  --out-dir <workdir>
```

### Mandatory Credential Gate
- The script reads `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` from `.env` (and optional `ELEVENLABS_MODEL_ID`, default `eleven_v4`).
- **If either is missing (exit code `2`), STOP immediately**, present the tagged pangram + Voice Design description in code blocks so the user can either:
  1. Add `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` to `.env`, OR
  2. Paste the tagged pangram into the free ElevenLabs Web UI, download the `.mp3`, and feed it back via `--audio-in`.
- **Whole-second rule:** `ffprobe` measures the MP3 duration, then `ffmpeg` pads trailing silence up to `math.ceil(duration)` exact whole seconds (e.g., `15.2s` -> `16.00s` exact, never decimals) and exports `reference_voce.mp4` (`1280x720`, `30fps`, `libx264`, `aac`).

---

## Fase D — Prompt per Video Reference Sheet a 1080p (`Shot Caller v2`)

### Pre-Prompt Check (Plain Chat Text Before Code Block)
> Pre-prompt check:
> - References: `@Image 1` (3-panel character sheet), `@Video 1` (`reference_voce.mp4`, exact runtime `T`s, sole audio source)
> - Version: Seedance 2.5 (1080p)
> - Scene: Two-panel studio character-reference capture on a flat 18% neutral gray field
> - Speech: Verbatim phonetic pangram (tags stripped) lip-synced on the RIGHT panel
> - Runtime: `T`s whole seconds (`LEFT`: `n` shots; `RIGHT`: 1 continuous shot)
>
> Run it?

### Timing Formula (`T` = exact whole seconds of `reference_voce.mp4`)
- `n = min(7, T // 2)` shots on the LEFT panel.
- Shots `2..n` run `2s` each; **Shot 1** takes `s1 = T - 2 * (n - 1)` seconds.
- **LEFT Montage Order:**
  1. Shot 1 (`s1`s): full-body turn on the spot from front through three-quarter toward profile.
  2. Shot 2 (`2s`): full-body rear view, weight shift.
  3. Shot 3 (`2s`): full-body right profile completing turn back to front.
  4. Shots `4..n` (`2s` each): tight `12° (180mm)` detail inserts (neckline/collar & glasses, sweatshirt sleeve/fabric weave, denim pockets/hardware, white sneakers with one heel lifting).

| `T` (seconds) | `n` (LEFT shots) | Shot 1 (`s1`) | Shots `2..n` |
|---|---|---|---|
| `8` | `4` | `2s` | `2s` each |
| `10` | `5` | `2s` | `2s` each |
| `12` | `6` | `2s` | `2s` each |
| `13` | `6` | `3s` | `2s` each |
| `14` | `7` | `2s` | `2s` each |
| `15` | `7` | `3s` | `2s` each |
| `16` | `7` | `4s` | `2s` each |

### Head-Turn Rules (RIGHT Panel)
- Continuous 1-shot close-up for all `T` seconds (`18° / 120mm` lens).
- Head turns naturally roughly **15–20 degrees either side of front** across the emotional beats so the model learns bone structure from multiple angles and soft key light moves across brow, cheekbone, and jaw.
- **Mouth stays 100% unobstructed and readable** in every frame (no hands, hair tendrils, or collar rising over lips).
- Explicitly list **closed-lip words (`b, p, m`)** from the pangram so lip seals land cleanly.

### Verbatim Video Reference Sheet Prompt Template (Seedance 2.5 — 1080p)
*(Replace `[brackets]`; attach `@image1` = 3-panel character sheet, `@video1` = `reference_voce.mp4`. No character names, no aspect ratio, no negative block.)*

```text
Two side-by-side panels, total [T] seconds. The LEFT panel is a montage of [n] shots with hard cuts inside the left panel only — shot 1 runs [s1] seconds, shots 2 through [n] run 2 seconds each. The RIGHT panel is 1 continuous shot for the full [T] seconds, never cutting. No transitions, no dissolves. All footage real-time, no slow motion, no speed ramping anywhere.
Style: 8K photorealism, high dynamic range, large-format film look. NOT a 3D render, NOT a game engine, NOT a game-cutscene aesthetic, NOT a cartoon.
Operating style: clean studio character-reference capture, in-camera feel, tactile textures, photochemical look.
Texture: matte non-reflective surfaces, heavyweight cotton fleece, medium-indigo denim weave, leather sneakers, acetate tortoiseshell eyewear frames, silver metal hoops, no digital gloss, no plastic sheen.
Skin: pore-level realism, fine vellus hair, natural asymmetry, no smoothing, no retouching.
Technical: real-time 24fps, true 180-degree shutter with a real 1/48 second exposure on every frame, genuine photographic motion blur, each frame blending smoothly into the next. No flicker, no warping, no morphing, no frame interpolation, no frame blending, no ghosting, no high-shutter video crispness.
NO ON-SCREEN TEXT — CRITICAL: no on-screen text of any kind anywhere in frame at any point. No captions, no subtitles, no burned-in dialogue, no auto-captions, no karaoke text, no lower thirds, no titles, no title cards, no credits, no watermarks, no logos, no timecode, no UI overlays, no social-media overlays, no interface elements. The frame is clean of all overlay graphics from first frame to last.
THE SPEECH IS THE PRIMARY SUBJECT — CRITICAL: in the RIGHT panel the woman speaks out loud to the attached voice recording in @video1, in [language], every syllable formed on her lips in time with it, for its full length. She is the speaker of this recording, never mouthing along. The words she forms, in order: "[PANGRAM TEXT EXACTLY, TAGS REMOVED]" Every closed consonant lands as a complete visible lip seal held a beat before releasing — both lips press fully together on [LIST EVERY WORD WITH B, P, OR M SOUND]. Open vowels are held open, the jaw working with the phrasing, never lazily half-open or mumbling. Her mouth is the focus of the right panel.
THE HEAD TURN AND THE MOUTH — CRITICAL: in the right panel she turns her head naturally while speaking, so the camera reads her facial expressions and bone structure from several angles. [BEAT-BY-BEAT HEAD PATH MATCHED TO EMOTIONAL TAGS, e.g., starting slightly angled toward camera-left, drifting gently toward camera-right on the curious question, snapping subtly toward center on the playful warning, leaning slightly forward on the whisper, lifting and loosening into a natural smile on the laugh.] Every turn stays about fifteen to twenty degrees either side of front. Her mouth stays unobstructed and clearly readable in every frame and at every angle. Nothing ever covers it — no hand, no loose hair strand, no collar rising over her chin.
THE TWO PANELS — CRITICAL: the frame is two equal side-by-side vertical panels on one continuous flat neutral 18% gray field, separated by a thin straight seam of the same gray. Every cut happens inside the LEFT panel only; the RIGHT panel runs unbroken through every left-panel cut, its performance never jumping, resetting, or pausing. Only the right panel speaks — in the left panel her face is fully visible and sharp, her mouth closed, never forming words, never mouthing along with the recording. The two panels never mirror each other or move in sync. The layout never shifts, resizes, or merges.
ASSETS:
@image1 = identity and wardrobe reference only — its layout, panel arrangement, and framing are never reproduced. Slim build, warm natural fair-olive skin with light freckles across nose bridge and cheeks, small beauty mark below left eye, dark-brown eyebrows, warm brown eyes behind round tortoiseshell eyeglasses, small double silver hoop earrings, high messy dark-brown bun with loose tendrils; off-white heavyweight cotton crew-neck sweatshirt, medium-indigo straight-leg denim jeans, white leather low-top sneakers. THIS SCENE: standing alone on the gray field. Her face identical in both panels. 100% match to the reference.
GEOMETRY MAP: LEFT panel — each montage shot centred on her body against the bare gray field. RIGHT panel — tight close-up from just above the crown of her messy bun to just below the ribbed white crew-neck collar, her shoulders angled slightly toward camera-left while her head turns on her neck. She is sharp in every shot, the gray field behind softly falling off. Nobody else is in either panel.
FIRST FRAME: already in motion in both panels — the left panel already mid-turn, the right panel already drawing a natural breath before the first word. No empty establishing hold, no static frame.
LENS LOCK LEFT, shots 1–3 = 84° (24mm) full body head to sneaker soles with clear gray margin above and below, kept at distance so proportions stay true, no edge distortion. LENS LOCK LEFT, shots 4–[n] = 12° (180mm) tight detail inserts. LENS LOCK RIGHT = 18° (120mm) — a LONG lens, strong compression, the gray thrown soft, only her face sharp. NOT wide-angle, no deep focus. No focal drift within any shot.
CAMERA: locked-off for every shot in both panels, real tripod weight, no movement. The stillness of the frame is the subject.
LIGHT: relight from scratch overriding reference lighting. One broad, very soft diffused key from the front and slightly above, warm-neutral, wrapping evenly, faithful skin, a gentle soft triangle of light on the shadow cheek in the right panel that travels naturally across the face as the head turns, showing the brow, cheekbone, and jaw from each angle. The background is completely shadowless — no cast shadow from her body on the field or floor at any point, the gray evenly lit edge to edge. Soft specular highlights along the tortoiseshell eyewear rim and silver hoops. Blacks lifted, highlights rolled off softly.
COLOUR: ~65% neutral 18% gray field and off-white cotton sweatshirt; ~20% warm natural skin tone and dark-brown hair; ~15% medium-indigo denim and warm tortoiseshell accent.
ATMOSPHERE: the air carries real density at every depth — a continuous soft scattering gradient from the lens to the gray field, blacks lifted on the dark hair and indigo denim, the field falling off gently behind her. Low macro contrast; high micro contrast — cotton weave, denim grain, individual hair strands, skin pores, and eyewear frames. She moves through the air without disturbing it. No plumes, no wisps, no beams, no rays. Nothing in the air is emitted by anything.
ACTION:
LEFT panel, shot 1 ([s1]s), full body: a calm, natural turn on the spot to her OWN left, from front through three-quarter toward profile, hands relaxed at her sides.
LEFT panel, shot 2 (2s), full body: her back to the lens, weight shifting gently from one hip to the other — high bun from behind, back of the off-white sweatshirt, indigo denim back pockets, white sneaker heels.
LEFT panel, shot 3 (2s), full body: her right side in profile, completing the turn back to front, settling into a relaxed even stance, a natural glance toward camera-right.
LEFT panel, shot 4 (2s), insert: tight close-up on the ribbed crew-neck collar, round tortoiseshell glasses, and double silver hoops.
[ADD INSERTS FOR SHOTS 5..n — e.g. heavyweight cotton cuff and forearm, indigo denim waistband and pocket stitching, white sneaker profile with one heel lifting slightly as weight shifts.]
RIGHT panel, throughout: she speaks with the recording while her head turns as described, her eyes moving naturally past the lens toward camera-left and back, with brief warm glances near lens height without staring dead-pan. Minimal relaxed shoulder shift; most of the movement lives in the neck, the jaw, and the face.
Micro-motion: natural breathing rhythm, loose hair tendrils shifting and settling on every head turn, subtle cotton creasing at the shoulders. Nothing in the environment moves.
PHYSICS: real gravity and bodyweight — white sneakers planting and pivoting with weight transfer through the hips, sweatshirt fabric draping and settling, hair tendrils moving with real weight. She stands firmly grounded on the shadowless floor. Nothing floats, nothing slides.
ACTING: RIGHT panel — warm, expressive, authentic presence, active brows and eyes matched to each line in order: [ONE VISIBLE MUSCLE BEAT PER TAG IN ORDER, e.g., brows lifting slightly with curious eyes on the opening question; amused squint and sharp chin tuck on the playful rebuke; softened lids and lowered chin on the whisper; gentle brow release on the soft instruction; genuine laugh crinkling the eye corners and parting the lips naturally at the end]. Every expression lives in real facial muscle, never a frozen mask, never dead eyes. LEFT panel — relaxed natural posture, a neutral face with natural blinking and small idle shifts of the eyes, never mannequin-stiff.
AUDIO: the attached clip @video1 is the sole and complete audio source for this sequence. Generate no additional audio of any kind — no room tone, no foley, no ambience, no breath, no added dialogue, no music.
LOCKS: two panels held for the full take — the left panel a [n]-shot outfit montage from three full-body angles into [n-3] detail inserts, the right panel one unbroken close-up speaking with the recording while the head turns through about fifteen to twenty degrees either side of front. Cuts stay inside the left panel. One woman, identical to @image1 throughout — high bun, round tortoiseshell glasses, silver hoops, freckles, white sweatshirt, indigo denim, white sneakers unchanged. Only the right panel speaks; the left panel mouth stays closed. Speech applies per THE SPEECH. The background stays completely shadowless and the light stays soft and identical across both panels. The air holds uniform density. Skin reads true cinematic matte — zero shine on forehead, nose bridge, cheekbones, and chin, real fine even pore texture, peach fuzz at the jaw and hairline, light absorbed like true subsurface scattering, rendering true and natural, never plastic. No CGI, no rendered look, no digital cleanliness, no AI smoothness, no frozen posing, no stabilized glide, no high-shutter crispness, no frame interpolation, no dropped frames.
```

### After Rendering the Video Reference Sheet
Instruct the user to save the rendered 1080p clip as a **Higgsfield Element** (e.g., `@eva-voice-ref`) and mark it as a **video character reference sheet**.

---

## Fase E — Uso nelle Scene Successive del Video (`Shot Caller v2` Scene Locking)

Whenever generating prompts for actual spoken or reaction scenes (cloning a Reel or building original scenes), **always attach the saved Video Reference Sheet Element (`@[handle]`) as the primary character reference** and apply these rules:

1. **`THE REFERENCE LOCKS LOOK, VOICE AND PERFORMANCE — CRITICAL:`** (place right after `THE SCRIPT` when dialogue is generated, or first when non-speaking):
   ```text
   THE REFERENCE LOCKS LOOK, VOICE AND PERFORMANCE — CRITICAL: the attached video character reference @[handle] is the single source of truth for the [visual handle]'s face, hair, outfit, voice, and emotional performance. Her outfit matches the reference garment for garment in every shot — nothing added, removed, recoloured, or restyled. Her speaking voice is the exact voice heard in the reference — the same timbre, register, pitch, texture, pace, accent, and delivery — on every line she speaks, never replaced, deepened, brightened, or genericized, never drifting toward any other speaker's voice. She emotes the way she does in the reference — the same range and size of expression, the same brow and eye movement, the same head carriage, the same laugh, whisper, gasp, and raised voice. Only the character carries over: the reference's panel layout, gray backdrop, framing, cuts, and spoken words are never reproduced.
   ```
2. **In `ASSETS`:** Keep the visual handle short and write:
   `Voice: exactly the voice heard in the reference.` (Never invent a conflicting voice description.)
3. **In `AUDIO`:**
   - **Generated Dialogue (Shotcaller Dialogue System):** Open every line with `"her reference voice,"` and specify only emotion, pace, volume, stress, and room distance for that specific line. Put exact verbatim lines in `THE SCRIPT — CRITICAL:` (plus `THE LANGUAGE — CRITICAL:` for non-English Italian speech), `ACTION TIMING`, and `AUDIO` — all 3 appearances character-for-character identical.
   - **Attached Audio Track (Lipsync Protocol):** Export the target voice/audio slice onto a black frame in whole seconds as `@video1`, include `THE SPEECH IS THE PRIMARY SUBJECT — CRITICAL:` with verbatim transcript + explicit `b/p/m` lip-seal counts, and close `AUDIO` with the sole-source lock for `@video1`.
4. **Shotcaller v2 House Rules:**
   - Never put character names or aspect ratios inside the prompt code block.
   - Never include a negative prompt block (negations stay inline).
   - Follow the 16-slot Spine (`1. HEADER` -> `2. STYLE PREFIX` -> `3. NO ON-SCREEN TEXT` -> `4. CRITICAL BLOCKS` -> `5. ASSETS` -> `6. GEOMETRY MAP` -> `7. FIRST FRAME` -> `8. OPTICS` -> `9. CAMERA` -> `10. LIGHT & COLOUR` -> `11. ATMOSPHERE` -> `12. ACTION TIMING` -> `13. PHYSICS` -> `14. ACTING` -> `15. AUDIO` -> `16. LOCKS`).
