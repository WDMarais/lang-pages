# The `script.traditional` field

How the simplified↔traditional (繁體) correspondence is structured on a symbol.
Companion to [authoring.md](authoring.md) (the symbol-file schema) — this doc
specifies one field it adds. Supersedes the interim "note `繁: X` inline in
`cn.extra`" convention (see memory *cn-traditional-handling*).

## Decision

- **A field, not an edge.** Traditional forms are *orthographic alternates of the
  same teaching unit*, not independently-taught characters — so they live as an
  attribute on the simplified symbol, minting no graph nodes/edges. (Contrast
  `association` confusable/cognate, where both glyphs are real things you learn
  separately → edges. A specific traditional form can be *promoted* to a real node
  later if it ever needs teaching in its own right.)
- **One axis: the orthodox Han form.** We already store the other two axes —
  `glyph` = simplified CN, `readings.jp.name` = JP shinjitai (従, 個, 業…). The only
  missing axis is the traditional/orthodox Han form, and Han-traditional stands in
  for JP-kyujitai too (體=體, 從=從, 萬=萬 — they diverge on the *simplified* side,
  not the old side). So one new field completes the picture; no `jp.name` migration.

## Schema

`script.traditional` — sibling of `readings`/`programs`/`composes` on the symbol.
Its value is one of:

| value | meaning | example |
|---|---|---|
| list of entries | the traditional form(s) | see below |
| `"same"` | **verified** no divergence (繁体同) | 可, 如 |
| *absent* | **not yet classified** — `check-source` warns (CN char only) | — |

`"same"` vs absent is the point: it separates *checked, identical* from *unknown*,
so the gate can flag the real backlog instead of silently passing everything.

An **entry** is `{ "glyph": "體", "when"?: "<sense>" }`:
- `glyph` (req) — a single traditional CJK character.
- `when` (opt) — the sense under which this form applies; **required when >1 entry**
  disambiguates by meaning (the merge cases), omitted for a plain 1:1.

```jsonc
// 体 — 1:1
"script": { "traditional": [ { "glyph": "體" } ] }

// 个 — one simplified glyph, several traditional forms
"script": { "traditional": [ { "glyph": "個" },
                             { "glyph": "箇", "when": "classifier; literary" } ] }

// 后 — sense-conditioned merge: 後 only for the "after" sense; queen-sense 后 is unchanged
"script": { "traditional": [ { "glyph": "後", "when": "after; behind; time & position" },
                             { "glyph": "后", "when": "empress; queen (unchanged)" } ] }

// 可 / 如 — verified identical
"script": { "traditional": "same" }
```

A `when`-entry whose `glyph` equals the simplified glyph itself (后→后) means *that
sense did not change* — the honest way to say "partial merge".

## The one edge case: 円 (JP-primary glyph)

円 inverts the axes — the file is the JP **shinjitai**, its orthodox form is 圓, and
Chinese uses a *different* simplification 圆. The minimal model marks this with
`script.role: "shinjitai"` (default, unstated, is `"simplified"`) and records
`traditional: [ { "glyph": "圓" } ]`; the "中文作 圆" cross-note stays in prose,
since 円 is off the CN teaching axis (罕用) and not worth a fourth structured slot.
This is the sole glyph the traditional-Han-only scope doesn't fully structure —
accepted, documented, revisitable if more JP-primary glyphs arrive.

## Projection & tooling

- **`to_card`** (`symbols_io.py`) passes `traditional` through onto the card, the
  same way `readings` flow — so both build-pages (render) and build-graph (node +
  round-trip) see it and round-trip stays ✓.
- **Card render** (`cards3.*`): a 繁 chip beside the glyph showing the traditional
  form(s); the `when` qualifier as a caption/tooltip on multi-entry cards; `"same"`
  renders as a subtle 繁=简 marker (or nothing). Replaces the buried `繁: X` prose.
- **`check-source` gate**: a CN `char`-class symbol with a `cn` reading and no
  `script.traditional` (neither list nor `"same"`) → warning `traditional not
  classified`. Validates entry shape (single CJK `glyph`; `when` present when
  multiple entries diverge by sense). Same machinery that gates readings/audio keys.

## Backfill

Ship the mechanism plus the ~13 glyphs already carrying inline `繁` prose, stripping
the now-redundant `繁: X` fragment from `cn.extra` as each is structured:

万→萬 · 与→與 · 业→業 · 个→個/箇 · 义→義 · 于→於 · 从→從 · 体→體 · 儿→兒 ·
后→後(+后 queen) · 円→圓(role: shinjitai) · 可→same · 如→same

The gate then surfaces every *remaining* unclassified CN char as a warning, so the
rest is incremental and tracked rather than silent — same play as the frontier
word-part warnings.
