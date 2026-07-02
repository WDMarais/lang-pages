#!/usr/bin/env python3
"""Fetch character decomposition (IDS) from Make-Me-a-Hanzi and emit
data/decomposition.json for the glyphs in our graph.

Adds the structural 'parts' the card JSON lacks: 男 ← 田 力, 好 ← 女 子, 林 ← 木.
One level per character (immediate components). build-graph.py turns these into
`composes` edges (new components become frontier nodes).

The MMAH dictionary (several MB) is cached under data/.cache after the first
pull, so adding one glyph doesn't re-download the whole thing. It rarely
changes; pass --refresh to force a fresh download.

Run: python3 data/fetch-decomp.py [--refresh]
"""
import json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DICT_URL = "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt"
CACHE = DATA / ".cache" / "makemeahanzi-dictionary.txt"
IDC = set(range(0x2FF0, 0x2FFC))  # ideographic description chars ⿰ ⿱ … ⿻

# MMAH's decomposition floor is the RADICAL, not the stroke: it marks
# stroke-atomic glyphs (八, 人, 入) and sub-parts it can't name with '？', so
# they arrive with no usable components. Our graph has a stroke tier BELOW that
# floor, so we hand-author those stroke parts here. 八's own card already says
# 撇+捺 — that's 丿+㇏; MMAH simply can't see it.
#
# Seeded with stroke-level decompositions MMAH leaves atomic. The compound
# strokes 横折钩 (㇆) and 撇点 (㇛) are now carded (strokes.json), lifted from
# 力 / 女 — so 力/勹/女 resolve to real stroke nodes rather than losing a stroke
# to MMAH's '？'. ト follows its 卜 origin as 丿 + 丶 (the katakana-slant call).
STROKE_OVERRIDE = {
    "八": ["丿", "㇏"],
    "人": ["丿", "㇏"],
    "入": ["丿", "㇏"],
    "𠂉": ["丿", "一"],
    "力": ["㇆", "丿"],
    "勹": ["丿", "㇆"],
    "女": ["㇛", "丿", "一"],
    "ト": ["丿", "丶"],
}


def dictionary_lines(refresh=False):
    """The MMAH dictionary as text lines, cached locally so repeat runs (e.g.
    adding one card) reuse the download instead of re-pulling several MB."""
    if refresh or not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(DICT_URL) as r:
            CACHE.write_bytes(r.read())
        print(f"downloaded dictionary → {CACHE.relative_to(ROOT)}")
    else:
        print(f"using cached dictionary  {CACHE.relative_to(ROOT)}")
    return CACHE.read_text(encoding="utf-8").splitlines()


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
                    if v.get("appearsIn"):
                        glyphs.add(v["appearsIn"]["char"])
    return glyphs


def main(argv):
    refresh = "--refresh" in argv
    want = needed_glyphs()
    decomp = {}
    for line in dictionary_lines(refresh):
        if not line.strip():
            continue
        e = json.loads(line)
        ch = e["character"]
        if ch in want and e.get("decomposition"):
            comps = [c for c in e["decomposition"] if is_component(c) and c != ch]
            if comps:
                decomp[ch] = comps
    # hand-authored stroke parts below MMAH's radical floor (override any
    # partial MMAH result — 力's '？'-truncated [丿] would otherwise stand).
    for ch, comps in STROKE_OVERRIDE.items():
        if ch in want:
            decomp[ch] = comps
    DATA.mkdir(exist_ok=True)
    (DATA / "decomposition.json").write_text(
        json.dumps(decomp, ensure_ascii=False, indent=2) + "\n")
    print(f"decomposition for {len(decomp)}/{len(want)} glyphs")
    for k in list(decomp)[:10]:
        print(f"  {k} ← {' '.join(decomp[k])}")


if __name__ == "__main__":
    main(sys.argv[1:])
