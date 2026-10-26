#!/usr/bin/env python3
"""Écrit automatiquement le spec.js de montage (short-editing) d'un Short à partir de :
- pipeline/shorts.yaml (titre, accroche, points forts optionnels)
- files/words.md produit par `short.mjs prepare` (les temps réels de chaque mot)

Gabarit E-Maquis :
  accroche écrite dès la 1re image -> écran partagé avec sous-titres et punch-ins ->
  logo E-Maquis + coches quand « E-Maquis » est prononcé -> plein écran sur la signature finale.

    python auto_spec.py <short_id> <dossier du montage>
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
EMOJI = re.compile(r"[\U0001F000-\U0001FAFF☀-➿️‍#]+")


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^a-z0-9-]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


def read_words(path: Path) -> list[tuple[float, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*([\d.]+)\s*\|\s*[\d.]+\s*\|\s*(.+?)\s*\|$", line)
        if m:
            rows.append((float(m.group(1)), m.group(2)))
    return rows


def find(words, targets, after=0.0):
    targets = {norm(t) for t in targets}
    for t, w in words:
        if t >= after and norm(w) in targets:
            return t
    return None


def hook_lines(title: str) -> list[str]:
    title = EMOJI.sub("", title).replace("Shorts", "").strip(" -:")
    parts = title.split()
    if len(parts) <= 3:
        return [title]
    cut = (len(parts) + 1) // 2
    return [" ".join(parts[:cut]), " ".join(parts[cut:])]


def main(short_id: str, edit_dir: str) -> None:
    edit = Path(edit_dir)
    shorts = {s["id"]: s for s in yaml.safe_load((ROOT / "shorts.yaml").read_text(encoding="utf-8"))["shorts"]}
    short = shorts[short_id]
    words = read_words(edit / "files" / "words.md")
    end = words[-1][0] + 0.6

    brand_at = find(words, ["E-Maquis", "Emaki", "Emaquis", "E-Maki", "Imaki"], after=2.0)
    sign_at = find(words, ["Ici"], after=(brand_at or 0) + 1.0)
    stops = [t for t, w in words if t > 1.0 and w.rstrip().endswith(("?", ".", "!"))]
    # l'accroche reste jusqu'à la 2e phrase (au moins ~3 s), sans empiéter sur la marque
    first_stop = next((t for t in stops if t >= 3.0), stops[0] if stops else 3.0)
    if brand_at:
        first_stop = min(first_stop, brand_at - .8)

    lines = short.get("hook") or hook_lines(short["title"])
    if isinstance(lines, str):
        lines = [lines]
    emph = short.get("hook_emph", "")
    hook_items = [
        {"k": "text", "text": l, "size": 104, "x": 540, "y": 380 + 130 * i, "at": 0, "pre": .5,
         **({"emph": emph, "emphAt": 0} if emph and emph in l else {})}
        for i, l in enumerate(lines[:3])
    ]
    scenes = [{"type": "board", "from": 0, "to": round(first_stop + .4, 2), "pre": .5, "items": hook_items}]

    if brand_at:
        board_to = round((sign_at or end) - .15, 2)
        items = [{"k": "logo", "logo": "assets/logos/emaquis.png", "s": 380, "x": 540, "y": 330, "at": brand_at}]
        points = short.get("points") or []
        span = max(1.0, board_to - brand_at - .6)
        for i, p in enumerate(points[:3]):
            at = round(brand_at + .6 + span * i / max(1, len(points[:3])), 2)
            y = 600 + 140 * i
            items += [{"k": "check", "s": 70, "x": 200, "y": y, "at": round(at + .3, 2)},
                      {"k": "text", "text": p, "size": 70, "x": 600, "y": y, "at": at}]
        scenes.append({"type": "board", "from": brand_at, "to": board_to, "items": items})

    # vues : écran partagé, plein écran sur la signature finale
    layout = [[0, 1160], [round(first_stop + .5, 2), 0]]   # visage plein écran entre l'accroche et la marque
    if brand_at:
        layout.append([round(brand_at - .1, 2), 1160])
    if sign_at:
        layout.append([round(sign_at - .1, 2), 0])
    # un punch-in discret toutes les ~4 s pour garder du mouvement
    zoom, t, z = [[0, 1]], 3.0, 1.06
    while t < end - 1:
        zoom.append([round(t, 2), z, 400])
        z = 1.0 if z > 1 else 1.06
        t += 4.0

    spec = {
        "title": EMOJI.sub("", short["title"]).strip(),
        "media": {},
        "cam": {"crop": [0, 0, 1080, 1920], "eyes": [555, 640], "splitZoom": 1},
        "cut": [],
        "layout": {"keys": layout},
        "zoom": {"keys": zoom},
        "actors": [],
        "scenes": scenes,
        "music": {"bed": short.get("music", "enquete"), "offset": 0},
        "sfx": {"swish": 0, "accents": 0, "extra": [[brand_at, "pop", -6]] if brand_at else []},
        "captions": {
            "replace": [[w, "E-Maquis"] for w in ["Emaki", "Emaquis", "E-Maki", "Imaki"]],
            "emph": short.get("emph", ["E-Maquis", "argent", "stock", "caisse"]),
            "hide": [],
        },
    }
    out = edit / "source" / "spec.js"
    out.write_text(f"// Généré par pipeline/auto_spec.py pour {short_id}. Temps = SOURCE secondes.\n"
                   f"window.SPEC = {json.dumps(spec, ensure_ascii=False, indent=2)};\n", encoding="utf-8")
    print(f"[auto_spec] {out} : accroche {lines}, marque à {brand_at}, signature à {sign_at}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
