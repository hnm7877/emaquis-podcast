#!/usr/bin/env python3
"""Accès YouTube chiffré (le dépôt est public).

Le jeton OAuth est stocké dans youtube_token.enc, chiffré avec une clé dérivée du secret GitHub
YT_CLIENT_SECRET (scrypt + Fernet). Sans ce secret, le fichier est illisible.

    python yt_token.py exchange <code>   # échange le code Google contre un jeton, le chiffre
    python yt_token.py check             # affiche la chaîne YouTube connectée
"""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

import requests
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent
ENC = ROOT / "youtube_token.enc"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
REDIRECT = "http://localhost"


def _fernet(salt: bytes) -> Fernet:
    secret = os.environ.get("YT_CLIENT_SECRET", "").encode()
    if not secret:
        sys.exit("Secret YT_CLIENT_SECRET absent.")
    key = hashlib.scrypt(secret, salt=salt, n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)
    return Fernet(base64.urlsafe_b64encode(key))


def save(token: dict) -> None:
    salt = os.urandom(16)
    blob = _fernet(salt).encrypt(json.dumps(token).encode())
    ENC.write_bytes(base64.b64encode(salt) + b"." + blob)


def load() -> dict | None:
    if not ENC.exists():
        return None
    salt, blob = ENC.read_bytes().split(b".", 1)
    return json.loads(_fernet(base64.b64decode(salt)).decrypt(blob))


def credentials():
    """Identifiants Google prêts à l'emploi (rafraîchis si besoin), ou None."""
    data = load()
    if not data:
        return None
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return creds


def exchange(code: str) -> None:
    cid, secret = os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"]
    r = requests.post("https://oauth2.googleapis.com/token", timeout=60, data={
        "code": code.strip(), "client_id": cid, "client_secret": secret,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
    if r.status_code != 200:
        sys.exit(f"Google a refusé le code ({r.status_code}) : {r.text[:400]}")
    t = r.json()
    if "refresh_token" not in t:
        sys.exit("Pas de refresh_token : refaire l'autorisation avec prompt=consent.")
    save({"refresh_token": t["refresh_token"], "client_id": cid, "client_secret": secret,
          "token_uri": "https://oauth2.googleapis.com/token", "scopes": SCOPES})
    print("✅ Accès YouTube enregistré (chiffré) dans youtube_token.enc")


def check() -> None:
    from googleapiclient.discovery import build
    creds = credentials()
    if not creds:
        sys.exit("Aucun accès YouTube enregistré.")
    ch = build("youtube", "v3", credentials=creds).channels().list(part="snippet", mine=True).execute()
    print("✅ Chaîne connectée :", ch["items"][0]["snippet"]["title"])


if __name__ == "__main__":
    if sys.argv[1:2] == ["exchange"]:
        exchange(sys.argv[2])
        check()
    else:
        check()
