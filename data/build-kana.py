#!/usr/bin/env python3
"""Emit the kana mora inventory → kana/data.json for the /kana/ bank page.

Unlike the CN syllable bank (a projection of the symbol store), kana is a *fixed*
canonical inventory, so it is constructed here rather than derived from cards — but
still generated, not hand-typed: only hiragana + romaji are written out, and every
katakana is derived by the constant U+0060 offset that separates the two blocks
(あ U+3042 → ア U+30A2, ゃ U+3083 → ャ U+30E3). That keeps the 200-odd glyphs
systematic and typo-free.

Romaji follows Hepburn (shi/chi/tsu/fu/ja/sha…) and doubles as the audio key: the
/audio/kana/<romaji>.mp3 bank is voiced from the kana glyph itself (gen-audio).

The kana bank teaches the *sounds*; it does not assemble words (pitch accent,
rendaku, gemination live at the word level), so JP card audio stays per-item. See
the CN/JP asymmetry note in the audio-slug memory.
"""
from paths import ROOT, write_json

H2K = 0x60  # hiragana → katakana codepoint offset (holds across the whole block)


def kata(hira):
    return "".join(chr(ord(c) + H2K) for c in hira)


def cell(hira, romaji):
    return {"hira": hira, "kata": kata(hira), "romaji": romaji} if hira else None


# ── 五十音 gojūon: the base grid, row by row. None marks the historical gaps
# (ya-row i/e, wa-row i/u/e). Irregular romaji (shi, chi, tsu, fu, wo) are explicit.
GOJUON = [
    [("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o")],
    [("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko")],
    [("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so")],
    [("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to")],
    [("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no")],
    [("は", "ha"), ("ひ", "hi"), ("ふ", "fu"), ("へ", "he"), ("ほ", "ho")],
    [("ま", "ma"), ("み", "mi"), ("む", "mu"), ("め", "me"), ("も", "mo")],
    [("や", "ya"), None, ("ゆ", "yu"), None, ("よ", "yo")],
    [("ら", "ra"), ("り", "ri"), ("る", "ru"), ("れ", "re"), ("ろ", "ro")],
    [("わ", "wa"), None, None, None, ("を", "wo")],
    [("ん", "n"), None, None, None, None],
]

# ── 濁音 dakuten (゛, voiced) and 半濁音 handakuten (゜). ぢ/づ share ji/zu with じ/ず.
DAKUTEN = [
    [("が", "ga"), ("ぎ", "gi"), ("ぐ", "gu"), ("げ", "ge"), ("ご", "go")],
    [("ざ", "za"), ("じ", "ji"), ("ず", "zu"), ("ぜ", "ze"), ("ぞ", "zo")],
    [("だ", "da"), ("ぢ", "ji"), ("づ", "zu"), ("で", "de"), ("ど", "do")],
    [("ば", "ba"), ("び", "bi"), ("ぶ", "bu"), ("べ", "be"), ("ぼ", "bo")],
]
HANDAKUTEN = [
    [("ぱ", "pa"), ("ぴ", "pi"), ("ぷ", "pu"), ("ぺ", "pe"), ("ぽ", "po")],
]

# ── 拗音 yōon: base i-column kana + small ゃ/ゅ/ょ. じゃ/ぢゃ collapse to ja/ju/jo,
# し/ち/じ drop the 'y' (sha not sya). Written as (base_i_kana, [(small, romaji)…]).
YOON = [
    ("き", [("ゃ", "kya"), ("ゅ", "kyu"), ("ょ", "kyo")]),
    ("し", [("ゃ", "sha"), ("ゅ", "shu"), ("ょ", "sho")]),
    ("ち", [("ゃ", "cha"), ("ゅ", "chu"), ("ょ", "cho")]),
    ("に", [("ゃ", "nya"), ("ゅ", "nyu"), ("ょ", "nyo")]),
    ("ひ", [("ゃ", "hya"), ("ゅ", "hyu"), ("ょ", "hyo")]),
    ("み", [("ゃ", "mya"), ("ゅ", "myu"), ("ょ", "myo")]),
    ("り", [("ゃ", "rya"), ("ゅ", "ryu"), ("ょ", "ryo")]),
    ("ぎ", [("ゃ", "gya"), ("ゅ", "gyu"), ("ょ", "gyo")]),
    ("じ", [("ゃ", "ja"), ("ゅ", "ju"), ("ょ", "jo")]),
    ("び", [("ゃ", "bya"), ("ゅ", "byu"), ("ょ", "byo")]),
    ("ぴ", [("ゃ", "pya"), ("ゅ", "pyu"), ("ょ", "pyo")]),
]


def grid(rows):
    return [[cell(*c) if c else None for c in row] for row in rows]


def yoon_rows():
    rows = []
    for base, combos in YOON:
        rows.append([cell(base + small, romaji) for small, romaji in combos])
    return rows


def main():
    payload = {
        "gojuon": grid(GOJUON),
        "dakuten": grid(DAKUTEN),
        "handakuten": grid(HANDAKUTEN),
        "yoon": yoon_rows(),
    }
    write_json(ROOT / "kana/data.json", payload)
    n = sum(1 for sec in payload.values() for row in sec for c in row if c)
    print(f"{'kana/data.json':24} {n:3} mora "
          f"(gojūon {sum(1 for r in payload['gojuon'] for c in r if c)}, "
          f"dakuten {sum(1 for r in payload['dakuten'] for c in r if c)}, "
          f"handakuten {sum(1 for r in payload['handakuten'] for c in r if c)}, "
          f"yōon {sum(1 for r in payload['yoon'] for c in r if c)})")


if __name__ == "__main__":
    main()
