#!/usr/bin/env python3
"""Publication Facebook (Reel sur la Page) et TikTok (brouillon dans la boîte de réception) via Treg.

    TREG_TOKEN=... python social_publish.py <short_id> <video.mp4> [--dry-run]

- Facebook : la vidéo est hébergée 7 jours chez Treg (treg host), puis Meta la récupère.
  Publication à l'heure du créneau YouTube s'il est dans plus de 15 min, sinon tout de suite.
- TikTok : tant que TikTok n'a pas audité Treg, la publication directe est refusée. La vidéo part
  dans la boîte de réception TikTok : il reste à l'ouvrir dans l'appli et appuyer sur Publier (24 h max).
L'état est enregistré dans state.json : rien n'est envoyé deux fois.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

import pipeline as P
from treg_publish import treg_call

FB_PAGE_ID = "112426258497903"  # Page Facebook « E-Maquis »


def social_export(video: Path) -> Path:
    """Copie légère (< 28 Mo) pour l'hébergement Treg et TikTok."""
    if video.stat().st_size < 28 * 1024 * 1024:
        return video
    out = video.with_name("social.mp4")
    rate = int(28 * 8000 / P.duration(video)) - 160
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-c:v", "libx264", "-preset", "slow",
                    "-b:v", f"{rate}k", "-maxrate", f"{rate}k", "-bufsize", f"{2 * rate}k", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    return out


def caption(short: dict, defaults: dict) -> str:
    tags = " ".join(defaults.get("hashtags", []))
    return f"{short['title']}\n\n{P.clean_text(short['text'])[:900]}\n\n{defaults.get('cta', '')}\n" \
           f"Animé par Tonton Koffi, avatar IA d'E-Maquis.\n{tags}"


def facebook(short_id: str, video: Path, text: str, at: dt.datetime | None) -> str:
    url = subprocess.check_output(["treg", "host", str(video)], text=True, stderr=subprocess.DEVNULL).strip().split()[-1]
    body = {"file_url": url, "description": text, "title": text.splitlines()[0][:100]}
    now = dt.datetime.now(dt.timezone.utc)
    if at and at - now > dt.timedelta(minutes=15):
        body.update(published=False, scheduled_publish_time=int(at.timestamp()))
    r = treg_call("facebook.facebook.page.video.create", {"page_id": FB_PAGE_ID, "fields": "id,permalink_url"}, body)
    if r.status_code >= 400:
        raise RuntimeError(f"Facebook HTTP {r.status_code} : {r.text[:600]}")
    data = r.json()
    data = data.get("data", data)
    link = data.get("permalink_url") or f"https://www.facebook.com/reel/{data.get('id')}"
    if link.startswith("/"):
        link = "https://www.facebook.com" + link
    return link


def tiktok_inbox(video: Path) -> str:
    size = video.stat().st_size
    r = treg_call("tiktok.tiktok.video.inbox.init", {}, {"source_info": {
        "source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}})
    if r.status_code >= 400:
        raise RuntimeError(f"TikTok HTTP {r.status_code} : {r.text[:600]}")
    data = r.json()
    data = data.get("data", data)
    data = data.get("data", data)
    with open(video, "rb") as f:
        up = requests.put(data["upload_url"], data=f, timeout=600, headers={
            "Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size - 1}/{size}"})
    if up.status_code not in (200, 201, 206):
        raise RuntimeError(f"TikTok envoi HTTP {up.status_code} : {up.text[:400]}")
    for _ in range(30):
        time.sleep(10)
        s = treg_call("tiktok.tiktok.publish.status", {}, {"publish_id": data["publish_id"]}).json()
        status = json.dumps(s)
        if "SEND_TO_USER_INBOX" in status or "PUBLISH_COMPLETE" in status:
            return "boîte de réception TikTok"
        if "FAILED" in status:
            raise RuntimeError(f"TikTok : {status[:400]}")
    return "envoyé (traitement TikTok en cours)"


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("id")
    a.add_argument("video")
    a.add_argument("--dry-run", action="store_true")
    args = a.parse_args()

    defaults, shorts = P.load_shorts()
    short = shorts[args.id]
    state = P.load_state()
    entry = state.setdefault(args.id, {})
    at = dt.datetime.fromisoformat(entry["publish_at"]) if entry.get("publish_at") else None
    video = social_export(Path(args.video))
    text = caption(short, defaults)
    if args.dry_run:
        print(f"[réseaux] plan : Facebook ({'programmé ' + at.isoformat() if at else 'maintenant'}), "
              f"TikTok (boîte de réception) — {video.stat().st_size // 1024} Ko")
        return

    failed = False
    for name, done_key, fn in (("Facebook", "facebook", lambda: facebook(args.id, video, text, at)),
                               ("TikTok", "tiktok", lambda: tiktok_inbox(video))):
        if entry.get(done_key):
            print(f"[{name}] déjà fait : {entry[done_key]}")
            continue
        try:
            entry[done_key] = fn()
            print(f"[{name}] ✅ {entry[done_key]}")
        except Exception as e:  # noqa: BLE001 — une plateforme en échec ne bloque pas l'autre
            failed = True
            print(f"[{name}] ❌ {e}")
        P.save_state(state)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
