#!/usr/bin/env python3
"""Vérifie les accès (HeyGen, YouTube) et affiche les identifiants à mettre dans config.yaml.

Lancé par le bouton « Tester les accès » (GitHub Actions) ou à la main :
    HEYGEN_API_KEY=... python check_setup.py
"""
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
HEYGEN = "https://api.heygen.com"
ok = True


def section(title: str) -> None:
    print(f"\n=== {title} ===")


section("HeyGen")
key = os.environ.get("HEYGEN_API_KEY", "")
if not key:
    ok = False
    print("❌ Secret HEYGEN_API_KEY absent.")
else:
    h = {"X-Api-Key": key}
    r = requests.get(f"{HEYGEN}/v2/user/remaining_quota", headers=h, timeout=30)
    if r.status_code != 200:
        ok = False
        print(f"❌ Clé refusée par HeyGen ({r.status_code}) : {r.text[:200]}")
    else:
        print(f"✅ Clé valide. Quota restant : {r.json().get('data', {}).get('remaining_quota')}")

        groups = requests.get(f"{HEYGEN}/v2/avatar_group.list", headers=h, timeout=30).json()
        groups = (groups.get("data") or {}).get("avatar_group_list", [])
        print(f"\nAvatars photo (groupes) : {len(groups)}")
        for g in groups:
            print(f"  • Groupe « {g.get('name')} »  id={g.get('id')}")
            looks = requests.get(f"{HEYGEN}/v2/avatar_group/{g.get('id')}/avatars", headers=h, timeout=30).json()
            for a in (looks.get("data") or {}).get("avatar_list", []):
                img = a.get('image_url') or a.get('preview_image_url') or a.get('motion_preview_url') or ''
                print(f"      look « {a.get('name') or a.get('avatar_name')} »  avatar_id={a.get('id') or a.get('avatar_id')}  image={img}")

        voices = requests.get(f"{HEYGEN}/v2/voices", headers=h, timeout=60).json()
        voices = (voices.get("data") or {}).get("voices", [])
        fr_male = [v for v in voices if "french" in str(v.get("language", "")).lower()
                   and str(v.get("gender", "")).lower() == "male"]
        print(f"\nVoix masculines en français : {len(fr_male)} (les 15 premières)")
        for v in fr_male[:15]:
            print(f"  • {v.get('name')}  voice_id={v.get('voice_id')}  aperçu={v.get('preview_audio')}")

section("YouTube")
token = os.environ.get("YT_TOKEN_JSON", "")
if not token:
    print("⏳ Secret YT_TOKEN_JSON absent (étape 2, plus tard).")
else:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_info(json.loads(token))
        if not creds.valid:
            creds.refresh(Request())
        ch = build("youtube", "v3", credentials=creds).channels().list(part="snippet", mine=True).execute()
        print(f"✅ Connecté à la chaîne : {ch['items'][0]['snippet']['title']}")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"❌ Jeton YouTube invalide : {e}")

print("\nRÉSULTAT :", "✅ tout est prêt pour cette étape" if ok else "❌ à corriger (voir ci-dessus)")
raise SystemExit(0 if ok else 1)
