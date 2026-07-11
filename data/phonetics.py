#!/usr/bin/env python3
"""CN phonetic normalization — the shared floor under the syllable audio bank,
the tones/zhuyin reference page, and the CN audio reconcile.

Readings in the symbol store are tone-marked pinyin (千 → "qiān", 女 → "nǚ"). Two
consumers need to turn that into a *content key* decoupled from the hanzi:
  - gen-audio: one clip per syllable (cn/qian1.mp3), synthesized once from a
    representative hanzi, instead of one clip per card slug.
  - build-pages: stamp each CN card with its audio key so cards3.js resolves the
    bank path with no normalization logic of its own.

The single source of that normalization is `audio_key(reading)`. It returns None for
anything that is not exactly one syllable — multi-syllable stroke names ("héngzhégōu",
"piědiǎn", "shùgōu") are the CN analog of JP whole-word clips and stay per-item.

Keys are ASCII: the ü umlaut becomes 'v' (nǚ → "nv3"), tone is a trailing digit
1–4, neutral tone is 5. So a key is /^[a-z]+[1-5]$/ and is filename-safe.
"""

# Each tone-marked vowel → (plain letter, tone number). ü and its accents map to the
# ASCII 'v' used in keys/filenames; the reference page can still render 'ü'.
_TONE_VOWELS = {
    "ā": ("a", 1), "á": ("a", 2), "ǎ": ("a", 3), "à": ("a", 4),
    "ē": ("e", 1), "é": ("e", 2), "ě": ("e", 3), "è": ("e", 4),
    "ī": ("i", 1), "í": ("i", 2), "ǐ": ("i", 3), "ì": ("i", 4),
    "ō": ("o", 1), "ó": ("o", 2), "ǒ": ("o", 3), "ò": ("o", 4),
    "ū": ("u", 1), "ú": ("u", 2), "ǔ": ("u", 3), "ù": ("u", 4),
    "ǖ": ("v", 1), "ǘ": ("v", 2), "ǚ": ("v", 3), "ǜ": ("v", 4),
    "ü": ("v", 0),  # bare umlaut, no tone mark of its own (neutral resolved below)
}


def strip_tone(syllable):
    """('qiān') → ('qian', 1); ('nǚ') → ('nv', 3); neutral ('de') → ('de', 5).

    Returns (ascii_base, tone). A single pinyin syllable carries exactly one
    tone-marked vowel; neutral-tone syllables carry none and get tone 5.
    """
    base = []
    tone = 5  # neutral until a tone mark is seen
    for ch in syllable:
        if ch in _TONE_VOWELS:
            plain, t = _TONE_VOWELS[ch]
            base.append(plain)
            if t:  # a real tone mark (not the bare ü)
                tone = t
        else:
            base.append(ch)
    return "".join(base), tone


def _tone_mark_count(reading):
    """How many tone-marked vowels the reading carries. One → single toned syllable;
    more → a multi-syllable name (stroke names like 'héngzhégōu')."""
    return sum(1 for ch in reading if ch in _TONE_VOWELS and _TONE_VOWELS[ch][1])


def audio_key(reading):
    """Bank key for a CN reading, or None if it is not one bank-eligible syllable.

    'qiān' → 'qian1', 'nǚ' → 'nv3', 'yī' → 'yi1'.
    'héngzhégōu' → None (three tone marks → multi-syllable, stays per-item).
    """
    if not reading:
        return None
    if _tone_mark_count(reading) != 1:
        return None  # 0 = untoned/unknown, >1 = multi-syllable — neither is bank-eligible
    base, tone = strip_tone(reading)
    if not base.isascii() or not base.isalpha():
        return None
    return f"{base}{tone}"


# ── pinyin → zhuyin (注音/Bopomofo) ────────────────────────────────────────────
# For the Taiwan phonetic column on the syllable page. Input is the ASCII base from
# strip_tone (no tone mark; ü already 'v'). Zhuyin has no letters for the syllabic
# consonants (zhi/chi/shi/ri/zi/ci/si) — the initial stands alone — and no zero-
# initial glide symbols (yi/wu/yu are spelling dressings of i/u/ü), so those are
# unwound before the initial+final tables compose.

