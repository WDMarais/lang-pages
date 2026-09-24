#!/usr/bin/env python3
"""Render stroke data in this directory to a picture, for eyeballing.

The stroke JSON is the one thing here you cannot review by reading it — an
`assemble.py` placement or a `composes` claim about which component a glyph
actually draws is a question about shapes. This answers it:

    python3 render.py out.svg 全 入 𠆢 人      # SVG strip, one cell per glyph
    python3 render.py out.png 全 入 𠆢 人      # same, rasterised via rsvg-convert

Each cell draws the glyph with its first two strokes coloured and a dot where
each of those strokes BEGINS, because that is what separates the lookalike tops:
入's ㇏ starts above the 丿 and crosses the apex, 人's and 𠆢's start below it.
The same numbers print to stdout, so a claim can be checked without opening the
file — this is how 全 was shown to draw 𠆢, not 入, against every radical index.

Reads <glyph>.json from the directory this script lives in (fetch.py / assemble.py
put them there). `--strokes N` colours the first N instead of two.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELL, PAD = 260, 14
# Distinct hues for the strokes under inspection; everything else stays grey so the
# coloured ones read as "the part being argued about".
HUES = ["#e5484d", "#ffb224", "#8e4ec6", "#0090ff", "#4cc38a"]
REST, DOT, BG, TILE, GRID, TEXT = "#5b626e", "#4cc38a", "#14161a", "#0f1114", "#2c313a", "#e8e6e3"


def load(glyph):
    path = HERE / f"{glyph}.json"
    if not path.exists():
        sys.exit(f"no stroke data for {glyph} — fetch.py or assemble.py it first "
                 f"({path.relative_to(HERE.parent.parent)})")
    return json.loads(path.read_text(encoding="utf-8"))


def cell(glyph, data, ox, lit):
    s = CELL / 1024
    out = [f'<g transform="translate({ox},0)">',
           f'<rect width="{CELL}" height="{CELL}" fill="{TILE}" rx="8"/>',
           f'<line x1="{CELL / 2}" y1="0" x2="{CELL / 2}" y2="{CELL}" stroke="{GRID}" stroke-dasharray="4 6"/>',
           f'<line x1="0" y1="{CELL / 2}" x2="{CELL}" y2="{CELL / 2}" stroke="{GRID}" stroke-dasharray="4 6"/>',
           # HanziWriter's em box is 1024 units with y pointing UP — the same transform
           # assemble.py writes, so what this draws is what the animation draws.
           f'<g transform="scale({s}) translate(0,900) scale(1,-1)">']
    for i, path in enumerate(data["strokes"]):
        out.append(f'<path d="{path}" fill="{HUES[i] if i < lit else REST}"/>')
    for median in data["medians"][:lit]:
        out.append(f'<circle cx="{median[0][0]}" cy="{median[0][1]}" r="30" fill="{DOT}"/>')
    out.append("</g>")
    out.append(f'<text x="{CELL / 2}" y="{CELL - 10}" fill="{TEXT}" font-size="20" '
               f'font-family="sans-serif" text-anchor="middle">{glyph}</text>')
    out.append("</g>")
    return "\n".join(out)


def starts(data, lit):
    """Where each inspected stroke begins, and stroke 2's offset from stroke 1.

    dy > 0 means stroke 2 starts BELOW stroke 1 in writing space (y points up), which
    is the 人/𠆢 profile; dy < 0 is 入's, whose falling stroke starts over the apex."""
    pts = [m[0] for m in data["medians"][:lit]]
    if len(pts) < 2:
        return pts, None, None
    return pts, pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]


def main(argv):
    lit = 2
    if "--strokes" in argv:
        i = argv.index("--strokes")
        lit = int(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) < 2:
        sys.exit(__doc__.strip().splitlines()[0] + "\n\n  render.py OUT.svg|OUT.png <glyph>…")

    out, glyphs = Path(argv[0]), argv[1:]
    loaded = [(g, load(g)) for g in glyphs]

    width = len(glyphs) * (CELL + PAD) + PAD
    height = CELL + 2 * PAD
    body = "\n".join(cell(g, d, PAD + i * (CELL + PAD), lit)
                     for i, (g, d) in enumerate(loaded))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">'
           f'<rect width="{width}" height="{height}" fill="{BG}"/>'
           f'<g transform="translate(0,{PAD})">{body}</g></svg>')

    if out.suffix.lower() == ".png":
        if not shutil.which("rsvg-convert"):
            sys.exit("rsvg-convert not found (apt install librsvg2-bin), "
                     "or write a .svg instead")
        subprocess.run(["rsvg-convert", "-w", str(width * 2), "-o", str(out)],
                       input=svg.encode("utf-8"), check=True)
    else:
        out.write_text(svg, encoding="utf-8")
    print(f"wrote {out}")

    print(f"\nfirst {lit} stroke start(s), in em-box units (y points UP):")
    for g, d in loaded:
        pts, dx, dy = starts(d, lit)
        where = "" if dy is None else \
            f"   stroke 2 starts {'ABOVE' if dy < 0 else 'below'} stroke 1 " \
            f"by {abs(dy)} (dx {abs(dx)})"
        print(f"  {g}  {' '.join(f'({int(x)},{int(y)})' for x, y in pts)}{where}")


if __name__ == "__main__":
    main(sys.argv[1:])
