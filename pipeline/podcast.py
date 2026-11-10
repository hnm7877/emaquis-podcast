#!/usr/bin/env python3
"""Montage d'un épisode long « Le Maquis Parle » (16:9) à partir de la vidéo HeyGen de Tonton Koffi.

    python podcast.py <raw_16x9.mp4> <words.json> <sortie.mp4> "<titre>" <numéro> "<chap1>|<chap2>|..."

- Ouverture (6 s) : le jingle mascotte + « LE MAQUIS PARLE · Épisode N » + titre.
- Émission : Tonton plein cadre (plan fixe), bandeau permanent en haut à gauche,
  bandeau de chapitre « ÉTAPE n · … » à chaque « Étape … » prononcée, sous-titres, musique très basse.
- Fin : carte E-MAQUIS + www.e-maquis.com (même carte que les pubs).
"""
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pub_pos as P  # noqa: E402  (polices, couleurs, carte de fin, outils ffmpeg)

STEP_WORDS = ["un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix"]


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    return "".join(c for c in w if c.isalnum() and unicodedata.category(c) != "Mn")


def chapter_times(words) -> list[float]:
    """Temps de chaque « Étape un / deux / … » dans la voix."""
    out = []
    for i in range(len(words) - 1):
        if norm(words[i][2]) == "etape" and norm(words[i + 1][2]) in STEP_WORDS:
            out.append(words[i][0])
    return out


def srt(words, script: str, out: Path, per=6):
    sw = script.split()
    n, m = len(sw), len(words)
    tm = [(words[min(m - 1, j * m // n)][0], words[min(m - 1, ((j + 1) * m - 1) // n)][1]) for j in range(n)]
    ts = lambda t: f"{int(t // 3600):02}:{int(t // 60 % 60):02}:{int(t % 60):02},{int(round(t % 1 * 1000)) % 1000:03}"
    lines = []
    for k, i in enumerate(range(0, n, per), 1):
        s, e = tm[i][0], tm[min(n - 1, i + per - 1)][1]
        if i + per < n:
            e = min(e, tm[i + per][0])
        lines.append(f"{k}\n{ts(s)} --> {ts(max(e, s + .3))}\n{' '.join(sw[i:i + per])}\n")
    out.write_text("\n".join(lines), encoding="utf-8")


def build(raw: Path, words_json: Path, final: Path, title: str, num: str, chapters: list[str], script: str):
    work = final.parent / f"_work-{final.stem}"
    work.mkdir(parents=True, exist_ok=True)
    words = json.loads(words_json.read_text())
    vd = P.dur(raw)
    times = chapter_times(words)
    print(f"[podcast] {len(times)} chapitres détectés : {times}")

    # 1. ouverture
    intro = work / "intro.mp4"
    jd = 6.0
    fc = ("[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=24:3,"
          f"drawbox=x=0:y=0:w=iw:h=ih:color={P.NAVY}@0.55:t=fill[bg];"
          "[0:v]scale=900:-2,pad=iw+16:ih+16:8:8:white[c];[bg][c]overlay=90:(H-h)/2,"
          + P.dt("LE MAQUIS PARLE", P.BLACK, 54, 1080, 330, box="0x1F1A17@0.9") + ","
          + P.dt(f"Épisode {num}", P.SEMI, 46, 1080, 450, color=P.ORANGE, start=.4) + ","
          + P.dt(title, P.BLACK, 64 if len(title) < 26 else 52, 1080, 530, start=.8) + ","
          + P.dt("avec Tonton Koffi", P.SEMI, 40, 1080, 640, start=1.3)
          + f",fade=t=in:st=0:d=0.3,fade=t=out:st={jd - .4}:d=0.4[v]")
    P.sh(["ffmpeg", "-y", "-loglevel", "error", "-t", jd, "-i", P.JINGLE, "-filter_complex", fc, "-map", "[v]",
          "-map", "0:a", "-af", f"loudnorm=I=-15:TP=-2,aresample=48000,afade=t=out:st={jd - .6}:d=0.6",
          "-r", P.FPS, "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
          "-ac", "2", intro])

    # 2. émission : bandeaux de chapitre + sous-titres + musique basse
    sub = work / "subs.srt"
    srt(words, script, sub)
    draws = [P.dt("LE MAQUIS PARLE", P.BLACK, 34, 50, 44, box="0x1F1A17@0.85"),
             P.dt(f"Ép. {num} · {title}", P.SEMI, 28, 50, 112, box="0x0B1020@0.6")]
    for k, (t, name) in enumerate(zip(times, chapters), 1):
        a = f"between(t,{t:.2f},{t + 5:.2f})"
        draws.append(f"drawbox=x=0:y=760:w=980:h=120:color={P.ORANGE}@0.95:t=fill:enable='{a}'")
        draws.append(f"drawtext=fontfile={P.BLACK}:text='{P.esc(f'ÉTAPE {k}  ·  {name.upper()}')}':fontsize=52:"
                     f"fontcolor=0x1F1A17:x=50:y=792:enable='{a}'")
    style = ("FontName=Poppins SemiBold,Bold=1,PrimaryColour=&H00FFFFFF,BackColour=&H990B1020,"
             "BorderStyle=4,Outline=0,Shadow=0,Alignment=2,FontSize=17,MarginV=26")
    body = work / "body.mp4"
    P.sh(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-stream_loop", "-1", "-i", P.MUSIC,
          "-filter_complex",
          f"[0:v]fps={P.FPS},scale=1920:1080,setsar=1," + ",".join(draws)
          + f",subtitles={sub}:fontsdir={P.FONTS}:force_style='{style}'[v];"
          f"[0:a]loudnorm=I=-15:TP=-2,aresample=48000[vo];[1:a]volume=-28dB,aresample=48000,atrim=0:{vd},"
          f"afade=t=out:st={vd - 2:.2f}:d=2[mu];[vo][mu]amix=inputs=2:duration=first:normalize=0,"
          "aformat=channel_layouts=stereo[a]",
          "-map", "[v]", "-map", "[a]", "-t", vd, "-c:v", "libx264", "-crf", "19", "-preset", "medium",
          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", body])

    # 3. fin
    P.OUTRO_TITLE, P.OUTRO_SUB = "E-MAQUIS", "Appli mobile  •  Web  •  Caisse POS"
    end = work / "outro.mp4"
    P.outro("16x9", end)

    fc = ("[0:v]setsar=1[a];[1:v]setsar=1[b];[2:v]setsar=1[c];"
          "[a][0:a][b][1:a][c][2:a]concat=n=3:v=1:a=1[v][au]")
    P.sh(["ffmpeg", "-y", "-loglevel", "error", "-i", intro, "-i", body, "-i", end, "-filter_complex", fc,
          "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final])
    print(f"✅ {final} ({P.dur(final):.0f} s)")


if __name__ == "__main__":
    import yaml
    raw, words, final, title, num, chaps = sys.argv[1:7]
    sid = sys.argv[7] if len(sys.argv) > 7 else "podcast-01"
    shorts = {s["id"]: s for s in yaml.safe_load((P.ROOT / "pipeline" / "shorts.yaml").read_text())["shorts"]}
    script = " ".join(shorts[sid]["text"].split())
    build(Path(raw), Path(words), Path(final), title, num, chaps.split("|"), script)