_ZH_INITIAL = {
    "b": "ㄅ", "p": "ㄆ", "m": "ㄇ", "f": "ㄈ", "d": "ㄉ", "t": "ㄊ", "n": "ㄋ",
    "l": "ㄌ", "g": "ㄍ", "k": "ㄎ", "h": "ㄏ", "j": "ㄐ", "q": "ㄑ", "x": "ㄒ",
    "zh": "ㄓ", "ch": "ㄔ", "sh": "ㄕ", "r": "ㄖ", "z": "ㄗ", "c": "ㄘ", "s": "ㄙ",
}

_ZH_FINAL = {
    "a": "ㄚ", "o": "ㄛ", "e": "ㄜ", " e": "ㄝ", "ai": "ㄞ", "ei": "ㄟ", "ao": "ㄠ",
    "ou": "ㄡ", "an": "ㄢ", "en": "ㄣ", "ang": "ㄤ", "eng": "ㄥ", "er": "ㄦ",
    "i": "ㄧ", "ia": "ㄧㄚ", "ie": "ㄧㄝ", "iao": "ㄧㄠ", "iou": "ㄧㄡ", "iu": "ㄧㄡ",
    "ian": "ㄧㄢ", "in": "ㄧㄣ", "iang": "ㄧㄤ", "ing": "ㄧㄥ", "iong": "ㄩㄥ",
    "u": "ㄨ", "ua": "ㄨㄚ", "uo": "ㄨㄛ", "uai": "ㄨㄞ", "uei": "ㄨㄟ", "ui": "ㄨㄟ",
    "uan": "ㄨㄢ", "uen": "ㄨㄣ", "un": "ㄨㄣ", "uang": "ㄨㄤ", "ong": "ㄨㄥ", "ueng": "ㄨㄥ",
    "v": "ㄩ", "ve": "ㄩㄝ", "van": "ㄩㄢ", "vn": "ㄩㄣ",
}

# Zero-initial syllables written with y/w — normalize the whole final back to its
# medial form before lookup. Order matters: longer keys first (weng before wen).
_ZERO_INITIAL = [
    ("yuan", "van"), ("yue", "ve"), ("yun", "vn"), ("yu", "v"),
    ("yong", "iong"), ("ying", "ing"), ("yin", "in"), ("yang", "iang"), ("yan", "ian"),
    ("yao", "iao"), ("you", "iou"), ("ye", "ie"), ("ya", "ia"), ("yi", "i"), ("y", "i"),
    ("weng", "ueng"), ("wang", "uang"), ("wan", "uan"), ("wen", "uen"),
    ("wai", "uai"), ("wei", "uei"), ("wo", "uo"), ("wa", "ua"), ("wu", "u"), ("w", "u"),
]

# After j/q/x, a written 'u' is really ü — restore it so the ㄩ finals are picked.
_JQX = {"j", "q", "x"}
# Syllabic-consonant syllables: the 'i' is not ㄧ; the initial stands alone.
_SYLLABIC = {"zhi", "chi", "shi", "ri", "zi", "ci", "si"}


def to_zhuyin(base):
    """ASCII pinyin base (no tone) → zhuyin string, or None if it doesn't parse.
    'qian' → 'ㄑㄧㄢ', 'nv' → 'ㄋㄩ', 'zhi' → 'ㄓ', 'yi' → 'ㄧ', 'er' → 'ㄦ'."""
    if not base:
        return None
    if base in _SYLLABIC:
        return _ZH_INITIAL[base[:-1]]
    for pre, final in _ZERO_INITIAL:  # zero-initial y/w syllables have no initial
        if base == pre:
            return _ZH_FINAL[final]
    for init in ("zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l", "g",
                 "k", "h", "j", "q", "x", "r", "z", "c", "s"):
        if base.startswith(init):
            rest = base[len(init):]
            if init in _JQX and rest and rest[0] == "u":
                rest = "v" + rest[1:]  # ju/qu/xu → jü/qü/xü
            fin = _ZH_FINAL.get(rest)
            if fin is None:
                return None
            return _ZH_INITIAL[init] + fin
    return _ZH_FINAL.get(base)  # bare final (a, o, e, ai, ao, an, en, er, ...)


# ── the syllable bank inventory ────────────────────────────────────────────────
# One definition of "the CN syllable bank", shared by build-phonetics (the /zhuyin/
# page) and gen-audio (the audio clips) so the two can never drift on which syllables
# exist or which hanzi voices each one.

