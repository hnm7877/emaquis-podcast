#!/usr/bin/env python3
"""Fin de chaque Short : jingle E-Maquis (mascotte) + carte « Télécharge E-Maquis Pro » + site web.

    python outro.py build                 # fabrique assets/outro-9x16.mp4 (une fois)
    python outro.py append <short.mp4>    # colle la fin au Short (remplace le fichier)

La carte verticale 1080x1920 : fond orange E-Maquis animé (le jingle flouté), le jingle net au centre,
bandeau « LA MINUTE E-MAQUIS » en haut, puis « Télécharge E-Maquis Pro », les stores et www.e-maquis.com
qui apparaissent l'un après l'autre. Son du jingle mis au même niveau que le Short (-14 LUFS).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JINGLE = ROOT / "assets" / "jingle-emaquis.mp4"
OUTRO = ROOT / "assets" / "outro-9x16.mp4"
FONTS = ROOT / ".claude" / "skills" / "short-editing" / "engine" / "fonts"
BLACK = FONTS / "ArchivoBlack.ttf"
SEMI = FONTS / "Poppins-SemiBold.ttf"
ORANGE = "0xE8701A"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def duration(path: Path) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]))


def text(t: str, font: Path, size: int, y: str, start: float, color: str = "white", box: str = "") -> str:
    """Texte centré qui apparaît en fondu à `start` s."""
    t = t.replace(":", r"\:").replace("'", "’")
    alpha = f"if(lt(t,{start}),0,min(1,(t-{start})/0.35))"
    extra = f":box=1:boxcolor={box}:boxborderw=26" if box else ""
    return (f"drawtext=fontfile={font}:text='{t}':fontsize={size}:fontcolor={color}:"
            f"x=(w-text_w)/2:y={y}:alpha='{alpha}'{extra}")


def build() -> Path:
    d = duration(JINGLE)
    vf = ";".join([
        # fond : le jingle agrandi, flouté et teinté orange
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:4,"
        f"eq=brightness=-0.08:saturation=1.3,"
        f"drawbox=x=0:y=0:w=iw:h=ih:color={ORANGE}@0.55:t=fill[bg]",
        # le jingle net au centre, dans un cadre blanc arrondi façon carte
        "[0:v]scale=1000:-2,pad=iw+24:ih+24:12:12:white[card]",
        "[bg][card]overlay=(W-w)/2:560[v1]",
        "[v1]" + ",".join([
            text("LA MINUTE E-MAQUIS", BLACK, 62, "250", 0.0, color="white", box="0x1F1A17@0.92"),
            text("Télécharge", SEMI, 74, "1235", 0.6),
            text("E-MAQUIS PRO", BLACK, 108, "1325", 0.9),
            text("Google Play  •  App Store", SEMI, 54, "1490", 1.6, color="0x1F1A17", box="white@0.95"),
            text("www.e-maquis.com", BLACK, 72, "1640", 2.3),
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={d - 0.4:.2f}:d=0.4",
        ]) + "[v]",
    ])
    af = f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,afade=t=out:st={d - 0.5:.2f}:d=0.5"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(JINGLE), "-filter_complex", vf, "-map", "[v]",
         "-map", "0:a", "-af", af, "-r", "30", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(OUTRO)])
    return OUTRO


def append(short: Path) -> Path:
    if not OUTRO.exists():  # la carte est versionnée (le ffmpeg de GitHub n'a pas drawtext)
        build()
    out = short.with_name(short.stem + "-fin.mp4")
    fc = ("[0:v]fps=30,scale=1080:1920,setsar=1,format=yuv420p[a];"
          "[1:v]fps=30,scale=1080:1920,setsar=1,format=yuv420p[b];"
          "[0:a]aresample=48000,aformat=channel_layouts=stereo[x];"
          "[1:a]aresample=48000,aformat=channel_layouts=stereo[y];"
          "[a][x][b][y]concat=n=2:v=1:a=1[v][au]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(short), "-i", str(OUTRO), "-filter_complex", fc,
         "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    out.replace(short)
    print(f"[fin] jingle ajouté : {short} ({duration(short):.1f} s)")
    return short


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        print(build())
    elif sys.argv[1:2] == ["append"]:
        append(Path(sys.argv[2]))
    else:
        sys.exit(__doc__)
