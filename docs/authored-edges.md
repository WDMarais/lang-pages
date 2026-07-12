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

`confusable` is genuinely **undirected** (unlike `composes`/`variant`) and genuinely
**n-ary** — 己/已/巳 is ONE three-way set, not three coincidental pairs. Authored as
an unordered `between` set of ≥2; build-graph splits that into two output pieces:

```jsonc
// edges.json → "edges": the pairwise CLIQUE, slim (from/to sorted → order-independent, stable diffs)
{ "from": "g:己", "to": "g:已", "kind": "confusable", "symmetric": true, "cluster": "cf:1", "source": "authored" }
{ "from": "g:己", "to": "g:巳", "kind": "confusable", "symmetric": true, "cluster": "cf:1", "source": "authored" }
{ "from": "g:已", "to": "g:巳", "kind": "confusable", "symmetric": true, "cluster": "cf:1", "source": "authored" }

// edges.json → "clusters": the n-ary payload, stored ONCE
{ "id": "cf:1", "kind": "confusable", "members": ["g:己","g:已","g:巳"],
  "basis": "visual", "note": "开口己、半口已、闭口巳 …", "examples": [ … ] }
```

- `symmetric: true` — renderer draws one undirected link; traversal treats it both ways.
- `cluster` — every clique link points back at the one cluster record.
- `source: "authored"` — provenance tag (see below).
- `"clusters"` is a **sibling key** of `"edges"`. Existing consumers (`graph.js`,
  `cardsJP.js`, `console.js`) read `.edges` as an array and are unaffected.

**Clique, not a star.** The alternative — reify the cluster as a node and emit
`member-of` edges — is arguably the more correct model for an n-ary relation, but it
forces the query a card actually asks ("what does 已 confuse with?") into a two-hop
traversal, and leaks a non-linguistic node into `nodes.json`. The clique keeps that a
one-hop edge filter; normalizing the payload into `clusters` gets the storage win
without paying the traversal cost.

### Grounding (`examples`)

The pedagogical half, per memory `confusable-pair-anchoring`: each member gets ≥1
example so the meanings anchor to **distinct contexts from the start** (Hebbian; cf.
`referent-anchoring-associative`). They ground the *set*, so they live on the cluster
record, not on any single pairwise link.

`audioKey` reuses the content-keyed audio-bank convention (memory
`phonetics-architecture`): a key into a sentence bank, or `null` for now. When null the
play button hides — exactly the existing "no reading → no play button" behaviour
(commit 09174a9). So text+gloss ships today and sentence audio wires in later with **no
schema change**.

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

## Shipped (v1)

Three entries, deliberately one of each shape:

| cluster | members | basis | shape |
|---------|---------|-------|-------|
| `cf:1` | 己 / 已 / 巳 | visual | glyph **triple** — 开口己、半口已、闭口巳 |
| `cf:2` | 人 / 入 | visual | glyph pair |
| `cf:3` | 可不 / 不可 | phonetic | **word** pair |

→ 5 confusable edges in 3 clusters. 己 was promoted from `form_only`; 已 and 巳 were
new symbols added to make the archetype real.

## Deferred (NOT built now)

- Sentence audio bank + `audioKey` synthesis (gen-audio sentence module).
- Confusable-aware **sequencing rule** (co-schedule a cluster) — belongs with SRS cadence, out of scope here.
- Authored `entity` nodes in anger (the Three-Kingdoms corpus) — schema reserves the slot; no content yet.
- A general authored `see-also` / weighted `assoc` kind — same file, same join, when it earns its keep.
