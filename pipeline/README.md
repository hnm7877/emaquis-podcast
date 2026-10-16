# Chaîne de production : « La Minute E‑Maquis »

`shorts.yaml` → **HeyGen** (avatar Tonton Kofi + voix) → **ffmpeg** (sous-titres jaunes + logo) → **YouTube** (publication programmée à 18 h, déclarée comme contenu IA)

## 1. Installation
```bash
cd pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt     # il faut aussi ffmpeg installé sur la machine
cp config.example.yaml config.yaml
```

## 2. Créer l'avatar (HeyGen), une seule fois
1. Génère **une** photo de référence de Tonton Kofi (description dans `../scripts/00-concept-avatar-episode01.md`).
2. Dans HeyGen, crée un **Photo Avatar** à partir de cette photo, puis ajoute **6 looks** (T1 à T6) en changeant **uniquement la tenue**. Le visage reste le même.
3. Choisis ou clone **une voix** grave et posée en français. Note son `voice_id`.
4. Copie la clé API (Settings → API), les `avatar_id` des 6 looks et le `voice_id` dans `config.yaml`.

## 3. Autoriser YouTube, une seule fois
1. Sur [Google Cloud Console](https://console.cloud.google.com/), crée un projet et active **YouTube Data API v3**.
2. Configure l'écran de consentement OAuth et ajoute ton adresse Gmail comme utilisateur test.
3. Crée un identifiant **OAuth → Application de bureau**, télécharge le JSON et renomme-le `client_secret.json` dans ce dossier.
4. Lance `python auth_youtube.py` et connecte-toi avec le compte de la chaîne. Le fichier `youtube_token.json` est créé.
5. ⚠️ Tant que le projet Google n'est pas **audité par YouTube**, les vidéos mises en ligne par l'API restent **privées**. Demande l'audit avec le formulaire « YouTube API Services – Audit and Quota Extension ». En attendant, tu peux passer chaque vidéo en public à la main dans YouTube Studio.

## 4. Utilisation
```bash
python pipeline.py plan                      # calendrier des Shorts en attente
python pipeline.py next --placeholder --dry-run   # test complet sans HeyGen ni YouTube
python pipeline.py next                      # VRAI : génère, habille et programme le prochain Short
```
Étape par étape : `generate <id>`, puis `brand <id>`, puis `upload <id>`.
Les Shorts déjà en ligne sont enregistrés dans `state.json` et ne sont jamais publiés deux fois.

## 5. Ajouter des Shorts
Ajoute des entrées dans `shorts.yaml` : `id`, `outfit`, `title`, `text`. Vise 100 à 120 mots pour rester sous 60 secondes.

## 6. Automatiser (publication continue)
Sur un serveur ou un VPS, avec cron, une fois par jour à 8 h UTC : chaque jour, le prochain Short est généré et programmé pour 18 h.
```
0 8 * * * cd /chemin/pipeline && .venv/bin/python pipeline.py next >> cron.log 2>&1
```
Avec GitHub Actions : voir `github-workflow.example.yml`. Mets les secrets `HEYGEN_API_KEY`, `YT_TOKEN_JSON` et `CONFIG_YAML` dans le dépôt.

## Coûts et limites
- **YouTube** : 10 000 unités de quota par jour, environ 1 600 par mise en ligne, donc environ 6 vidéos par jour. Largement suffisant.
- **HeyGen** : facturé en crédits selon la durée des vidéos (voir ton abonnement HeyGen). Un Short de 45 s coûte peu.
- Chaque vidéo est déclarée **« contenu synthétique »** (`containsSyntheticMedia`), et la description précise que l'animateur est un avatar IA.
