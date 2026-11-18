# Strategia di Ricerca e Matching Audio per TikTok e Instagram

Quando si replica un Reel virale o un TikTok con un avatar AI, l'audio è il **primo fattore di distribuzione algoritmica**.
Caricare un video con audio nativo di tendenza collegato alla traccia corretta porta fino a 10 volte più visualizzazioni organiche rispetto a un video con solo traccia audio caricata come "audio originale".

Per trovare l'audio esatto in pochi secondi, usiamo una **Strategia Doppia (Dual Strategy)**.

---

## Metodo 1 — Ricerca Diretta del Suono con Testo del Meme (Consigliato & Più Veloce)

### Il Principio
Sui social (TikTok e Instagram), quando un meme o uno skit diventa virale, i primi creator che hanno caricato il trend hanno spesso intitolato il proprio suono con **la frase dell'hook o la premessa del meme**, non con il nome della canzone sottostante.
Migliaia di altri video hanno poi riutilizzato quello stesso "Suono originale" della community.

### Come Funziona
1. **Identifica l'Hook / Frase Chiave del Video:**
   - Prendi la prima frase recitata o la scritta nel primo gancio (sia in italiano sia in inglese).
   - Esempi:
     - Reel del genio: `"genio tre desideri"`, `"genio 3 desideri"`, `"i have 3 wishes"`.
     - Reel del collega/bar: `"the guy next to me is using claude"`, `"il tizio accanto a me"`.
2. **Apri la Ricerca Suoni nell'App:**
   - Apri l'app TikTok o Instagram.
   - Tocca la lente di ingrandimento (Cerca).
   - **IMPORTANTE:** Seleziona subito la scheda **"Suoni"** (su TikTok) o **"Audio"** (su Instagram) nella barra orizzontale in alto, evitando di restare sulla scheda generale "Top" o "Video".
3. **Cerca la Frase:**
   - Digita la query (es. `genio tre desideri`).
4. **Seleziona e Salva:**
   - Nei primi 1-3 risultati troverai tracce utente o suoni con decine/centinaia di video già associati.
   - Ascolta l'anteprima: il brano è **già tagliato esattamente all'inizio del meme**, con i drop e le battute sincronizzate ai secondi originali!
   - Tocca l'icona del segnalibro (**"Aggiungi ai Preferiti"**) o tocca **"Usa questo suono"** per agganciare il video muto esportato (`FINAL-REEL-EVA-ITALIANO.mp4`).

---

## Metodo 2 — Shazam Fingerprint + Offset Forbici ✂️ (`find-audio`)

### Quando Usarlo
- Se la ricerca testuale del meme non restituisce risultati o i suoni trovati sono a bassa qualità audio / registrati male con fruscii.
- Se l'account è Aziendale (Business Account) e richiede l'uso di tracce verificate, o se vuoi associare il video alla traccia ufficiale dell'artista per cavalcare la classifica ufficiale.

### Come Funziona
1. **Lancia il comando CLI:**
   ```bash
   python scripts/reel_cloner.py find-audio <workdir>/clips/audio_originale.mp3 --hook "genio tre desideri"
   ```
2. **Cosa fa lo script:**
   - Analizza l'impronta acustica di `audio_originale.mp3` tramite `shazamio`.
   - Restituisce il **Titolo Ufficiale**, l'**Artista**, l'URL Shazam e il timestamp esatto di inizio (`offset`).
   - Se la traccia era rallentata/modificata (tape slowdown tipico dei trend TikTok, es. 0.8x), lo script o l'operatore possono normalizzarla con FFmpeg:
     ```bash
     ffmpeg -i audio_originale.mp3 -af "asetrate=48000*1.23,aresample=48000" audio_fast.mp3
     python scripts/reel_cloner.py find-audio audio_fast.mp3
     ```
3. **Applicazione con le Forbici ✂️ nell'Editor di TikTok:**
   - Cerca il brano ufficiale (es. `Took Her To The O (Fine Tuned Version)` o `Better Off Alone`).
   - Seleziona il brano, tocca l'icona delle **Forbici (Taglia / Trim)**.
   - Trascina l'inizio dell'audio al secondo millimetrico indicato dallo script (es. `00:07.86`).
   - Il ritaglio combacerà alla perfezione con le scene del video.

---

## Tabella di Riepilogo Casi Reali

| Reel / Trend | Hook Meme per Ricerca Suoni | Traccia Ufficiale Shazam | Offset Forbici ✂️ | Note di Sincronizzazione |
|---|---|---|---|---|
| `09-eva-genie-wishes` (Free Claude Code) | `"genio tre desideri"` / `"genio 3 desideri"` | *Took Her To The O (Fine Tuned Version)* — King Von | `00:07.86` | Occhi aperti a +4.50s, cambio pill a +5.47s, cut MacBook a +6.00s |
| `08-eva-google-flow` (Guy next to me) | `"the guy next to me is using claude"` / `"better off alone"` | *Better Off Alone (DZ3 Version)* — DZ3 | `01:41.46` | Cut MacBook a +2.33s, voce entra a +4.85s |

---

## Checklist Finale per la Consegna

Quando consegni il video pronto al creator, fornisci SEMPRE nel report di accompagnamento:
1. Le **2 query di ricerca diretta** per la scheda Suoni di TikTok/Instagram (es. `"genio tre desideri"`).
2. Il **titolo e artista ufficiale** con il minutaggio Forbici ✂️ (es. `Took Her To The O` a `00:07.86`).
3. Sia il file video **MUTO** (`FINAL-REEL-...mp4`, da caricare su TikTok per applicare il suono nativo) sia il file video **CON AUDIO MUXATO** (`FINAL-REEL-...-CON-AUDIO.mp4`, come riferimento visivo o per piattaforme terze).
