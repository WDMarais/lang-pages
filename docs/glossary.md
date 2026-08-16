# Glossary — what the words mean

The controlled vocabulary of the content graph: every `kind`, `type`, `basis`, and
`role` value, what it denotes, and the distinctions that are easy to conflate. This is
the source of truth for terminology; the deeper design rationale lives in
[content-graph-schema.md](content-graph-schema.md) and
[authored-edges.md](authored-edges.md).

> Rule of thumb for adding a value: a **new `kind`** is a new *relationship*; a new
> **`type`/`basis`/`role`** is a new *flavour* of an existing one. Reach for the widest
> field that still says what you mean.

## Containers

The data-layer graph is three generated files (from `data/symbols/*.json` via
`build-graph.py`):

| file | shape |
|------|-------|
| `data/nodes.json` | `{ "nodes": [ … ] }` |
| `data/edges.json` | `{ "edges": [ … ], "clusters": [ … ] }` — links + the n-ary authored payload |
| `data/bindings.json` | `{ "bindings": [ … ] }` — per-language (cn/jp) card data for a glyph |

## Node — a thing in the graph

`node.kind`:

| kind | is | key fields |
|------|----|-----------|
| `glyph` | one written character/component/stroke | `glyph`, `tier`, `variants?`, audio keys, `frontier?` |
| `word` | a lexeme (a vocabulary item), audience-tagged | `glyph` (surface), `audience`, `reading`, `gloss`, `okurigana?` |
| `referent` | a language-neutral **meaning** that glyphs/words point at | `label` |
| `entity` | an authored non-linguistic node (e.g. a person), reserved | `label` |

- **`frontier`** — a *field* (`true`), **not** a kind: a glyph node referenced as a part
  but not yet carded (a stub). It becomes a full node when a symbol file is authored.
- **`tier`** — a glyph's level in the substrate: `stroke` ⊂ `component` ⊂ `char`.

## Core vs interface — node (shared) + binding (per-language)

The data layer already splits a glyph into a **language-neutral core** and a
**per-language interface**, and the consumer (card) projection keeps the same seam:

- **core** (a `node`) — the shared facts: `glyph`, `tier`, `animated`/`image`/`kx`, and the
  `referent`s it denotes (the *meaning*, language-neutral).
- **interface** (a `binding`, one per `cn`/`jp`) — that language's rendering: `name`,
  `reading`, `gloss`, `extra`, program annotations, vocabulary, audio keys (content-keyed
  by *sound*, hence per-language).

The general schema carries only the core; a language's fields never enter it. The
**referent** is the shared meaning and a binding's **`gloss`** is one language's rendering
of it — which is why `gloss` is per-language but `referent` is core. A renderer *selects
interfaces over one core* (the comparison card takes both bindings; the JP focus card takes
JP). **Strict at ingest, tolerant at render:** authoring validates hard (`check-source.py`),
but a renderer quietly ignores a binding field it doesn't yet handle (additive enrichment),
so new per-language data lands without touching the core.

## Edge — a relationship between two nodes

`edge.kind`, in three families:

| kind | family | direction | gates SRS? | extra fields |
|------|--------|-----------|-----------|--------------|
| `composes` | **structural** | directed (part → whole) | **yes** (hard prereq) | `role` |
| `denotes` | **derived** | directed (glyph/word → referent) | no | — |
| `variant` | **derived** | directed (twin → canonical) | no | — |
| `association` | **authored** | symmetric | no (soft) | `type`, `basis`, `cluster`, `source`, `symmetric` |

### `composes.role` — the part's *function in the whole*

| role | the part contributes | example |
|------|----------------------|---------|
| `semantic` | meaning | 氵 in 海 (water) |
| `phonetic` | sound | 每 in 海 (méi → hǎi) |
| `form` | neither — just shape/structure | *(defined; unused so far)* |

### `association.type` — the *relation*, and `.basis` — the *reason*

All authored enrichment edges share the one `association` kind. `type` says which
relation; `basis` (a render hint) says why. **The two are orthogonal** — a pair can carry
either, both, or neither (カ/力 confusable-only; 東/东 cognate-only; 西/襾 both).

| type | is | intent | `basis` ∈ |
|------|----|--------|-----------|
| `confusable` | look/sound/mean **alike but distinct** | a **warning** ("don't mix up") | `visual` · `phonetic` · `semantic` |
| `cognate` | share an **origin** | **enrichment** ("same source") | `historical` · `etymological` · `orthographic` |

basis values:

- **confusable** — `visual` (look alike: 己/已/巳), `phonetic` (sound alike: 可不/不可),
  `semantic` (meanings blur).
- **cognate** — `historical` (one radical family over time: 西/襾), `etymological` (shared
  root word), `orthographic` (two written forms of one slot: 毋/母 under radical 80).

Authored `association` edges are **symmetric** and **n-ary**: a set of ≥2 members
(己/已/巳 is one three-way, not three pairs). The shared payload (`basis`/`note`/
`examples`) is stored once in a **cluster** record (`edges.json["clusters"]`, id `cf:N`
for confusable / `cg:N` for cognate); the edges are the pairwise clique pointing back at
it. `source:"authored"` tags provenance.

## The three "similar glyphs" relations — do not conflate

The single most confusable corner of the vocabulary itself:

| relation | same referent? | one node or two? | example |
|----------|:---:|------|---------|
| **`variant`** (fold) | **yes** (required) | **one** — twin folds onto canonical | 厶←ム, 𠂇←ナ, 襾←覀 |
| **`association`/`cognate`** | no | two, linked | 西/襾 (west vs cover) |
| **`association`/`confusable`** | no | two, linked | 己/已/巳 |

- A **`variant`** is same-shape **and** same-meaning — the twin *is* the canonical, kept
  as a badge to preserve a program binding. **Invariant (gated by `check-source.py`):** a
  variant twin must denote the *same referent* as its canonical; if it diverges, it is a
  cognate/confusable, not a variant. (This is what caught the 西/覀/襾 mis-fold.)
- **Hard vs soft:** only `composes` gates the SRS scheduler (you can't learn 好 before 女
  and 子). `association` edges are soft — they inform *sequencing* and *contrast rendering*
  (co-teach a confusable set; note a cognate), never a prerequisite lock.

## Program vocabulary (bindings)

A glyph's `programs[]` (WaniKani, Pandanese) project onto per-language bindings. Not a
graph relation — see `symbols_io.PROGRAM_TIERS`. Relevant terms:

- **`kind`** on a program item (distinct from node/edge kind): `meaning` (the name is the
  real meaning — render green) vs `mnemonic` (a memory-hook name, not the meaning — render
  red, cautioned).
- **`role`** on a program item (distinct from `composes.role`): `radical` / `kanji` /
  `character` — the tier the program teaches the glyph as.
