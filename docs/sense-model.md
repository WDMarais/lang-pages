# The sense model — polysemy & polyphony as one mechanism

**Status: design, not implemented.** This is the spec to review before code lands. It
**supersedes `docs/polyphonic-readings.md`** (the reading→list idea): that axis is a
special case of what follows, and its still-live details — the representative-voicing
bug and per-reading audio derivation — are carried in here.

## The problem

The data layer assumes **glyph = one meaning**. A glyph mints exactly one referent
(`build-graph.py:158-162`): `r:{slug(gloss)}` from its single `readings.{cn,jp}.gloss`,
with one `denotes` edge; `check-source` then holds a bare-glyph word to *"denote its
head glyph's referent."*

That assumption breaks on two orthogonal axes we have been conflating:

- **Polyphony** — one glyph, many *sounds*: 只 zhǐ / zhī, 行 xíng / háng, 生 せい/なま/…
- **Polysemy** — one glyph, many *meanings*: 生 life / raw / grow, independent of sound.

They correlate but are not the same. 外 has **two readings** (そと/がい), **one** sense.
生 in CN has **one sound** (shēng) spanning **three senses** (life/raw/grow). The
forcing case: WK vocab **生 (なま "raw")** is a bare-glyph word whose meaning is a real
sense of 生 that the schema cannot hold, so it trips the head-referent check. It was
deferred (see the `polysemy-ground-up-design` note) pending this model.

## The model: a **sense** between glyph and referent

The primitive that captures both axes is a **sense** — a bundle of *(reading(s) per
language, gloss, referent)*. A glyph owns an ordered **list of senses**; each sense
denotes one referent and carries its own reading-list per language (→ its own audio).

```
glyph 生
 ├─ sense 0 (primary)  cn shēng   jp [せい, しょう]   gloss "life"        → r:life
 ├─ sense 1            cn ―        jp [なま]           gloss "raw; fresh"  → r:raw
 └─ sense 2            cn ―        jp [は, う, い]     gloss "to grow"     → r:grow
```

Today's mono-sense glyph is **a list of one** — which is the entire migration story:
the existing `readings.{cn,jp}` block *is* sense 0. A sense sits on the **core** side of
the core/interface seam for its referent (language-neutral meaning), while its readings
and gloss are **interface** (per-language) — consistent with `glossary.md`.

## The four settled decisions

1. **Bundle, not matrix.** A sense = *(readings + gloss + referent)*. One sound may
   recur across senses (生 shēng in all three); we do **not** model an orthogonal
   reading×sense matrix. Bundle holds every case we have; the matrix (one sound fanning
   into several sub-senses, e.g. 行 háng → row/profession/business) is deferred until a
   real case demands it, and would then split into multiple senses that share a reading.
2. **Keep primary + optional `senses[]`.** `readings.{cn,jp}` stays as sense 0; extra
   senses live in an optional `senses[]`. Back-compatible — the vast majority of the 349
   symbols are untouched.
3. **On-demand enumeration.** Add a sense when a word or lesson needs it (monotonic
   enrichment). 生 gets *raw* now; *grow* arrives with 生える. No exhaustive dictionary
   pass.
4. **Per-language, override-else-inherit, gated** (see next section).

## Reading ↔ sense coupling

A non-primary sense states a reading **only for the language where it differs**; an
omitted language inherits the **primary sense's** reading for that language.

The default is safe only where inheritance is unambiguous, and the gate draws that line
mechanically:

> A non-primary sense may omit language *L*'s reading **iff the glyph resolves to a
> single distinct sound in *L***. If the glyph carries >1 reading in *L* across its
> senses, every non-primary sense **must** state its own *L* reading — omission is a
> `check-source` **error**, not a silent default.

| glyph | CN | JP | behaviour |
|-------|----|----|-----------|
| 生 | monophonic (shēng) | per-sense | CN inherits shēng freely; JP explicit (なま/せい/は… all differ) |
| 只 | polyphonic (zhǐ/zhī) | — | the zhī sense **must** declare `cn: {reading:"zhī"}` — gate enforces |
| 行 | polyphonic (xíng/háng) | — | any háng sense **must** declare it — no silent xíng |
| 外 | two readings, one sense | — | not a `senses[]` case at all — a reading-list *within* sense 0 |

This is decision-3-from-the-chat (override-when-provided) made **per-language**
(decision 2), demanding the **explicit** of decision 1 *exactly and only* where
inheritance would be a guess. DRY in the common case (secondary sense, same sound,
meaning-only split — the bulk of CN polysemy); enforced-explicit where it would rot.

Inheritance always targets **sense 0**, a well-defined anchor thanks to keep-primary.

## Schema

`senses[]` is a sibling of `readings`/`programs`/`composes` on the symbol. Each entry:

```jsonc
// data/symbols/生.json (illustrative)
"readings": {
  "cn": { "name": "生", "reading": "shēng", "gloss": "life" },      // sense 0 (primary)
  "jp": { "name": "生", "reading": ["せい","しょう"], "gloss": "life" }
},
"senses": [
  { "gloss": "raw; fresh; uncooked", "denotes": "raw",
    "jp": { "reading": ["なま"] } },                                 // cn omitted → inherit shēng
  { "gloss": "to grow; to be born", "denotes": "grow",
    "jp": { "reading": ["は","う","い"] } }
]
```

