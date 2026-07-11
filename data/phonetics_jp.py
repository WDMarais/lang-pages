#!/usr/bin/env python3
"""JP phonetic normalization — the sibling of phonetics.py (CN), and the floor under
the /audio/jp/ reading bank.

The CN reconcile decoupled audio from the card slug: a syllable is keyed by its
*sound* (千 → qian1) and voiced once, so every glyph reading it shares one clip.
This module does the same for JP. A glyph's JP reading is katakana/hiragana (千 →
セン, 月 → つき) — always a single, directly speakable unit (unlike a whole CN
stroke-name), so it banks cleanly by a romaji key:

  kana_key("セン") → "sen"   kana_key("つき") → "tsuki"   kana_key("キュウ") → "kyuu"

Romaji follows the same Hepburn table build-kana.py uses for the /kana/ board
(shi/chi/tsu/fu/ja/sha), so the two romanizations never diverge. Keys are ASCII
[a-z]+ and filename-safe. Readingless components (亻 乚 𠂇 ナ メ) have no reading →
None → no key → no clip (cards3.js already gates the play button on a reading).

This module is the JP sound floor only. The CN companions (multi_key/cn_key) live
in phonetics.py; the card-level stamp that bridges both (card_audio_keys) lives in
symbols_io.py with the other projection helpers.
"""

H2K = 0x60  # hiragana → katakana codepoint offset (see build-kana.py)

# ── kana → romaji (Hepburn), mirroring build-kana.py's tables ──────────────────
# Base gojūon + dakuten + handakuten, then the yōon two-kana combos. Keyed in
# hiragana; katakana is folded to hiragana before lookup. ん/ぢ/づ handled here too.
_MORA = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "wo", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    # yōon: base i-column kana + small ゃ/ゅ/ょ (し/ち/じ drop the y: sha not sya)
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
}
_SOKUON = {"っ"}          # gemination: doubles the next mora's leading consonant
_CHOON = {"ー"}           # katakana long-vowel bar: repeats the previous vowel


def _to_hira(reading):
    """Fold katakana onto hiragana so one table serves both. Non-kana (ー, already-
    hiragana) pass through: ー (U+30FC) sits above the katakana block so it is left
    intact and handled as a long-vowel mark."""
    out = []
    for ch in reading:
        o = ord(ch)
        out.append(chr(o - H2K) if 0x30A1 <= o <= 0x30F6 else ch)
    return "".join(out)


def kana_key(reading):
    """Kana reading → romaji bank key, or None if it isn't pure kana.

    'セン' → 'sen', 'つき' → 'tsuki', 'キュウ' → 'kyuu', 'ショウ' → 'shou',
    'みっつ' → 'mittsu'. Empty/None → None (readingless component → no clip)."""
    if not reading:
        return None
    s = _to_hira(reading)
    out, i, gem = [], 0, False
    while i < len(s):
        ch, nxt = s[i], s[i + 1] if i + 1 < len(s) else ""
        if ch in _SOKUON:
            gem = True
            i += 1
            continue
        if ch in _CHOON:
            if out and out[-1] and out[-1][-1] in "aeiou":
                out.append(out[-1][-1])
            i += 1
            continue
        if ch + nxt in _MORA:          # yōon: consume the small-kana pair
            r, i = _MORA[ch + nxt], i + 2
        elif ch in _MORA:
            r, i = _MORA[ch], i + 1
        else:
            return None                # not pure kana — no bank key
        out.append(r[0] + r if gem else r)
        gem = False
    if gem:                            # dangling っ — malformed
        return None
    key = "".join(out)
    return key if key and key.isascii() and key.isalpha() else None


def _selftest():
    """Romanize every live JP reading (glyph + example) and report keys, homophone
    merges, and any reading that fails to romanize (would signal a table gap)."""
    import sys
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from symbols_io import load_symbols

    keyed, failed = {}, []
    for s in load_symbols().values():
        jp = (s.get("readings") or {}).get("jp") or {}
        for src in (jp.get("reading"), (jp.get("appearsIn") or {}).get("reading")):
            if not src:
                continue
            k = kana_key(src)
            if k is None:
                failed.append(src)
            else:
                keyed.setdefault(k, set()).add(src)

    print(f"JP readings → {len(keyed)} unique romaji keys")
    merges = {k: v for k, v in keyed.items() if len(v) > 1}
    print(f"homophone/script merges (share one clip): {len(merges)}")
    for k, v in sorted(merges.items()):
        print(f"  {k}: {' '.join(sorted(v))}")
    if failed:
        print(f"\n✗ failed to romanize ({len(failed)}): {' '.join(failed)}")
    else:
        print("\n✓ every JP reading romanized")
    for k in sorted(keyed)[:16]:
        print(f"  {k}  ← {' '.join(sorted(keyed[k]))}")


if __name__ == "__main__":
    _selftest()
