#!/usr/bin/env bash
# Produit (et publie si demandé) le prochain Short en attente.
#   pipeline/produce.sh [short_id] [--publish] [--heygen-id ID]
# Étapes : HeyGen (Avatar IV) -> montage short-editing -> YouTube via Treg (programmé).
set -euo pipefail
cd "$(dirname "$0")/.."
SKILL=.claude/skills/short-editing/engine
ID="" ; PUBLISH=0 ; HEYGEN_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --publish) PUBLISH=1 ;;
    --heygen-id) HEYGEN_ID="$2"; shift ;;
    *) ID="$1" ;;
  esac; shift
done
if [ -z "$ID" ]; then
  ID=$(cd pipeline && python - <<'PY'
import pipeline as P
_, shorts = P.load_shorts(); st = P.load_state()
print(next((s for s in shorts if not st.get(s, {}).get("youtube_id")), ""))
PY
)
fi
[ -z "$ID" ] && { echo "File vide : ajouter des Shorts dans pipeline/shorts.yaml"; exit 0; }
echo "▶ Short $ID"

# 1. vidéo HeyGen
if [ -n "$HEYGEN_ID" ]; then (cd pipeline && python pipeline.py fetch "$ID" "$HEYGEN_ID")
else (cd pipeline && python pipeline.py generate "$ID"); fi
mkdir -p video-agent/takes && cp "pipeline/out/$ID/raw.mp4" "video-agent/takes/$ID.mp4"

# 2. montage
E="video-agent/edits/short-$ID"
rm -rf "$E"
node $SKILL/short.mjs init "$E" --source "video-agent/takes/$ID.mp4"
mkdir -p "$E/assets/logos" && cp assets/emaquis-logo.png "$E/assets/logos/emaquis.png"
node $SKILL/short.mjs words "$E" fr
node $SKILL/short.mjs prepare "$E"
if [ -f "video-agent/specs/$ID.js" ]; then cp "video-agent/specs/$ID.js" "$E/source/spec.js"
else python pipeline/auto_spec.py "$ID" "$E"; fi
node $SKILL/short.mjs prepare "$E"
node $SKILL/short.mjs all "$E"
FINAL="$E/output/short-$ID.mp4"
ls -la "$FINAL"

# 3. publication YouTube (programmée au prochain créneau)
# Route : accès YouTube propre (quota à nous) si autorisé, sinon Treg (quota partagé).
mkdir -p "pipeline/out/$ID" && cp "$FINAL" "pipeline/out/$ID/final.mp4"
if [ -f pipeline/youtube_token.enc ] && [ -n "${YT_CLIENT_SECRET:-}" ]; then
  if [ "$PUBLISH" = 1 ]; then (cd pipeline && python pipeline.py upload "$ID")
  else (cd pipeline && python pipeline.py upload "$ID" --dry-run); fi
else
  if [ "$PUBLISH" = 1 ]; then (cd pipeline && python treg_publish.py "$ID" "../$FINAL")
  else (cd pipeline && python treg_publish.py "$ID" "../$FINAL" --dry-run); fi
fi

# 4. Facebook (Reel sur la Page) + TikTok (boîte de réception) via Treg
SOCIAL_OK=1
if [ "$PUBLISH" = 1 ]; then (cd pipeline && python social_publish.py "$ID" "../$FINAL") || SOCIAL_OK=0
else (cd pipeline && python social_publish.py "$ID" "../$FINAL" --dry-run); fi
echo "FINAL=$FINAL" >> "${GITHUB_OUTPUT:-/dev/null}"
[ "$SOCIAL_OK" = 1 ] || { echo "⚠️ Une publication réseau a échoué (voir ci-dessus)"; exit 1; }
