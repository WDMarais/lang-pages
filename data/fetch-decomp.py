#!/usr/bin/env python3
"""Fetch character decomposition (IDS) from Make-Me-a-Hanzi and emit
data/decomposition.json for the glyphs in our graph.

Adds the structural 'parts' the card JSON lacks: 男 ← 田 力, 好 ← 女 子, 林 ← 木.
One level per character (immediate components). build-graph.py turns these into
`composes` edges (new components become frontier nodes).

Run: python3 data/fetch-decomp.py
"""
import json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DICT_URL = "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt"
IDC = set(range(0x2FF0, 0x2FFC))  # ideographic description chars ⿰ ⿱ … ⿻


def is_component(ch):
    return ord(ch) not in IDC and ch not in "？ \t\n"


def needed_glyphs():
    """The glyphs we card (radicals + strokes) plus the example chars they cite."""
    glyphs = set()
    for f in ("radicals/radicals.json", "strokes/strokes.json"):
        d = json.loads((ROOT / f).read_text())
        for grp in d["groups"]:
            for c in grp["cards"]:
                glyphs.add(c["glyph"])
                for v in (c["cn"], c["jp"]):
                    if v.get("ex"):
                        glyphs.add(v["ex"]["char"])
    return glyphs


def main():
    want = needed_glyphs()
    decomp = {}
    with urllib.request.urlopen(DICT_URL) as r:
        for line in r:
            e = json.loads(line)
            ch = e["character"]
            if ch in want and e.get("decomposition"):
                comps = [c for c in e["decomposition"] if is_component(c) and c != ch]
                if comps:
                    decomp[ch] = comps
    DATA.mkdir(exist_ok=True)
    (DATA / "decomposition.json").write_text(
        json.dumps(decomp, ensure_ascii=False, indent=2) + "\n")
    print(f"decomposition for {len(decomp)}/{len(want)} glyphs")
    for k in list(decomp)[:10]:
        print(f"  {k} ← {' '.join(decomp[k])}")


if __name__ == "__main__":
    main()