# Representative preference: a real character voices a syllable cleanly; a stroke or
# bare component (㇐ ㇏ メ) can't be spoken by the TTS voice, so it must never be the
# clip's representative when a character reads the same syllable. Lower rank wins.
_REP_RANK = {"char": 0, "comp": 1, "stroke": 2}


def _observe(entries, glyph, reading, gloss, rank):
    """Record one (glyph reads syllable) observation into the bank, if it is a single
    bank-eligible syllable voiced by a single hanzi. First writer sets the canonical
    pinyin/zhuyin; a glyph is listed once even if seen as both a reading and an example."""
    key = audio_key(reading)
    if key is None or not glyph or len(glyph) != 1:
        return
    base, tone = strip_tone(reading)
    e = entries.setdefault(key, {
        "key": key, "pinyin": reading, "base": base, "tone": tone,
        "zhuyin": to_zhuyin(base), "glyphs": [],
    })
    if all(g["glyph"] != glyph for g in e["glyphs"]):
        e["glyphs"].append({"glyph": glyph, "gloss": gloss, "rank": rank})


def bank(symbols):
    """Project the CN syllable bank from the symbol store: {key: entry}, one entry per
    bank-eligible syllable, sorted by key. Each entry carries the pinyin base, tone,
    zhuyin, and every hanzi that reads it (`glyphs`), the first of which is the
    representative used to synthesize the clip (edge-tts can't voice bare pinyin) — a
    real character where one exists, never an unspeakable stroke/component.

    Scans both a glyph's own reading and its example (`appearsIn`) — the example plays
    the appearing character's reading, itself just a syllable, so it dedupes into the
    same bank. Both the page and the audio generator consume this, so "what syllables
    exist" and "which hanzi says each one" have a single source."""
    entries = {}
    for s in symbols.values():
        r = (s.get("readings") or {}).get("cn") or {}
        _observe(entries, s["glyph"], r.get("reading"), r.get("gloss", ""),
                 _REP_RANK.get(s.get("class"), 3))
    for s in symbols.values():  # examples are real chars in context → rank as characters
        ai = ((s.get("readings") or {}).get("cn") or {}).get("appearsIn") or {}
        _observe(entries, ai.get("char"), ai.get("reading"), ai.get("gloss", ""), 0)
    for e in entries.values():  # most-speakable representative first, then stable by glyph
        e["glyphs"].sort(key=lambda g: (g["rank"], g["glyph"]))
    return {k: entries[k] for k in sorted(entries)}


def _selftest():
    """Validate against the live symbol inventory: every single-syllable CN reading
    yields a clean key; the known multi-syllable stroke names yield None."""
    import sys
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from symbols_io import load_symbols

    keyed, skipped = {}, []
    for s in load_symbols().values():
        r = (s.get("readings") or {}).get("cn") or {}
        reading = r.get("reading")
        if not reading:
            continue
        k = audio_key(reading)
        (skipped if k is None else keyed.setdefault(k, [])).append((s["glyph"], reading))

    print(f"single-syllable → {len(keyed)} unique keys "
          f"from {sum(len(v) for v in keyed.values())} readings")
    collisions = {k: v for k, v in keyed.items() if len(v) > 1}
    print(f"homophone keys (dedupe wins): {len(collisions)}")
    for k, v in sorted(collisions.items())[:8]:
        print(f"  {k}: {' '.join(g for g, _ in v)}")
    print(f"\nnot bank-eligible ({len(skipped)}):")
    for g, reading in skipped:
        print(f"  {g} «{reading}»  {'→ ' + str(_tone_mark_count(reading)) + ' tone marks'}")

    # zhuyin coverage: every single-syllable base must convert without fall-through.
    bases = {strip_tone(reading)[0] for k, v in keyed.items() for _, reading in v}
    missing = sorted(b for b in bases if to_zhuyin(b) is None)
    print(f"\nzhuyin: {len(bases) - len(missing)}/{len(bases)} bases convert")
    if missing:
        print(f"  ✗ no zhuyin for: {' '.join(missing)}")
    else:
        for b in sorted(bases)[:12]:
            print(f"  {b} → {to_zhuyin(b)}")


if __name__ == "__main__":
    _selftest()
