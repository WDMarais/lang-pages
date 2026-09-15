#!/usr/bin/env python3
"""Assemble a glyph's HanziWriter stroke data by lifting + placing its parts.

For glyphs the upstream CDN lacks (JP shinjitai, home-grown components) but
whose *parts* are already present as hanzi-data, we can synthesise the whole:
take each part's strokes + medians, apply a uniform affine (scale s, translate
tx,ty) in the shared 1024-em coordinate box, and concatenate in stroke order.

The em box has y pointing UP (dot ~y800 top, baseline ~y0 bottom, values may go
slightly negative). A part placed with s<1 shrinks toward the origin, so tx/ty
then slide it into position. Tune s/tx/ty against a reference glyph; `--preview`
writes an SVG you can open in a browser.

Usage:
    assemble.py <target> <part>[:<i>,<j>…]@<s>,<tx>,<ty> [...]
    assemble.py 広 广@1,0,0 厶@0.68,250,32
    assemble.py 氷 水:0@1,0,0 丶@0.55,-33,352 水:1,2,3@1,0,0
    assemble.py 広 ... --preview     # also write <target>.preview.svg, don't touch data

Parts are concatenated in the order given — that IS the stroke (animation) order.
An optional `:<i>,<j>…` selector takes only those strokes (0-based) of a part, so
a stroke can be slotted between another part's strokes (氷: the dot is stroke 2).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def transform_path(path, s, tx, ty):
    """Apply x'=s*x+tx, y'=s*y+ty to every coordinate in an SVG path string.
    Safe because these paths use only M/L/Q/C/Z — all absolute, all whole
    (x,y) coordinate pairs (Z carries none), so numeric tokens pair up 1:1."""
    nums = NUM.findall(path)
    if len(nums) % 2:
        raise ValueError(f"odd coordinate count in path: {path[:40]}…")
    out = []
    for i in range(0, len(nums), 2):
        x = float(nums[i]) * s + tx
        y = float(nums[i + 1]) * s + ty
        out.append((_fmt(x), _fmt(y)))
    it = iter(out)
    # Re-emit the path, swapping each numeric token for its transformed value
    # while leaving command letters and separators exactly as they were.
    coords = [c for pair in it for c in pair]
    k = [0]

    def repl(_m):
        v = coords[k[0]]
        k[0] += 1
        return v

    return NUM.sub(repl, path)


def transform_medians(medians, s, tx, ty):
    return [[[_round(px * s + tx), _round(py * s + ty)] for px, py in stroke]
            for stroke in medians]


def _fmt(v):
    r = round(v, 2)
    return str(int(r)) if r == int(r) else str(r)


def _round(v):
    r = round(v)
    return int(r)


def load_part(glyph):
    p = HERE / f"{glyph}.json"
    if not p.exists():
        sys.exit(f"missing part data: {p.relative_to(HERE.parent.parent)} "
                 f"— fetch or assemble {glyph} first")
    return json.loads(p.read_text())


def assemble(specs):
    strokes, medians = [], []
    for glyph, idx, s, tx, ty in specs:
        d = load_part(glyph)
        keep = range(len(d["strokes"])) if idx is None else idx
        for i in keep:
            if not 0 <= i < len(d["strokes"]):
                sys.exit(f"{glyph} has {len(d['strokes'])} stroke(s); no stroke {i}")
        strokes += [transform_path(d["strokes"][i], s, tx, ty) for i in keep]
        medians += transform_medians([d["medians"][i] for i in keep], s, tx, ty)
    return {"strokes": strokes, "medians": medians}


def preview_svg(data):
    """makemeahanzi render transform: viewBox 0 0 1024 1024, y-up flipped via
    translate(0,900) scale(1,-1). Fill each stroke so the shape is legible."""
    paths = "\n".join(
        f'    <path d="{s}"/>' for s in data["strokes"])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" '
        'width="256" height="256">\n'
        '  <g transform="translate(0,900) scale(1,-1)" '
        'fill="#111" stroke="none">\n'
        f'{paths}\n'
        '  </g>\n'
        '</svg>\n')


def parse_spec(tok):
    part, _, rest = tok.partition("@")
    usage = f"bad spec {tok!r} — expected <part>[:<i>,<j>…]@<s>,<tx>,<ty>"
    if not rest:
        sys.exit(usage)
    glyph, _, sel = part.partition(":")
    try:
        s, tx, ty = (float(x) for x in rest.split(","))
        idx = [int(i) for i in sel.split(",")] if sel else None
    except ValueError:
        sys.exit(usage)
    return (glyph, idx, s, tx, ty)


def _spec_str(glyph, idx, s, tx, ty):
    sel = f":{','.join(map(str, idx))}" if idx is not None else ""
    return f"{glyph}{sel}@{s},{tx},{ty}"


def main(argv):
    preview = "--preview" in argv
    argv = [a for a in argv if a != "--preview"]
    if len(argv) < 2:
        sys.exit(__doc__)
    target, spec_toks = argv[0], argv[1:]
    specs = [parse_spec(t) for t in spec_toks]
    data = assemble(specs)

    if preview:
        out = HERE / f"{target}.preview.svg"
        out.write_text(preview_svg(data))
        print(f"wrote {out.name}  ({len(data['strokes'])} stroke(s)) — preview only")
        return 0

    out = HERE / f"{target}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    parts = " + ".join(_spec_str(*spec) for spec in specs)
    print(f"wrote {out.name}  ({len(data['strokes'])} stroke(s))  ← {parts}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
