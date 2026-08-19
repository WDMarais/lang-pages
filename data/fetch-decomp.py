#!/usr/bin/env python3
"""Suggest a glyph's immediate components (IDS) from Make-Me-a-Hanzi.

An AUTHORING AID, not a build step. The graph's composition edges come from each
symbol's authored `composes` field (data/symbols/<glyph>.json) — the glyph-level
source of truth, read directly by build-graph.py. This tool only helps you FILL
that field for a new glyph: it prints MMAH's one-level decomposition so you can
paste/adjust it into `composes`. MMAH's floor is the radical, so stroke-level
parts and JP shinjitai (absent from MMAH) come back partial or empty — the human
`composes` is authoritative and refines by hand (合 ← 𠆢 一 口, 広 ← 广 厶).

    python3 data/fetch-decomp.py 男 好 林       # suggest parts for these glyphs
    python3 data/fetch-decomp.py --refresh 男   # re-pull the MMAH dictionary first

Prints JSON {glyph: [parts]} to stdout (scaffold.py consumes it); status notes go
to stderr. The MMAH dictionary (several MB) is cached under data/.cache.
"""
import json, sys, urllib.request  # json: MMAH ships JSONL text lines, parsed inline

from paths import ROOT, DATA

DICT_URL = "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt"
CACHE = DATA / ".cache" / "makemeahanzi-dictionary.txt"
IDC = set(range(0x2FF0, 0x2FFC))  # ideographic description chars ⿰ ⿱ … ⿻


def dictionary_lines(refresh=False):
    """The MMAH dictionary as text lines, cached locally so repeat runs reuse the
    download instead of re-pulling several MB."""
    if refresh or not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(DICT_URL) as r:
            CACHE.write_bytes(r.read())
        print(f"downloaded dictionary → {CACHE.relative_to(ROOT)}", file=sys.stderr)
    else:
        print(f"using cached dictionary  {CACHE.relative_to(ROOT)}", file=sys.stderr)
    return CACHE.read_text(encoding="utf-8").splitlines()


def is_component(ch):
    return ord(ch) not in IDC and ch not in "？ \t\n"


def suggest(glyphs, refresh=False):
    """MMAH's immediate (one-level) components for each requested glyph, as
    {glyph: [parts]}. A glyph MMAH can't decompose (stroke-atomic, or absent like
    JP shinjitai) maps to [] — refine by hand into the symbol's `composes`."""
    want = set(glyphs)
    out = {g: [] for g in want}
    for line in dictionary_lines(refresh):
        if not line.strip():
            continue
        e = json.loads(line)
        ch = e.get("character")
        if ch in want and e.get("decomposition"):
            out[ch] = [c for c in e["decomposition"] if is_component(c) and c != ch]
    return out


def main(argv):
    refresh = "--refresh" in argv
    glyphs = [a for a in argv if not a.startswith("--")]
    if not glyphs:
        print(__doc__)
        return 0
    print(json.dumps(suggest(glyphs, refresh), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
