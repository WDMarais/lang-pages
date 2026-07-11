#!/usr/bin/env python3
"""Project the CN phonetics reference (/zhuyin/) from the symbol store.

Like build-pages, this is a *projection*: the syllable inventory is derived from the
same symbol readings the cards render (via phonetics.bank), so the reference page and
the audio bank stay in lockstep with the substrate — no hand-maintained syllable list.

Writes zhuyin/data.json = { chart, syllables }:
  - chart: the fixed 37-symbol Bopomofo alphabet (initials / medials / finals) with
    pinyin equivalents — the "what are these symbols" reference.
  - syllables: the enumerable bank (phonetics.bank) — every syllable our characters
    actually use, each with pinyin, zhuyin, tone, its representative + sibling hanzi,
    and the audio key the /audio/cn/ bank is filed under.
"""
from paths import ROOT, write_json
from symbols_io import load_symbols
from phonetics import bank

# The Bopomofo alphabet in canonical order, each with its pinyin equivalent. This is
# fixed reference content (the 37 symbols never change), kept here so the page is a
# pure render of generated data. Syllabic-consonant note: ㄓㄔㄕㄖㄗㄘㄙ take no
# vowel symbol when they stand as zhi/chi/shi/ri/zi/ci/si.
CHART = {
    "声母 · initials": [
        ("ㄅ", "b"), ("ㄆ", "p"), ("ㄇ", "m"), ("ㄈ", "f"),
        ("ㄉ", "d"), ("ㄊ", "t"), ("ㄋ", "n"), ("ㄌ", "l"),
        ("ㄍ", "g"), ("ㄎ", "k"), ("ㄏ", "h"),
        ("ㄐ", "j"), ("ㄑ", "q"), ("ㄒ", "x"),
        ("ㄓ", "zh"), ("ㄔ", "ch"), ("ㄕ", "sh"), ("ㄖ", "r"),
        ("ㄗ", "z"), ("ㄘ", "c"), ("ㄙ", "s"),
    ],
    "介母 · medials": [
        ("ㄧ", "i / y"), ("ㄨ", "u / w"), ("ㄩ", "ü / yu"),
    ],
    "韵母 · finals": [
        ("ㄚ", "a"), ("ㄛ", "o"), ("ㄜ", "e"), ("ㄝ", "ê"),
        ("ㄞ", "ai"), ("ㄟ", "ei"), ("ㄠ", "ao"), ("ㄡ", "ou"),
        ("ㄢ", "an"), ("ㄣ", "en"), ("ㄤ", "ang"), ("ㄥ", "eng"), ("ㄦ", "er"),
    ],
}


def main():
    syms = load_symbols()
    inv = bank(syms)
    chart = {group: [{"zhuyin": z, "pinyin": p} for z, p in rows]
             for group, rows in CHART.items()}
    payload = {"chart": chart, "syllables": inv}

    path = ROOT / "zhuyin/data.json"
    path.parent.mkdir(exist_ok=True)
    write_json(path, payload)

    total_hanzi = sum(len(e["glyphs"]) for e in inv.values())
    tones = sorted({e["tone"] for e in inv.values()})
    print(f"{'zhuyin/data.json':24} {len(inv):3} syllables "
          f"({total_hanzi} hanzi, tones {tones})")


if __name__ == "__main__":
    main()
