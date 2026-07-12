# Authored-edge layer (draft)

> Status: **draft / proposal**. Extends `content-graph-schema.md`. Defines the
> first member of the **authored enrichment layer** — edges a human asserts that
> the decomposition graph cannot derive. First concrete kind: `confusable`.
>
> Design stance (unchanged): **bootstrap, don't boil the ocean.** Ship one
> explicit file + a linear join in build-graph, hand-write the first few entries,
> mechanize later. See memory `feedback-bootstrap-over-monolith`.

## Why a new layer

The graph today has three edge kinds, all **derived** from structural facts:
`composes` (from IDS decomposition), `denotes` (from a binding's gloss), `variant`
(from a symbol's `variants` field). None can express *"these two are easy to mix
up — teach them together against contrasting context."* That relation is
irreducibly **authored**: a human judgement, not a fact about the writing system.
It's the concrete first case of the "custom authored-edge layer" named in memory
`greenfield-independence-goal` — an addon on top of the pure graph, the same layer
that will later hold custom ordering and "see also" links.

Endpoint-agnostic by design (resolved 2026-07-12, memory
`confusable-pair-anchoring`): ONE `confusable` kind covers glyph↔glyph (人/入),
word↔word (可不/不可), and authored-entity↔entity (Three Kingdoms 馬謖/馬岱). The
endpoint *type* is carried by the node ids the edge connects, so it is never
re-encoded in the edge kind.

## Physical source of truth: `data/authored.json`

A single new curated side-input, sibling to `words.json` /
`composition-roles.json`. **Not** inline on symbols — an edge is between two nodes
and may name a word or an authored entity, so it can't live on one glyph atom.

```jsonc
{
  "edges": [ /* authored edges — see below */ ],
  "nodes": [ /* OPTIONAL authored entities (Three-Kingdoms case); reserved, empty for v1 */ ]
}
```

`build-graph.py` gains a `load_authored()` pass (after the word pass) that:
1. mints any authored `nodes` as `{id, kind:"entity", label, media?}`, and
2. expands each authored `edges` entry into the output `edges.json`.

Authored edges are **purely additive** to `edges.json` — no card projects them,
so the radicals/strokes round-trip identity is untouched.

## The `confusable` edge (authored form)

```jsonc
{
  "kind": "confusable",
  "between": ["可不", "不可"],          // ≥2 node refs, UNORDERED (symmetric relation)
  "audience": "cn",                      // disambiguates bare-glyph / word refs; optional if all refs are full ids
  "basis": "phonetic",                   // visual | phonetic | semantic  (optional; a RENDERING hint, not a fork)
  "note": "same two chars reversed; 可不(是) = 'isn't it just', 不可 = 'cannot'",
  "examples": [                          // OPTIONAL grounding — the pedagogical half
    { "for": "可不", "text": "可不可以好好相处?", "gloss": "Can we (or can't we) get along?", "audioKey": null },
    { "for": "不可", "text": "不可能。",           "gloss": "Impossible.",                     "audioKey": null }
  ]
}
```

### Node references (`between`, `for`)

Resolved to node ids with minimal sugar, so authoring stays terse but unambiguous:

| written              | resolves to        | rule |
|----------------------|--------------------|------|
| `"人"` (bare glyph)  | `g:人`             | single CJK codepoint → glyph node |
| `"可不"` + `audience`| `w:可不@cn`        | multi-char surface → word node in that audience |
| `"g:入"` / `"w:不可@cn"` / `"e:馬謖"` | itself | explicit id passes through |

`build-graph` **validates every ref resolves to a node that exists** (real glyph,
frontier stub, word, or authored entity) — mirrors the `composition-roles.json`
validation that every declared pair hits a real edge. An unresolved ref is a hard
error (typo guard), not a silent drop.

### Symmetric, and n-ary

`confusable` is genuinely **undirected** (unlike `composes`/`variant`). Authored as
an unordered `between` set; build-graph normalizes to deterministic output. For a
cluster of >2 (己/已/巳) it emits the **pairwise clique**, every emitted edge
carrying a shared `cluster` id so the UI can group the set:

```jsonc
// emitted into edges.json (from/to sorted for stable dedup; symmetric flag tells the renderer to draw it undirected)
{ "from": "w:不可@cn", "to": "w:可不@cn", "kind": "confusable",
  "symmetric": true, "cluster": "cf:1", "basis": "phonetic", "source": "authored" }
```

- `symmetric: true` — renderer draws one undirected link; traversal treats it both ways.
- `cluster` — ties clique edges + their `examples` back to one authored entry.
- `source: "authored"` — provenance tag (see below).

### Grounding (`examples`)

The pedagogical half, per memory `confusable-pair-anchoring`: each endpoint gets
≥1 example sentence so the two meanings anchor to **distinct contexts from the
start** (Hebbian; cf. `referent-anchoring-associative`). `audioKey` reuses the
content-keyed audio-bank convention (memory `phonetics-architecture`): a key into
a sentence bank, or `null` for now. When null, the play button hides — exactly the
existing "no reading → no play button" behaviour (commit 09174a9). So we can ship
text+gloss today and wire sentence audio later without a schema change.

`examples` live on the authored entry (attached to the cluster), **not** on the
output edges — they're grounding for the *set*, surfaced by the confusable panel,
not a property of any single pairwise link.

## Provenance (runtime tag, not a boundary mechanism)

`source:"authored"` distinguishes these from derived edges at *runtime* — for a
merged-graph consumer that wants to filter by origin. It is **not** the mechanism
that keeps proprietary content out of the product. Per `greenfield-independence-goal`,
that boundary is **which files ship**, not a strip pass over inline tags: the engine
stays program-agnostic and WK/PD overlay files simply never enter the product repo.
Authored edges are first-party core content — they're on the ship side regardless of
the tag; the tag is only for legibility and origin-filtering once everything is merged
into `edges.json`.

## Where it sits in the edge taxonomy

```
STRUCTURAL (derived, acyclic, hard)   composes            → SRS composite gates
DERIVED    (from bindings)            denotes · variant
AUTHORED   (enrichment, cyclic, soft) confusable  ← NEW   → sequencing + contrast render, NOT a gate
```

`confusable` is the first named member of the **enrichment** family sketched as
`assoc` edges under *Future exploration* in `content-graph-schema.md`: cyclic-OK,
non-gating, feeding *soft* priority (co-schedule the pair) rather than a hard
prerequisite unlock. It informs the scheduler and the renderer; it never blocks.

## Build-graph changes (scope)

1. `load_authored()` reader + `data/authored.json` (absent file → no-op, like `words.json`).
2. Ref resolver + validator (bare-glyph / word-surface+audience / explicit id).
3. Clique expansion → symmetric `confusable` edges with `cluster` ids.
4. Optional authored `entity` nodes.
5. Extend the edge-count print line; the round-trip block is unchanged (authored edges are additive).

Renderer (`graph.js`) + any confusable panel: separate follow-up, not in this pass.

## First entries to hand-author (v1)

- 可不 / 不可 (`basis: phonetic`) — the motivating pair, with the two example sentences above.
- Candidate look-alikes for a `basis: visual` sanity check: 人/入, 己/已/巳 (three-way clique test).

## Deferred (NOT built now)

- Sentence audio bank + `audioKey` synthesis (gen-audio sentence module).
- Confusable-aware **sequencing rule** (co-schedule a cluster) — belongs with SRS cadence, out of scope here.
- Authored `entity` nodes in anger (the Three-Kingdoms corpus) — schema reserves the slot; no content yet.
- A general authored `see-also` / weighted `assoc` kind — same file, same join, when it earns its keep.
