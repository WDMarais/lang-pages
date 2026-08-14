# Polyphonic readings (多音字) — design memo

**Status: design only, not implemented.** Captures the intended model so the next
person (or the next glyph) doesn't re-derive it. Motivated by 只 (see below).

## The problem

A character can have more than one reading depending on sense — a *heteronym* /
多音字:

- **只** → **zhǐ** ("only; just": 只有, 只好) and **zhī** (measure word: 一只猫; also
  the traditional 隻).
- 行 → xíng / háng, 长 → cháng / zhǎng, 重 → zhòng / chóng, …

Our symbol schema stores **one** reading per language (`readings.cn.reading: "zhǐ"`,
the secondary noted informally in `extra`). The graph/binding then carries a single
scalar `audio_key` derived from that one reading (`cn_key("zhǐ") → "zhi3"`). So the
second reading is invisible to the data — it can't be shown, played, or reasoned about.

### The concrete bite: shared syllable clips get a polyphonic voice

Audio is **content-keyed by sound**: `audio/cn/zhi3.mp3` is ONE clip shared by every
glyph that reads zhǐ (止, 黹, 夂, 只). gen-audio voices it by handing **one
representative hanzi** to edge-tts *in isolation*, and edge-tts chooses the reading:

- **止** is monophonic → always "zhǐ". Safe.
- **只** is polyphonic → edge-tts may read zhǐ *or* zhī; if zhī, the `zhi3` clip is a
  wrong-tone "zhī" for all four glyphs.

Today gen-audio picks the representative by codepoint order, so adding 只 (U+53EA <
止 U+6B62) silently re-voiced `zhi3.mp3` from 止 → 只 (commit 5fbb807). Same intended
sound, but now voiced by a polyphonic char — a latent tone-safety risk, not a proven bug.

## The model: keys map onto readings, not onto the glyph

`readings` is already an array in the binding projection. The fix is to make the
**source** reading a list too, and derive **one audio key per reading**:

```
只 cn  reading: ["zhǐ", "zhī"]   →  keys ["zhi3", "zhi1"]   (two clips, two play buttons)
一 cn  reading: ["yī"]           →  keys ["yi1"]            (1:1 — nothing changes)
```

Keys are **not stored** — a reading *is* a sound and `cn_key`/`kana_key` are pure, so
the build derives `key = f(reading)` per reading. The single-reading case is a list of
one, so the vast majority of glyphs are untouched.

### What this buys

1. **Heteronyms become first-class.** 只's zhī sense stops living in `extra`; the card
   shows each reading with its own audio. (Sense labels per reading — zhǐ "only" / zhī
   "measure word" — are a natural extension; see open questions.)
2. **The representative bug fixes itself.** gen-audio, choosing the shared syllable-bank
   representative, prefers a glyph whose reading-list has **length 1** (monophonic) — no
   special-casing, no pin map. `zhi3.mp3` goes back to being voiced by 止.
3. **`ex_audio_key` is orthogonal** (whole example-word clip) and unaffected.

### JP already has this shape

Japanese kanji are inherently multi-reading (音読み/訓読み). Today the primary rides in
`readings.jp.reading` and the rest in the `program.kanji.on/kun` arrays — a parallel,
program-tier place. Promoting `reading → list` unifies CN and JP under one mechanism
(`kana_key` per reading), rather than CN-single / JP-via-program.

## Touchpoints (for whoever implements it)

- **Schema** `data/symbols/*.json`: `readings.<lang>.reading` accepts a **string or a
  list** (back-compat: a bare string = list of one). First element = primary.
- **`symbols_io.card_audio_keys`**: emit a key per reading (list), keep the primary key
  where a scalar is still expected during migration.
- **`build-graph` / `build-pages`**: carry the per-reading keys onto the node/card;
  the binding's `readings` + derived `audioKeys` line up 1:1.
- **`gen-audio`**: (a) generate a clip per reading; (b) **prefer a len==1 reading glyph
  as each syllable's representative** (the tone-safety fix).
- **`cards3.js` / glyph dossier**: render N readings, each with its own play button.
- **`check-source`**: validate the list (non-empty, each a valid single-syllable reading
  for CN); optionally warn when a known-polyphonic glyph carries only one reading.
- **Interaction with `script.traditional`**: 只's zhī sense maps to 隻 — a reading can be
  tied to a traditional form (see docs/traditional-script.md). The `when:` qualifier there
  and a per-reading sense may want to reference each other.

## Open questions

- **Primary marker** — first element, or an explicit flag? (First-element is simplest.)
- **Per-reading sense/gloss** — do readings carry their own gloss (zhǐ "only" vs zhī
  "MW"), or stay sound-only with sense in `extra`? Sense-per-reading is the richer model
  and pairs with the 所指/referent panel (a reading can denote a different referent).
- **Which glyphs to backfill** — start with the ones already carded whose bank clip is
  voiced by a polyphonic representative (audit gen-audio's chosen reps against a
  multi-reading list); 只 is the first known case.
