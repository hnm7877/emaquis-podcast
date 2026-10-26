#!/usr/bin/env python3
"""Chaîne de production des Shorts « La Minute E-Maquis ».

    python pipeline.py plan                 # calendrier des prochains Shorts
    python pipeline.py generate ep01-s1     # vidéo avatar via HeyGen  -> out/<id>/raw.mp4
    python pipeline.py placeholder ep01-s1  # fausse vidéo locale pour tester sans HeyGen
    python pipeline.py brand ep01-s1        # sous-titres + logo        -> out/<id>/final.mp4
    python pipeline.py upload ep01-s1       # mise en ligne YouTube programmée
    python pipeline.py next                 # enchaîne tout pour le prochain Short en attente
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
STATE_FILE = ROOT / "state.json"
HEYGEN = "https://api.heygen.com"


# ---------------------------------------------------------------- utilitaires
def load_yaml(name: str) -> dict:
    with open(ROOT / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config() -> dict:
    path = ROOT / "config.yaml"
    cfg = load_yaml("config.yaml" if path.exists() else "config.example.yaml")
    cfg["heygen"]["api_key"] = os.environ.get("HEYGEN_API_KEY") or cfg["heygen"].get("api_key", "")
    return cfg


def load_shorts() -> tuple[dict, dict[str, dict]]:
    data = load_yaml("shorts.yaml")
    shorts = {s["id"]: s for s in data["shorts"]}
    return data.get("defaults", {}), shorts


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
    )
    return float(out)


# ---------------------------------------------------------------- HeyGen
def generate(short_id: str) -> Path:
    cfg = load_config()["heygen"]
    _, shorts = load_shorts()
    short = shorts[short_id]
    if not cfg["api_key"]:
        sys.exit("HEYGEN_API_KEY manquant (config.yaml ou variable d'environnement).")
    avatar_id = cfg["outfits"].get(short["outfit"])
    if not avatar_id:
        sys.exit(f"Aucun look HeyGen configuré pour la tenue {short['outfit']}.")

    headers = {"X-Api-Key": cfg["api_key"], "Content-Type": "application/json"}
    # API v3 + moteur Avatar IV : mouvements de tête, expressions et lèvres plus naturels
    body = {
        "type": "avatar",
        "avatar_id": avatar_id,
        "script": clean_text(short["text"]),
        "voice_id": cfg["voice_id"],
        "voice_settings": {"speed": cfg.get("voice_speed", 1.0)},
        "resolution": "1080p",
        "aspect_ratio": "9:16",
        "fit": "cover",
        "engine": {"type": cfg.get("engine", "avatar_iv")},
        "expressiveness": cfg.get("expressiveness", "medium"),
        "motion_prompt": cfg.get("motion_prompt") or None,
        "title": f"E-Maquis {short_id}",
    }
    r = requests.post(f"{HEYGEN}/v3/videos", headers=headers, json=body, timeout=60)
    if r.status_code >= 400:
        sys.exit(f"[heygen] refus {r.status_code} : {r.text[:500]}")
    video_id = r.json()["data"]["video_id"]
    print(f"[heygen] vidéo lancée : {video_id}")

    state = load_state()
    state.setdefault(short_id, {})["heygen_video_id"] = video_id
    save_state(state)
    return fetch(short_id, video_id)


def fetch(short_id: str, video_id: str) -> Path:
    """Attend (si besoin) puis télécharge une vidéo HeyGen déjà lancée."""
    cfg = load_config()["heygen"]
    headers = {"X-Api-Key": cfg["api_key"]}
    for i in range(120):  # jusqu'à 60 min
        if i:
            time.sleep(30)
        s = requests.get(f"{HEYGEN}/v3/videos/{video_id}", headers=headers, timeout=60).json().get("data", {})
        print(f"[heygen] statut : {s.get('status')}")
        if s.get("status") == "completed":
            dest = OUT / short_id / "raw.mp4"
            dest.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(s["video_url"], stream=True, timeout=300) as dl:
                dl.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in dl.iter_content(1 << 20):
                        f.write(chunk)
            return dest
        if s.get("status") == "failed":
            sys.exit(f"[heygen] échec : {s.get('failure_code')} {s.get('failure_message')}")
    sys.exit("[heygen] délai dépassé.")


def placeholder(short_id: str) -> Path:
    """Vidéo de test 9:16 (fond orange + bip) pour valider la chaîne sans HeyGen."""
    _, shorts = load_shorts()
    words = len(clean_text(shorts[short_id]["text"]).split())
    secs = max(10, round(words / 2.6))  # ~2,6 mots/s en français parlé
    dest = OUT / short_id / "raw.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=0xE8701A:s=1080x1920:d={secs}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={secs}",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(dest),
    ], check=True)
    return dest


# ---------------------------------------------------------------- sous-titres et habillage
def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def whisper_srt(video: Path, script: str = "", words_per_line: int = 4) -> str | None:
    """Sous-titres calés mot à mot sur la vraie voix (faster-whisper), si disponible."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    import numpy as np
    try:
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video), "-ac", "1", "-ar", "16000",
                              "-f", "s16le", "-"], capture_output=True, check=True).stdout
        audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio, language="fr", word_timestamps=True)
        words = [w for seg in segments for w in seg.words]
    except Exception as e:  # noqa: BLE001
        print(f"[sous-titres] whisper indisponible ({e}), timing estimé utilisé.")
        return None
    if not words:
        return None
    # Le texte vient du script (orthographe exacte), les temps viennent de la voix réelle.
    timed = [(w.word.strip(), w.start, w.end) for w in words]
    script_words = clean_text(script).split()
    if script_words and abs(len(script_words) - len(words)) <= 0.2 * len(script_words):
        n, m = len(script_words), len(words)
        timed = [(sw, words[min(m - 1, j * m // n)].start, words[min(m - 1, ((j + 1) * m - 1) // n)].end)
                 for j, sw in enumerate(script_words)]
    chunks = [timed[i:i + words_per_line] for i in range(0, len(timed), words_per_line)]
    out = []
    for k, chunk in enumerate(chunks):
        start = chunk[0][1]
        end = chunk[-1][2] if k + 1 == len(chunks) else min(chunk[-1][2], chunks[k + 1][0][1])
        text = " ".join(t[0] for t in chunk).upper()
        out.append(f"{k + 1}\n{_ts(start)} --> {_ts(max(end, start + 0.2))}\n{text}\n")
    return "\n".join(out) or None


def build_srt(text: str, total: float, words_per_line: int = 5) -> str:
    """Découpe le texte en petites lignes, réparties au prorata du nombre de caractères."""
    words = clean_text(text).split()
    lines = [" ".join(words[i:i + words_per_line]) for i in range(0, len(words), words_per_line)]
    weights = [len(l) for l in lines]
    scale = (total - 0.3) / sum(weights)

    def ts(t: float) -> str:
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

    out, t = [], 0.15
    for i, (line, w) in enumerate(zip(lines, weights), 1):
        end = t + w * scale
        out.append(f"{i}\n{ts(t)} --> {ts(end)}\n{line.upper()}\n")
        t = end
    return "\n".join(out)


def fill_filter(raw: Path) -> str:
    """Si HeyGen a laissé des bandes (photo 4:5 dans un cadre 9:16), zoome pour remplir l'écran."""
    probe = subprocess.run(
        ["ffmpeg", "-ss", "2", "-i", str(raw), "-t", "3", "-vf", "cropdetect=limit=60:round=2:reset=0",
         "-f", "null", "-"], capture_output=True, text=True).stderr
    found = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", probe)
    if not found:
        return ""
    w, h, x, y = map(int, found[-1])
    if h >= 1880:
        return ""
    return f"crop={w}:{h}:{x}:{y},scale=-2:1920,crop=1080:1920,setsar=1,"


def brand(short_id: str) -> Path:
    cfg = load_config()["branding"]
    _, shorts = load_shorts()
    folder = OUT / short_id
    raw = folder / "raw.mp4"
    if not raw.exists():
        sys.exit(f"{raw} introuvable : lancer d'abord generate (ou placeholder).")

    srt = folder / "subs.srt"
    subs = whisper_srt(raw, shorts[short_id]["text"]) or build_srt(shorts[short_id]["text"], duration(raw))
    srt.write_text(subs, encoding="utf-8")

    style = (f"FontName={cfg.get('font', 'Arial')},FontSize=13,Bold=1,PrimaryColour=&H0000FFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=55")
    vf = f"{fill_filter(raw)}subtitles={srt.name}:force_style='{style}'"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", raw.name]
    logo = ROOT / cfg.get("logo_path", "")
    if cfg.get("logo_path") and logo.exists():
        cmd += ["-i", str(logo)]
        vf = (f"[0:v]{vf}[v];[1:v]scale=220:-1[l];[v][l]overlay=W-w-40:60")
        cmd += ["-filter_complex", vf]
    else:
        cmd += ["-vf", vf]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "final.mp4"]
    subprocess.run(cmd, check=True, cwd=folder)
    final = folder / "final.mp4"
    if duration(final) > 60:
        print("⚠️  Plus de 60 s : YouTube ne le classera pas en Short. Raccourcir le texte.")
    return final


# ---------------------------------------------------------------- planning et YouTube
def next_slot(cfg: dict, state: dict) -> dt.datetime:
    yt, sched = cfg["youtube"], cfg["schedule"]
    taken = [dt.datetime.fromisoformat(v["publish_at"]) for v in state.values() if v.get("publish_at")]
    now = dt.datetime.now(dt.timezone.utc)
    day = max(taken + [now]).date()
    while True:
        slot = dt.datetime.combine(day, dt.time(yt["publish_hour_utc"]), dt.timezone.utc)
        if slot > now + dt.timedelta(hours=1) and day.weekday() in sched["weekdays"] \
                and sum(t.date() == day for t in taken) < sched["per_day"]:
            return slot
        day += dt.timedelta(days=1)


def metadata(short: dict, defaults: dict) -> dict:
    title = short["title"]
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"
    description = "\n\n".join([
        clean_text(short["text"]),
        defaults.get("cta", ""),
        "Animé par Tonton Kofi, avatar généré par IA pour E-Maquis.",
        " ".join(defaults.get("hashtags", [])),
    ])
    return {"title": title[:100], "description": description[:5000],
            "tags": short.get("tags", defaults.get("tags", []))}


def youtube_client(cfg: dict):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    import yt_token
    enc_creds = yt_token.credentials()  # accès chiffré du dépôt (GitHub Actions)
    if enc_creds:
        return build("youtube", "v3", credentials=enc_creds)
    token = ROOT / cfg["youtube"]["token_file"]
    if not token.exists():
        sys.exit("Token YouTube absent : lancer d'abord le bouton « Autoriser YouTube ».")
    creds = Credentials.from_authorized_user_file(str(token))
    if not creds.valid:
        creds.refresh(Request())
        token.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(short_id: str, publish_at: dt.datetime | None = None, dry_run: bool = False) -> str | None:
    cfg = load_config()
    defaults, shorts = load_shorts()
    state = load_state()
    final = OUT / short_id / "final.mp4"
    if not final.exists():
        sys.exit(f"{final} introuvable : lancer d'abord brand.")
    if state.get(short_id, {}).get("youtube_id"):
        print(f"Déjà en ligne : https://youtu.be/{state[short_id]['youtube_id']}")
        return state[short_id]["youtube_id"]

    publish_at = publish_at or next_slot(cfg, state)
    meta = metadata(shorts[short_id], defaults)
    body = {
        "snippet": {**meta, "categoryId": cfg["youtube"]["category_id"],
                    "defaultLanguage": "fr", "defaultAudioLanguage": "fr"},
        "status": {
            "privacyStatus": cfg["youtube"]["privacy"],
            "publishAt": publish_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # déclaration IA exigée par YouTube
        },
    }
    if dry_run:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return None

    from googleapiclient.http import MediaFileUpload
    yt = youtube_client(cfg)
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(final), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    state.setdefault(short_id, {}).update(youtube_id=vid, publish_at=publish_at.isoformat(), route="google")
    save_state(state)
    print(f"[youtube] {short_id} -> https://youtu.be/{vid} (publication {publish_at:%d/%m %H:%M} UTC)")
    return vid


def make_public(short_id: str) -> None:
    """Rend public tout de suite un Short déjà envoyé (accès YouTube propre)."""
    state = load_state()
    vid = state.get(short_id, {}).get("youtube_id")
    if not vid:
        sys.exit(f"{short_id} n'a pas encore été envoyé sur YouTube.")
    yt = youtube_client(load_config())
    yt.videos().update(part="status", body={"id": vid, "status": {
        "privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}).execute()
    state[short_id].update(publish_at=dt.datetime.now(dt.timezone.utc).isoformat(), public=True)
    save_state(state)
    print(f"[youtube] ✅ {short_id} est PUBLIC : https://youtube.com/shorts/{vid}")


def plan() -> None:
    cfg = load_config()
    _, shorts = load_shorts()
    state = load_state()
    sim = dict(state)
    for sid, s in shorts.items():
        if sim.get(sid, {}).get("youtube_id"):
            print(f"✅ {sid:9} {sim[sid]['publish_at'][:16]}  {s['title']}")
            continue
        slot = next_slot(cfg, sim)
        sim[sid] = {"publish_at": slot.isoformat()}
        print(f"⏳ {sid:9} {slot:%a %d/%m %H:%M}Z  [{s['outfit']}] {s['title']}")


def run_next(use_placeholder: bool, dry_run: bool) -> None:
    _, shorts = load_shorts()
    state = load_state()
    pending = [sid for sid in shorts if not state.get(sid, {}).get("youtube_id")]
    if not pending:
        print("File vide : ajouter des Shorts dans shorts.yaml.")
        return
    sid = pending[0]
    print(f"▶ {sid} : {shorts[sid]['title']}")
    if not (OUT / sid / "raw.mp4").exists():
        placeholder(sid) if use_placeholder else generate(sid)
    brand(sid)
    upload(sid, dry_run=dry_run)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    fe = sub.add_parser("fetch")
    fe.add_argument("id")
    fe.add_argument("video_id")
    for name in ("generate", "placeholder", "brand"):
        sub.add_parser(name).add_argument("id")
    sub.add_parser("public").add_argument("id")
    up = sub.add_parser("upload")
    up.add_argument("id")
    up.add_argument("--dry-run", action="store_true")
    nx = sub.add_parser("next")
    nx.add_argument("--placeholder", action="store_true", help="vidéo de test au lieu de HeyGen")
    nx.add_argument("--dry-run", action="store_true", help="ne pas envoyer sur YouTube")
    a = p.parse_args()

    if a.cmd == "plan":
        plan()
    elif a.cmd == "generate":
        print(generate(a.id))
    elif a.cmd == "fetch":
        print(fetch(a.id, a.video_id))
    elif a.cmd == "placeholder":
        print(placeholder(a.id))
    elif a.cmd == "brand":
        print(brand(a.id))
    elif a.cmd == "public":
        make_public(a.id)
    elif a.cmd == "upload":
        upload(a.id, dry_run=a.dry_run)
    elif a.cmd == "next":
        run_next(a.placeholder, a.dry_run)


if __name__ == "__main__":
    main()