- A sense entry is `{ gloss, denotes, cn?: { reading }, jp?: { reading } }`.
- `cn`/`jp` are optional; absence = inherit-or-error per the coupling rule.
- `reading` is a **string or list** (list = polyphony within that sense; bare string =
  list of one). First element = that language's primary reading for the sense.
- `denotes` is the referent slug the sense points at (same field words already use), so
  a sense and a word can rejoin the same referent.
- **Primary marker** = position (sense 0 = the `readings` block). `senses[]` are the
  non-primary senses, in teaching order.

Back-compat: a file with no `senses[]` is a one-sense glyph; `readings.<lang>.reading` as
a bare string is a one-reading sense. Nothing to migrate until a glyph needs a 2nd sense.

## What it buys

1. **The 生 warning was correct — just single-sense-blind.** New `check-source` rule: a
   bare-glyph word is valid if its `denotes` ∈ *any* of the glyph's sense-referents.
   生(なま) **rejoins** the raw sense — it never diverged. No opt-out flag, no per-word
   suppression.
2. **Polyphony falls out.** A sense owns a reading-list; each resolved reading derives
   one content-keyed audio clip (`nama.mp3` returns as the legit audio of 生's raw
   sense). CN and JP unify under one mechanism instead of CN-single / JP-via-program.
3. **The 所指/referent panel gets richer, not redesigned.** A glyph denotes *N*
   referents, one per sense — 生's dossier shows the life-referent **and** the
   raw-referent, each with its reading(s) + audio + gloss.
4. **A new interference locus.** Senses of one glyph compete (生 life vs raw) — a
   type-**D** for the `deck-design.md` interference taxonomy (A leakage / B confusable /
   C hierarchy). Same-glyph-different-sense is its own thing to sequence around.

## Audio (carried from the polyphony memo)

Clips are content-keyed by **sound**. The build derives one key per **resolved** reading
across all senses, per language (`cn_key`/`kana_key` are pure), and generates one clip
each. Nothing is stored — `key = f(reading)`.

The **representative-voicing** rule from the polyphony memo survives intact and is the
reason senses help: a shared syllable clip (`zhi3.mp3`, voiced by handing one glyph to
edge-tts) must pick a **monophonic representative** — a glyph that resolves to a single
reading in that language — so a polyphonic char like 只 never re-voices a shared clip
with the wrong reading. With senses, "monophonic" is well-defined: the glyph's senses
resolve to one sound in *L*.

## Interaction with `script.traditional`

`traditional-script.md` already sense-conditions forms via a free-text `when`
qualifier (`{ "glyph": "隻", "when": "measure word" }`). Senses formalize what `when`
gestures at: a form entry's `when` should reference a **sense** (by its `denotes`/gloss),
so 只's zhī/measure-word sense and its 隻 traditional form point at each other instead of
matching on prose. Out of scope for the first cut; noted so the two don't drift.

## Touchpoints (supersedes the polyphony memo's list)

- **Schema** `data/symbols/*.json`: optional `senses[]`; `reading` string-or-list.
- **`symbols_io`** (`card_audio_keys`, `PROGRAM_TIERS` neighbours): resolve each sense's
  readings (own or inherited), emit a key per reading; keep the primary key where a
  scalar is still expected during migration.
- **`build-graph.py`**: mint a referent + `denotes` edge **per sense** (not just the
  gloss-derived primary); carry per-sense readings/keys onto the binding.
- **`build-pages.py` / dossier**: render N senses, each reading with its own play button
  and the sense's gloss + referent.
- **`gen-audio.py`**: (a) a clip per resolved reading; (b) prefer a single-reading glyph
  as each shared syllable's representative (the tone-safety fix).
- **`check-source.py`**: (a) bare-glyph word valid if `denotes` ∈ glyph's sense
  referents; (b) the coupling-rule guard (omitted reading legal iff monophonic in *L*);
  (c) validate each sense (non-empty gloss, present `denotes`, valid single-syllable CN
  readings).
- **`cards3.js` / glyph dossier**: N readings × senses, each its own audio.

## First citizen & rollout

1. Land the schema + build/gate/audio changes above, mono-sense files unchanged.
2. **Re-ingest 生**: add sense 1 `{ gloss:"raw; fresh", denotes:"raw", jp:{reading:["なま"]} }`;
   restore the 生 (なま) word (it now rejoins r:raw via the sense); `nama.mp3` regenerates.
   Un-defer the `polysemy-ground-up-design` item.
3. Backfill opportunistically: audit `gen-audio`'s chosen syllable representatives
   against multi-reading glyphs (只 first), and add senses where a shipped word already
   strains the head-referent rule.

## Open questions

- **Per-sense sense-label vs gloss** — is a sense's `gloss` enough, or does it want a
  short label (zhǐ "only" / zhī "MW") distinct from the full gloss? (Gloss-only to start.)
- **`when` ↔ sense reference** — formalize the traditional-form tie now or after the
  first cut? (After.)
- **Referent sharing across senses of *different* glyphs** — 生-raw and 鮮-fresh may want
  one referent; the model already allows it (both `denotes` the same slug), but no policy
  yet on when to merge vs keep distinct. Defer to the referent-QC pass.
