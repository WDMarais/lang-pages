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
import json, sys, urllib.request  # json: MMAH ships JSONL text lines, parsed inline

from paths import ROOT, DATA, write_json
from symbols_io import load_symbols
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
# to MMAH's '？'. ト follows its 卜 origin: 丨 (竖) + 丶 (点).
#
# Also hand-fix two more MMAH quirks: 白 arrives as ⿻？日 (its top stroke is
# below MMAH's floor) → 丿 + 日; and 線 arrives as ⿰糹泉 with the radical-variant
# codepoint 糹 (U+7CF9) → fold to the standalone thread char 糸 (U+7CF8) we card.
STROKE_OVERRIDE = {
    "八": ["丿", "㇏"],
    "人": ["丿", "㇏"],
    "入": ["丿", "㇏"],
    "𠂉": ["丿", "一"],
    "力": ["㇆", "丿"],
    "勹": ["丿", "㇆"],
    "女": ["㇛", "丿", "一"],
    "ト": ["丨", "丶"],
    "白": ["丿", "日"],
    "線": ["糸", "泉"],
    "丆": ["一", "丿"],  # WK "Leaf" — not in MMAH; 横 + 撇
    "合": ["人", "一", "口"],  # MMAH gives 亼 口; 亼 (人+一) not carded → its carded parts
    # The 𠂇-topped family: MMAH truncates the 𠂇 away and returns only the lower
    # part (as it does for 友, which keeps 𠂇 solely via that card's appearsIn).
    # Restoring it is what makes 左/右 a visible minimal pair — same hand, 工 vs 口.
    "右": ["𠂇", "口"],
    "左": ["𠂇", "工"],
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
    """Every carded glyph plus the example chars it cites — read straight from
    the symbol source of truth, not the projected page files. Reading the pages
    was both circular (build-pages writes them, but a new glyph needs its decomp
    *before* it can be paged) and stale (it named the retired radicals/radicals.json)."""
    glyphs = set()
    for sym in load_symbols().values():
        glyphs.add(sym["glyph"])
        for v in (sym["readings"]["cn"], sym["readings"]["jp"]):
            ai = v.get("appearsIn")
            if ai:
                glyphs.add(ai["char"])
    return glyphs


def compute_decomp(refresh=False):
    """Build the decomposition map from the (cached) MMAH dictionary + the
    STROKE_OVERRIDE floor, for the current symbol set. Pure — returns the dict,
    writes nothing. check-source.py calls this to prove decomposition.json is
    fresh (a symbol added without re-running this = an under-integrated glyph)."""
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
    return decomp


def main(argv):
    decomp = compute_decomp(refresh="--refresh" in argv)
    DATA.mkdir(exist_ok=True)
    write_json(DATA / "decomposition.json", decomp)
    print(f"decomposition for {len(decomp)}/{len(needed_glyphs())} glyphs")
    for k in list(decomp)[:10]:
        print(f"  {k} ← {' '.join(decomp[k])}")


if __name__ == "__main__":
    main(sys.argv[1:])
