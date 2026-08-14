# Spatial relators & locative phrases (の上/の下/…) — design memo

**Status: design only, not implemented.** Captures how locative phrases should be
represented so we don't ram them into the radial decomposition UI, where they don't
belong. Motivated by WaniKani L3 vocab **テーブルの上** ("on the table") and its sibling
**ベッドの下** ("under the bed") — a *class*, not two special cases.

## Why the radial breaks

A radial shows part→whole glyph decomposition ("what strokes/components is this glyph
made of"). A locative phrase is a different kind of thing:

```
テーブルの上  =  テーブル (katakana loanword)  +  の  +  上 (glyph)
```

1. **テーブル isn't a glyph.** It's a borrowed word — no stroke decomposition to draw.
2. **The meaning is a spatial relation, not a composition.** "on top of the table" is
   *where X is relative to Y*, not *what X is built from*. Forcing it into a part-whole
   radial mislabels the semantics.

## The class, and the unit worth teaching

The phrases share one shape:

```
[NOUN] の [LOCATION]     LOCATION ∈ { 上 下 中 前 後 左 右 横 間 隣 外 … }
```

`の` is the **arrangement operator** ("the top *of* the table") — precisely the "missing
arrangement descriptor" that [[cross-script-composition]] flagged as the CJK-shaped gap
(an edge asserts *participation*, not *position*; here position is the whole point).

The `LOCATION` slot is a **small, bounded, enumerable set of spatial relators**. That is
textbook [[enumerable-referent-principle]]: a bounded relation-space self-defines its
deck. So the unit worth teaching is the **relator** (`の上` = "on top of"), applied to a
noun — *not* the instance. Minting one node per `NOUN × RELATOR` combination
(テーブルの上, 机の上, 箱の上, ベッドの下, 箱の中, …) is a combinatorial explosion with no
pedagogical payoff; the learner needs 上/下/中 once and composes freely thereafter.

## Representation: a positional diagram, not text chips

Locatives want a **visual** render ([[feedback-visual-first]], [[scene-component]]): a
small positional diagram — a reference object with the relevant zone highlighted, or a
figure placed *on / under / inside* it — the same enumerable-region trick as the
[[body-diagram-idea]]. `の上` is a reusable widget: swap the noun and the relator and the
identical component renders ベッドの下 for free. Text ("on the table") is the demotable
fallback, not the anchor.

## Data-model options (the fork)

- **A. Instance node** — store テーブルの上 as a word, parts `[テーブル, 上]`, の omitted.
  WK-faithful and cheap, but (i) renders flat, (ii) needs テーブル as a loanword vocab
  node, and (iii) mints the explosion above. *Rejected as the teaching unit.*
- **B. Relator-as-operator (preferred direction)** — first-class **relators**
  (`の上` → referent `r:on-top-of`, carrying an SVG position zone), plus nouns as
  ordinary vocab words (テーブル → `r:table`). The phrase is the operator applied to the
  noun; the positional diagram is the render. Requires a small relators table + a new
  card render branch that detects a `の[relator]` surface.
- **C. Patterns layer** — `[NOUN]の[LOCATION]` is a *generated* construction, not a
  stored node; the substrate gains a thin "patterns" layer and phrases are instantiated
  at lesson-time. Avoids instance nodes entirely; biggest new machinery. Compatible with
  B (B supplies the relator + noun pieces the pattern instantiates).

**Recommendation:** treat the **relator** as the durable unit (B), render locatives with
a positional diagram, and let phrase instances be generated (C) rather than stored. Keep
テーブルの上 *out* of the graph until that render exists — a flat two-chip card would
misrepresent it and seed instance-node debt.

## Touchpoints (for whoever implements it)

- **Relators table** — `上下中前後左右横間隣外…` → spatial-relation referent + an SVG
  zone (reuse the strokes/scene SVG infra). A bounded set → an auto-enumerable deck.
- **Loanword vocab** — katakana borrowings (テーブル, ベッド) as first-class word nodes
  with no glyph decomposition; their referent is a direct image (r:table, r:bed), which
  the [[concrete-referent-panel]] already wants.
- **Card render** — a locative branch in cards3 that detects `の[relator]` and draws the
  positional diagram instead of a radial.
- **Deck generation** — relator × noun instantiated at lesson-time (option C), or a
  curated instance list; either way *don't* persist the cross-product as nodes.

## Open questions

- **Do we store any instance at all**, or only relators + nouns + a generator? (Leaning
  generator.)
- **Referent identity for a relator** — `r:on-top-of` as a relation referent; how does it
  sit beside thing-referents in the 所指 panel? A relation isn't an image of an object —
  it's an image of a *configuration* (X-on-Y), which is what [[scene-component]] renders.
- **How does の surface** — an explicit chip, an implicit join, or absorbed into the
  diagram? (The diagram makes it implicit, which is the point.)
- **Backfill** — テーブルの上 and ベッドの下 are the first two known; the full L1-3 WK set
  likely has more locatives to sweep once the render exists.
