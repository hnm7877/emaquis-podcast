#!/usr/bin/env python3
"""Publication YouTube via Treg (connexion YouTube de l'utilisateur, aucun projet Google Cloud).

    TREG_TOKEN=... python treg_publish.py <short_id> <video.mp4> [--now] [--dry-run]

Par défaut : mise en ligne en privé + publication programmée au prochain créneau (config.yaml).
L'état est enregistré dans state.json pour ne jamais publier deux fois le même Short.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import requests

import pipeline as P

TREG = "https://treg.to/call"


def treg_call(tool: str, query: dict, body: dict) -> requests.Response:
    token = os.environ.get("TREG_TOKEN")
    if not token:
        sys.exit("TREG_TOKEN manquant.")
    for attempt in range(5):  # Treg peut répondre 503 quand il est saturé : on réessaie
        r = requests.post(f"{TREG}/{tool}", params=query, json=body, timeout=120,
                          headers={"X-Treg-Token": token, "Content-Type": "application/json"})
        if r.status_code not in (429, 502, 503, 504):
            return r
        time.sleep(10 * (attempt + 1))
    return r


def youtube_upload(short_id: str, video: Path, now: bool, dry_run: bool) -> str | None:
    cfg = P.load_config()
    defaults, shorts = P.load_shorts()
    state = P.load_state()
    if state.get(short_id, {}).get("youtube_id"):
        print(f"Déjà en ligne : https://youtube.com/shorts/{state[short_id]['youtube_id']}")
        return state[short_id]["youtube_id"]

    meta = P.metadata(shorts[short_id], defaults)
    status = {"selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}
    if now:
        status["privacyStatus"] = "public"
        when = dt.datetime.now(dt.timezone.utc)
    else:
        when = P.next_slot(cfg, state)
        status.update(privacyStatus="private", publishAt=when.strftime("%Y-%m-%dT%H:%M:%SZ"))
    body = {"snippet": {**meta, "categoryId": cfg["youtube"]["category_id"],
                        "defaultLanguage": "fr", "defaultAudioLanguage": "fr"},
            "status": status}
    print("[youtube] plan :", json.dumps({"titre": meta["title"], "publication": when.isoformat(),
                                          "statut": status["privacyStatus"]}, ensure_ascii=False))
    if dry_run:
        return None

    r = treg_call("youtube.youtube.video.upload",
                  {"part": "id,snippet,status", "uploadType": "resumable"}, body)
    session = r.headers.get("Location") or r.headers.get("location")
    if not session:
        try:
            data = r.json()
        except ValueError:
            data = {}
        session = (data.get("location") or data.get("Location")
                   or (data.get("headers") or {}).get("location") or (data.get("headers") or {}).get("Location"))
    if r.status_code >= 400 or not session:
        sys.exit(f"[youtube] pas de session d'envoi (HTTP {r.status_code}) : {r.text[:800]}")

    size = video.stat().st_size
    with open(video, "rb") as f:
        up = requests.put(session, data=f, timeout=900,
                          headers={"Content-Type": "video/mp4", "Content-Length": str(size)})
    if up.status_code not in (200, 201):
        sys.exit(f"[youtube] envoi refusé (HTTP {up.status_code}) : {up.text[:800]}")
    vid = up.json()["id"]
    state = P.load_state()
    state.setdefault(short_id, {}).update(youtube_id=vid, publish_at=when.isoformat(), route="treg")
    P.save_state(state)
    print(f"[youtube] ✅ {short_id} -> https://youtube.com/shorts/{vid} "
          f"({'public maintenant' if now else f'programmé le {when:%d/%m à %H:%M} UTC'})")
    return vid


def make_public(short_id: str) -> None:
    """Rend public immédiatement un Short déjà envoyé (annule la programmation)."""
    state = P.load_state()
    vid = state.get(short_id, {}).get("youtube_id")
    if not vid:
        sys.exit(f"{short_id} n'a pas encore été envoyé sur YouTube.")
    body = {"id": vid, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                                  "containsSyntheticMedia": True}}
    token = os.environ.get("TREG_TOKEN")
    for attempt in range(5):  # Treg peut répondre 503 quand il est saturé : on réessaie
        r = requests.put(f"{TREG}/youtube.x.youtube-videos-update", params={"part": "status"}, json=body,
                         timeout=120, headers={"X-Treg-Token": token, "Content-Type": "application/json"})
        if r.status_code not in (429, 502, 503, 504):
            break
        time.sleep(10 * (attempt + 1))
    if r.status_code >= 400:
        sys.exit(f"[youtube] mise en public refusée (HTTP {r.status_code}) : {r.text[:800]}")
    now = dt.datetime.now(dt.timezone.utc)
    state[short_id].update(publish_at=now.isoformat(), public=True)
    P.save_state(state)
    print(f"[youtube] ✅ {short_id} est PUBLIC : https://youtube.com/shorts/{vid}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--make-public":
        make_public(sys.argv[2])
        sys.exit(0)
    a = argparse.ArgumentParser()
    a.add_argument("id")
    a.add_argument("video")
    a.add_argument("--now", action="store_true")
    a.add_argument("--dry-run", action="store_true")
    args = a.parse_args()
    youtube_upload(args.id, Path(args.video), args.now, args.dry_run)
