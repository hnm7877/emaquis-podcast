#!/usr/bin/env python3
"""Publicité « E-Maquis POS » (Windows) : voix off et visage de Tonton Koffi + captures du POS.

    python pub_pos.py <voix_heygen.mp4> <demo_pos.mp4> <slides_dir> <words.json> <sortie_dir>

Produit deux formats, sans zoom (plans fixes, fondus courts) :
  - pub-pos-16x9.mp4  (YouTube, Facebook, site web)
  - pub-pos-9x16.mp4  (Reels, TikTok, Shorts, statuts WhatsApp)
Structure (temps de la voix) : accroche face caméra -> 7 plans produit calés sur la phrase ->
signature face caméra -> carte de fin avec le jingle mascotte et www.e-maquis.com.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / ".claude" / "skills" / "short-editing" / "engine" / "fonts"
BLACK, SEMI = FONTS / "ArchivoBlack.ttf", FONTS / "Poppins-SemiBold.ttf"
JINGLE = ROOT / "assets" / "jingle-emaquis.mp4"
MUSIC = ROOT / ".claude" / "skills" / "short-editing" / "assets" / "music" / "arpege.mp3"
ORANGE, NAVY = "0xF29A1F", "0x0B1020"
FPS = 30

SCRIPT = ("Patron, ton maquis tourne fort le week-end. Mais ta caisse, elle suit ? "
          "Voici E-Maquis POS, la caisse tactile de ton maquis, sur Windows. "
          "Boissons, plats, zones : tout ton bar sur un seul écran. Tu touches, c'est dans le panier. "
          "En cuisine, chaque commande arrive en direct, de « Commencer » jusqu'à « Servie ». "
          "Sur un second écran, ton client voit sa commande et le total. Paiement confirmé, monnaie affichée. "
          "Et ton chiffre du jour, tu le suis en temps réel. "
          "E-Maquis POS : commande, vends, analyse. Télécharge-le sur e-maquis.com.")

OUTRO_TITLE, OUTRO_SUB, NAME = "E-MAQUIS POS", "Windows  •  Caisse barman  •  Cuisine", "pub-pos"

# (début, fin, visuel) en secondes de la voix ; visuel = ("face",) | ("slide", n) | ("demo", t0)
PLAN = [
    (0.00, 4.80, ("face", "Ta caisse suit ?")),
    (4.80, 9.20, ("slide", 6)),
    (9.20, 12.90, ("demo", 4.0)),
    (12.90, 14.85, ("demo", 8.3)),
    (14.85, 20.10, ("slide", 7)),
    (20.10, 23.70, ("slide", 8)),
    (23.70, 26.10, ("slide", 9)),
    (26.10, 28.45, ("demo", 17.6)),
    (28.45, None, ("face", "E-MAQUIS POS")),
]


def sh(cmd: list) -> None:
    subprocess.run([str(c) for c in cmd], check=True)


def dur(p: Path) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]))


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace(":", r"\:").replace("'", "’").replace("%", r"\%")


def dt(t, font, size, x, y, color="white", start=0.0, box=""):
    a = f"if(lt(t,{start}),0,min(1,(t-{start})/0.3))"
    b = f":box=1:boxcolor={box}:boxborderw=22" if box else ""
    return f"drawtext=fontfile={font}:text='{esc(t)}':fontsize={size}:fontcolor={color}:x={x}:y={y}:alpha='{a}'{b}"


def bg(w, h):
    """Fond sombre avec une lueur orange en haut à droite (comme les visuels POS)."""
    return (f"color=c={NAVY}:s={w}x{h}:r={FPS},format=rgba,"
            f"geq=r='r(X,Y)+90*exp(-((X-{w}*0.85)^2+(Y-{h}*0.05)^2)/({w}*{w}*0.12))':"
            f"g='g(X,Y)+55*exp(-((X-{w}*0.85)^2+(Y-{h}*0.05)^2)/({w}*{w}*0.12))':"
            f"b='b(X,Y)':a=255")


# ---------------------------------------------------------------- un plan, deux formats
def segment(fmt, i, a, b, vis, voice, demo, slides, out):
    d = b - a
    W, H = (1920, 1080) if fmt == "16x9" else (1080, 1920)
    face = f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={FPS}"
    inputs = ["-i", voice]
    kind = vis[0]
    if kind == "face":
        title = vis[1]
        if fmt == "16x9":
            fc = (f"{bg(W, H)},trim=duration={d}[bg];"
                  f"{face},crop=1080:1350:0:0,scale=780:975,pad=iw+16:ih+16:8:8:white[f];"
                  f"[bg][f]overlay=1040:52,"
                  + dt("LA MINUTE E-MAQUIS", BLACK, 40, 110, 300, box="0x1F1A17@0.9") + ","
                  + dt(title, BLACK, 110 if len(title) < 16 else 92, 110, 420, color=ORANGE, start=.15) + ","
                  + dt("Pour les maquis, bars et restos", SEMI, 40, 110, 600, start=.4)
                  + (("," + dt("www.e-maquis.com", BLACK, 64, 110, 760, start=2.2)) if "E-MAQUIS" in title else "")
                  + "[v]")
        else:
            fc = (f"{face},crop=1080:1920:0:0[f];[f]"
                  + dt("LA MINUTE E-MAQUIS", BLACK, 46, "(w-text_w)/2", 150, box="0x1F1A17@0.9") + ","
                  + dt(title, BLACK, 104 if len(title) < 16 else 92, "(w-text_w)/2", 1330, color=ORANGE, start=.15,
                       box="0x0B1020@0.75")
                  + (("," + dt("www.e-maquis.com", BLACK, 64, "(w-text_w)/2", 1490, start=2.2, box="0x0B1020@0.75"))
                     if "E-MAQUIS" in title else "")
                  + "[v]")
    else:
        if kind == "slide":
            img = Path(vis[1]) if not str(vis[1]).isdigit() else slides / f"{vis[1]}.png"
            inputs += ["-loop", "1", "-t", f"{d}", "-i", ROOT / img if not img.is_absolute() else img]
            # contenu entier, sans déformation (captures portrait ou paysage), sur fond marine
            src = (f"[1:v]fps={FPS},scale=1920:1080:force_original_aspect_ratio=decrease,"
                   f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color={NAVY},setsar=1,trim=duration={d}")
        else:
            inputs += ["-ss", f"{vis[1]}", "-t", f"{d}", "-i", demo]
            src = f"[1:v]fps={FPS},scale=1920:1080,setsar=1,setpts=PTS-STARTPTS"
        if fmt == "16x9":
            # visuel plein écran + Tonton en médaillon rond (il continue de parler)
            fc = (f"{src}[s];{face},crop=900:900:90:150,scale=300:300,format=rgba,"
                  f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(hypot(X-150,Y-150),146),255,0)'[m];"
                  f"color=c=white:s=316x316:r={FPS},format=rgba,"
                  f"geq=r=242:g=154:b=31:a='if(lt(hypot(X-158,Y-158),157),255,0)',trim=duration={d}[ring];"
                  f"[s][ring]overlay=W-w-48:H-h-48[s2];[s2][m]overlay=W-w-56:H-h-56[v]")
        else:
            # visage en haut, écran du POS au milieu, sous-titres en bas
            fc = (f"{bg(W, H)},trim=duration={d}[bg];"
                  f"{face},crop=1080:880:0:120[f];"
                  f"{src},scale=1040:585,pad=iw+12:ih+12:6:6:{ORANGE}[s];"
                  f"[bg][f]overlay=0:0[b1];[b1][s]overlay=(W-w)/2:960,"
                  f"drawbox=x=0:y=874:w=iw:h=6:color={ORANGE}:t=fill[v]")
    sh(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[v]",
        "-t", f"{d}", "-r", FPS, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-an", out])


# ---------------------------------------------------------------- sous-titres (texte exact du script)
def srt(words_json: Path, out: Path, per=4):
    wh = json.loads(words_json.read_text())
    sw = SCRIPT.replace("« ", "«").replace(" »", "»").split()
    n, m = len(sw), len(wh)
    tm = [(wh[min(m - 1, j * m // n)][0], wh[min(m - 1, ((j + 1) * m - 1) // n)][1]) for j in range(n)]
    lines, k = [], 0
    for i in range(0, n, per):
        chunk = sw[i:i + per]
        s, e = tm[i][0], tm[min(n - 1, i + per - 1)][1]
        if i + per < n:
            e = min(e, tm[i + per][0])
        k += 1
        ts = lambda t: f"{int(t // 3600):02}:{int(t // 60 % 60):02}:{int(t % 60):02},{int(round(t % 1 * 1000)):03}"
        lines.append(f"{k}\n{ts(s)} --> {ts(max(e, s + .25))}\n{' '.join(chunk).replace('«', '« ').replace('»', ' »')}\n")
    out.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- carte de fin
def outro(fmt, out):
    d = dur(JINGLE)
    if fmt == "16x9":
        fc = ("[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=28:3,"
              f"drawbox=x=0:y=0:w=iw:h=ih:color={NAVY}@0.6:t=fill[bg];"
              "[0:v]scale=980:-2,pad=iw+16:ih+16:8:8:white[c];[bg][c]overlay=70:(H-h)/2,"
              + dt("Télécharge", SEMI, 60, 1130, 330, start=.5) + ","
              + dt(OUTRO_TITLE, BLACK, 86, 1130, 405, color=ORANGE, start=.8) + ","
              + dt(OUTRO_SUB, SEMI, 32, 1130, 530, start=1.3) + ","
              + dt("www.e-maquis.com", BLACK, 56, 1130, 630, start=1.9, box="0x1F1A17@0.9")
              + f",fade=t=in:st=0:d=0.25,fade=t=out:st={d - .4:.2f}:d=0.4[v]")
    else:
        fc = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:4,"
              f"drawbox=x=0:y=0:w=iw:h=ih:color={NAVY}@0.6:t=fill[bg];"
              "[0:v]scale=1000:-2,pad=iw+24:ih+24:12:12:white[c];[bg][c]overlay=(W-w)/2:520,"
              + dt("LA MINUTE E-MAQUIS", BLACK, 56, "(w-text_w)/2", 240, box="0x1F1A17@0.9") + ","
              + dt("Télécharge", SEMI, 72, "(w-text_w)/2", 1200, start=.5) + ","
              + dt(OUTRO_TITLE, BLACK, 110, "(w-text_w)/2", 1290, color=ORANGE, start=.8) + ","
              + dt(OUTRO_SUB, SEMI, 40, "(w-text_w)/2", 1450, start=1.3) + ","
              + dt("www.e-maquis.com", BLACK, 72, "(w-text_w)/2", 1580, start=1.9, box="0x1F1A17@0.9")
              + f",fade=t=in:st=0:d=0.25,fade=t=out:st={d - .4:.2f}:d=0.4[v]")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", JINGLE, "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
        "-af", f"loudnorm=I=-14:TP=-1.5,aresample=48000,afade=t=out:st={d - .5:.2f}:d=0.5", "-r", FPS,
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ac", "2", out])


def build(fmt, voice, demo, slides, words, outdir):
    work = outdir / f"_work-{NAME}-{fmt}"
    work.mkdir(parents=True, exist_ok=True)
    vd = dur(voice)
    parts = []
    for i, (a, b, vis) in enumerate(PLAN):
        b = b or vd
        p = work / f"seg{i:02}.mp4"
        segment(fmt, i, a, b, vis, voice, demo, slides, p)
        parts.append(p)
    # enchaînement avec de courts fondus (0,25 s), sans zoom
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    body = work / "body.mp4"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", body])

    sub = work / "subs.srt"
    srt(words, sub, per=4 if fmt == "16x9" else 3)
    style = ("FontName=Poppins SemiBold,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H990B1020,"
             "BorderStyle=4,Outline=0,Shadow=0,Alignment=2,"
             + ("FontSize=17,MarginV=22" if fmt == "16x9" else "FontSize=13,MarginV=34"))
    # voix + musique douce sous la voix (-20 dB), puis la carte de fin
    mixed = work / "body-mix.mp4"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", body, "-i", voice, "-stream_loop", "-1", "-i", MUSIC,
        "-filter_complex",
        f"[0:v]subtitles={sub}:fontsdir={FONTS}:force_style='{style}'[v];"
        f"[1:a]loudnorm=I=-15:TP=-2,aresample=48000[vo];[2:a]volume=-22dB,aresample=48000,atrim=0:{vd},"
        f"afade=t=out:st={vd - 1.2:.2f}:d=1.2[mu];[vo][mu]amix=inputs=2:duration=first:normalize=0,"
        f"aformat=channel_layouts=stereo[a]",
        "-map", "[v]", "-map", "[a]", "-t", vd, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", mixed])
    end = work / "outro.mp4"
    outro(fmt, end)
    final = outdir / f"{NAME}-{fmt}.mp4"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", mixed, "-i", end, "-filter_complex",
        "[0:v]setsar=1[a0];[1:v]setsar=1[b0];[a0][0:a][b0][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final])
    print(f"✅ {final} ({dur(final):.1f} s)")


def load_spec(path: Path) -> None:
    """Une pub = un fichier JSON : name, script, plan [[début, fin|null, [type, valeur]]], outro_title, outro_sub."""
    global SCRIPT, PLAN, OUTRO_TITLE, OUTRO_SUB, NAME
    spec = json.loads(path.read_text(encoding="utf-8"))
    SCRIPT, NAME = spec["script"], spec["name"]
    PLAN = [(a, b, tuple(v)) for a, b, v in spec["plan"]]
    OUTRO_TITLE, OUTRO_SUB = spec.get("outro_title", OUTRO_TITLE), spec.get("outro_sub", OUTRO_SUB)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--spec":
        load_spec(Path(sys.argv[2]))
        del sys.argv[1:3]
    voice, demo, slides, words, outdir = map(Path, sys.argv[1:6])
    outdir.mkdir(parents=True, exist_ok=True)
    for f in (sys.argv[6:] or ["16x9", "9x16"]):
        build(f, voice, demo, slides, words, outdir)
