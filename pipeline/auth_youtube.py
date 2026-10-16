#!/usr/bin/env python3
"""Autorisation YouTube, à lancer UNE seule fois sur ton ordinateur.

Ouvre le navigateur, tu te connectes avec le compte Google de la chaîne,
et le jeton (avec refresh token) est enregistré dans youtube_token.json.
"""
from pathlib import Path

import yaml
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]

cfg_path = ROOT / ("config.yaml" if (ROOT / "config.yaml").exists() else "config.example.yaml")
cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))["youtube"]

flow = InstalledAppFlow.from_client_secrets_file(str(ROOT / cfg["client_secrets"]), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
(ROOT / cfg["token_file"]).write_text(creds.to_json())
print(f"✅ Jeton enregistré dans {cfg['token_file']}")
