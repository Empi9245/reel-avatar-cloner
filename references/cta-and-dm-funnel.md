# CTA & DM Funnel per piattaforma (Instagram vs TikTok)

Regola base: **mai nominare l'app promossa** (nome o hashtag) in caption, hashtag o scritte a video. Il nome si scopre solo ricevendo il DM.

## Instagram / Facebook: commento -> DM automatico
- CTA a video e in caption: `seguici e commenta "promo" per ricevere l'app`.
- Tool: **LinkDM** (app.linkdm.com), solo Instagram/Facebook. Trigger: parola chiave `promo`, match "contiene" e non case-sensitive (PROMO, Promo, promo). Va collegato prima l'account Instagram (login e autorizzazione li fa l'utente nel browser).
- Messaggio DM: vedi sotto.

## TikTok: NON esiste commento -> DM automatico
- L'API ufficiale TikTok permette di automatizzare solo i DM che l'utente manda per primo. Nessun tool può partire da un commento pubblico. LinkDM non supporta TikTok.
- Gli account UE (Italia inclusa) in genere non possono usare tool esterni sui DM TikTok. L'unica automazione possibile è nativa: Message Center / Business Suite, risposte automatiche a parole chiave (da verificare sul proprio account).
- Non usare tool non ufficiali che simulano l'app: rischio ban.
- **CTA TikTok a video:** `scrivimi "promo" in DM per ricevere l'app` (non "commenta"). Si genera con `render_part2_italian(cta_lines=[...], out_name=...)` in `add_italian_captions.py`, oppure con una card `caption` che usa queste righe.
- **Caption TikTok:** stessa struttura, con "scrivimi PROMO in DM" al posto di "commenta". Risposta ai DM: manuale o con le risposte automatiche native se disponibili. Alternativa: link in bio senza nominare l'app.

## Messaggio DM (Instagram)
```text
🚀Come promesso, ecco a te il link per accedere alla tua AI gratuita!

👉 https://freebuff.com/?ref=ref-f0f0c25f-722c-4afd-8fa5-a8a96d66f799&via=rewards_link

Puoi iniziare gratuitamente e provare a programmare con modelli AI avanzati, senza un abbonamento fisso.

Le pubblicità presenti nell'app contribuiscono a sostenere i costi dei modelli.

Fammi sapere cosa ne pensi! 🚀
```
Il link è già il referral dell'utente: non modificarlo. Il nome dell'app compare solo qui, nel DM.
