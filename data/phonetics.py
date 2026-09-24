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
import hashlib

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

    'qiān' → 'qian1', 'nǚ' → 'nv3', 'yī' → 'yi1', neutral 'me' → 'me5'.
    'héngzhégōu' → None (three tone marks → multi-syllable, stays per-item).
    """
    if not reading:
        return None
    marks = _tone_mark_count(reading)
    if marks > 1:
        return None  # multi-syllable (stroke names) — not bank-eligible
    base, tone = strip_tone(reading)
    if not base.isascii() or not base.isalpha():
        return None
    if marks == 0 and base not in _SYLLABLES:
        return None  # untoned but not one real syllable: unknown, not a neutral tone
    return f"{base}{tone}"


def multi_key(reading):
    """Companion to audio_key for the handful of multi-syllable stroke names it
    returns None for (héngzhégōu → 'hengzhegou'): strip the tones to an ASCII base so
    those clips are content-keyed too, not slug-keyed. None for empty/non-ASCII."""
    if not reading:
        return None
    base, _ = strip_tone(reading)
    return base if base and base.isascii() and base.isalpha() else None


def cn_key(reading):
    """The CN bank key for any reading: the single-syllable key when there is one
    (qiān → qian1), else the multi-syllable base (shùgōu → shugou)."""
    return audio_key(reading) or multi_key(reading)


# The pinyin chart: which finals each initial actually takes, plus the zero-initial
# (y-/w-/yu-) spellings. Used only to segment a compound reading so each syllable's tone
# digit lands at the syllable's END (真相 → zhen1xiang4, not zhen1xia4ng).
#
# This is a per-initial table rather than initials × finals because the cross-product
# cannot express Mandarin's gaps, and an over-generated syllable is not a harmless
# retry: _segment() backtracks only when the bogus span STRANDS the remainder. When it
# parses the rest cleanly you get a confident wrong answer — 之内 zhinei as zhin+ei.
# The cross-product's three class-level gaps are:
#   · velars g/k/h take no i- or ü-final at all
#   · palatals j/q/x take ONLY i- and ü-finals (their written 'u' IS ü)
#   · retroflex/sibilant zh/ch/sh/r/z/c/s take the syllabic 'i' (zhi, si) but never an
#     i-GLIDE final — this is the zhin trap
# Stating those as exclusion rules still leaves ~129 irregular fakes (fai, bou, shong,
# ruang…) that follow no rule, so the table lists what exists instead of what doesn't.
#
# Erring NARROW is deliberate: a missing syllable fails loudly (the parse fails, no tone
# digits, _selftest's per-hanzi digit count catches it) while a fabricated one fails
# silently. Marginal syllables are therefore omitted until a real reading needs them.
# Spelling is as written — the iou→iu, uei→ui, uen→un contractions, ü as 'v' after n/l
# (strip_tone's output) but as 'u' after j/q/x. _selftest() segments the whole CN word
# list to keep this honest.
_CHART = {
    "b":  "a o ai ei ao an en ang eng i ie iao ian in ing u",
    "p":  "a o ai ei ao ou an en ang eng i ie iao ian in ing u",
    "m":  "a o e ai ei ao ou an en ang eng i ie iao iu ian in ing u",
    "f":  "a o ei ou an en ang eng u",
    "d":  "a e ai ei ao ou an en ang eng ong i ia ie iao iu ian ing u uo ui uan un",
    "t":  "a e ai ao ou an ang eng ong i ie iao ian ing u uo ui uan un",
    "n":  "a e ai ei ao ou an en ang eng ong i ie iao iu ian in iang ing u uo uan un v ve",
    "l":  "a o e ai ei ao ou an ang eng ong i ia ie iao iu ian in iang ing u uo uan un v ve",
    "g":  "a e ai ei ao ou an en ang eng ong u ua uo uai ui uan un uang",
    "k":  "a e ai ei ao ou an en ang eng ong u ua uo uai ui uan un uang",
    "h":  "a e ai ei ao ou an en ang eng ong u ua uo uai ui uan un uang",
    "j":  "i ia ie iao iu ian in iang ing iong u ue uan un",
    "q":  "i ia ie iao iu ian in iang ing iong u ue uan un",
    "x":  "i ia ie iao iu ian in iang ing iong u ue uan un",
    "zh": "a e i ai ei ao ou an en ang eng ong u ua uo uai ui uan un uang",
    "ch": "a e i ai ao ou an en ang eng ong u ua uo uai ui uan un uang",
    "sh": "a e i ai ei ao ou an en ang eng u ua uo uai ui uan un uang",
    "r":  "e i ao ou an en ang eng ong u uo ui uan un",
    "z":  "a e i ai ei ao ou an en ang eng ong u uo ui uan un",
    "c":  "a e i ai ao ou an en ang eng ong u uo ui uan un",
    "s":  "a e i ai ao ou an en ang eng ong u uo ui uan un",
}

# Zero-initial syllables. NB 'eng' is absent by the same rule as the rest of the table:
# unlike 'en'/'ang' no character reads ēng, and admitting it let a preceding syllable's
# coda be stolen (只能 zhineng → zhin+eng). 'er' stands alone here and appears under no
# initial — a fabricated 'ger' would mis-split 个人 gèrén to ger+en.
_ZERO = ("yi ya ye yao you yan yin yang ying yong wu wa wo wai wei wan wen wang weng "
         "yu yue yuan yun yo a o e ai ei ao ou an en ang er")


def _build_syllables():
    syl = set(_ZERO.split())
    for initial, finals in _CHART.items():
        syl.update(initial + f for f in finals.split())
    return frozenset(syl)


_SYLLABLES = _build_syllables()
_MAX_SYL = 6  # zhuang / chuang / shuang


def _is_syllable(chunk, final):
    """A syllable, optionally carrying an erhua coda (nar, tour, huir). The coda is
    allowed only on the LAST syllable of the chunk: an unanchored 'r' would let 本人
    benren split as benr+en, since 'en' is itself a zero-initial syllable."""
    if chunk in _SYLLABLES:
        return True
    return final and chunk.endswith("r") and chunk[:-1] in _SYLLABLES


def _segment(base):
    """Split an ASCII pinyin base (one apostrophe-free chunk) into syllable spans,
    longest match first but BACKTRACKING when that strands the remainder. Returns a
    list of [start, end] or None if it doesn't parse.

    Plain greedy is not enough: a syllable-final n/ng is equally a following syllable's
    initial, so 只能 zhineng grabs zhin and leaves eng. Backtracking rejects that split
    the moment the remainder fails to parse, and zhi+neng wins. Erhua 'r' rides along
    on its syllable (see _is_syllable), keeping 一会儿 yihuir as yi+huir."""
    n = len(base)
    memo = {}

    def parse(i):
        if i == n:
            return []
        if i not in memo:
            memo[i] = None
            for j in range(min(n, i + _MAX_SYL + 1), i, -1):
                if not _is_syllable(base[i:j], j == n):
                    continue
                rest = parse(j)
                if rest is not None:
                    memo[i] = [[i, j]] + rest
                    break
        return memo[i]

    return parse(0)


def word_key(surface, reading):
    """Bank key for a whole CN WORD clip → audio/cn/<key>.mp3, the CN analog of the
    JP jpAudioKey (phonetics_jp.kana_key). Unlike a bare syllable, a word is real
    hanzi (真相), directly speakable, so its clip is voiced by the SURFACE itself — no
    representative hanzi needed.

    A single-hanzi word is one syllable (犬 quǎn → 'quan3'): it reuses the syllable
    bank clip the glyph already voices, so it routes through audio_key and shares it.
    A compound is keyed by its reading segmented into per-syllable tone keys, each in
    the same ü→v, trailing-tone-digit form the syllable bank uses (真相 zhēnxiàng →
    'zhen1xiang4', 十二 shí'èr → 'shi2er4', 一下 yīxià → 'yi1xia4', 以下 yǐxià →
    'yi3xia4'). Tone lives in the key, so two compounds differing only in tone no
    longer collide. If a reading fails to segment (unexpected spelling), fall back to
    the tone-stripped ASCII base so a clip is still produced."""
    if not reading:
        return None
    if len(surface) == 1:  # one hanzi = one syllable → share the glyph's bank clip
        return audio_key(reading)
    parts = []
    for chunk in reading.replace("’", "'").split("'"):
        chars, tones = [], []
        for ch in chunk:
            if ch in _TONE_VOWELS:
                plain, t = _TONE_VOWELS[ch]
                chars.append(plain)
                tones.append(t or None)
            elif ch.isascii() and ch.isalpha():
                chars.append(ch.lower())
                tones.append(None)
            # any other char (spaces, digits, stray marks) is dropped
        base = "".join(chars)
        spans = _segment(base)
        if spans is None:
            parts.append(base)  # fallback: tone-stripped, still filename-safe
            continue
        for s, e in spans:
            tone = next((t for t in tones[s:e] if t), 5)
            parts.append(f"{base[s:e]}{tone}")
    key = "".join(parts)
    return key or None


def sentence_key(lang, text):
    """Content-key for a whole SENTENCE clip → audio/sent/<lang>-<digest>.mp3.

    The syllable banks key by the sound spelled out (qian1, sen) because a syllable has
    a short canonical spelling. A sentence has none — so it is keyed by a digest of its
    own text. That is the same content-keyed principle (the identical sentence, authored
    in two clusters, is voiced ONCE) under the only spelling that scales.

    `lang` sits in the key rather than the digest, so a clip still says which voice it
    belongs to at a glance. The VOICE deliberately does not: swapping CN_VOICE must
    RESTAMP the clip, not rename every file — gen-audio's manifest already regenerates a
    clip whose recorded voice has moved. Language-neutral, hence no cn/jp in the name.
    """
    if not lang or not text:
        return None
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{lang}-{digest}"


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
    "i": "ㄧ", "ia": "ㄧㄚ", "io": "ㄧㄛ", "ie": "ㄧㄝ", "iao": "ㄧㄠ", "iou": "ㄧㄡ", "iu": "ㄧㄡ",
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
    ("yao", "iao"), ("you", "iou"), ("yo", "io"), ("ye", "ie"), ("ya", "ia"),
    ("yi", "i"), ("y", "i"),
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
    """Validate against the live inventory: every single-syllable CN reading yields a
    clean key; the known multi-syllable stroke names yield None; and every CN word
    segments, with one tone digit per hanzi (the check that catches a mis-split)."""
    import sys
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from paths import DATA, read_json
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

    # Word segmentation: a compound of N hanzi must key to N tone digits. A mis-split
    # still "parses" (zhineng → zhin1eng2), so counting spans is what exposes it; a
    # reading that fails outright falls back to a digit-free base, caught by the same
    # test. 〜 and ASCII in a surface are not syllables, hence the hanzi filter.
    words = read_json(DATA / "words.json")
    words = words["words"] if isinstance(words, dict) else words
    bad = []
    for w in words:
        if w.get("audience") != "cn" or not w.get("reading"):
            continue
        surface, reading = w["surface"], w["reading"]
        hanzi = [c for c in surface if "一" <= c <= "鿿"]
        if len(hanzi) != len(surface):
            continue
        want = len(hanzi)
        if want > 1 and surface.endswith("儿") and reading.endswith("r"):
            want -= 1  # erhua: 儿 fuses onto the previous syllable, no clip of its own
        key = word_key(surface, reading)
        digits = sum(c.isdigit() for c in key or "")
        if digits == want:
            continue
        bad.append((surface, reading, key, want, digits))
    print(f"\nword keys: {len(bad)} mis-segmented")
    for surface, reading, key, want, got in bad:
        print(f"  ✗ {surface} «{reading}» → {key}  ({got} syllable(s), expected {want})")


if __name__ == "__main__":
    _selftest()
