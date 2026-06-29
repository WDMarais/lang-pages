#!/usr/bin/env python3
"""Fetch / lift HanziWriter stroke data into this directory.

Self-hosting helper for the stroke-order animation (see ./LICENSE.md for
provenance). Two modes:

  Download whole characters (data is already centred by Make-Me-a-Hanzi):
      python3 fetch.py 九 十 川 工 山 木 日

  Lift one or more strokes out of a source character and recentre them to the
  tile centre — for stroke-block / katakana glyphs that aren't in the dataset
  (e.g. ㇏ ㇀ 𠂉 ト). Indices are 0-based, in writing order:
      python3 fetch.py --lift 午:0,1 --as 𠂉
      python3 fetch.py --lift 卜:0,1 --as ト

Source data is pulled from the hanzi-writer-data CDN. Output goes to the
directory this script lives in, one <glyph>.json per character.
"""
import json, re, sys, urllib.parse, urllib.request
from pathlib import Path

CDN = "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2/{}.json"
BOX = 1024          # Make-Me-a-Hanzi coordinate box
CENTER = BOX // 2   # 512
HERE = Path(__file__).resolve().parent
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def fetch(char):
    """Download raw {strokes, medians} for a character from the CDN."""
    url = CDN.format(urllib.parse.quote(char))
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def coords(path):
    """Flat list of numbers in a path. MMAH paths use only absolute M/L/Q/C/Z,
    so the numbers strictly alternate x, y across the whole string."""
    return [float(x) for x in NUM.findall(path)]


def translate_path(path, dx, dy):
    i = [0]
    def repl(m):
        k = i[0]; i[0] += 1
        v = float(m.group()) + (dx if k % 2 == 0 else dy)
        return str(int(round(v)))
    return NUM.sub(repl, path)


def lift(char, idxs):
    """Lift strokes[idxs] + medians[idxs] from char, recentre the group to
    (512, 512), return a one-or-more-stroke {strokes, medians} dict."""
    d = fetch(char)
    strokes = [d["strokes"][i] for i in idxs]
    medians = [d["medians"][i] for i in idxs]
    xs, ys = [], []
    for p in strokes:
        c = coords(p); xs += c[0::2]; ys += c[1::2]
    dx = CENTER - (min(xs) + max(xs)) / 2
    dy = CENTER - (min(ys) + max(ys)) / 2
    return {
        "strokes": [translate_path(p, dx, dy) for p in strokes],
        "medians": [[[int(round(x + dx)), int(round(y + dy))] for x, y in m]
                    for m in medians],
    }


def write(glyph, data):
    out = HERE / f"{glyph}.json"
    out.write_text(json.dumps(data, ensure_ascii=False))
    print(f"wrote {out.name}  ({len(data['strokes'])} stroke(s))")


def main(argv):
    if not argv:
        print(__doc__); return 1
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--lift":
            src, _, idxspec = argv[i + 1].partition(":")
            idxs = [int(x) for x in idxspec.split(",")]
            assert argv[i + 2] == "--as", "expected --as <glyph> after --lift"
            write(argv[i + 3], lift(src, idxs))
            i += 4
        else:
            write(a, fetch(a))
            i += 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
