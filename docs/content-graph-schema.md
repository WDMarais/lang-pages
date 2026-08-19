# Content graph schema (draft)

> Status: **draft / proposal**. Defines the *data layer* — the canonical content
> graph that lang-pages renders and srs-tool schedules. No SRS cadence is wired
> here; this is the fact model only.
>
> Design stance: **bootstrap, don't boil the ocean.** Build a simple, explicit,
> easily-mechanizable core now (form + composition + per-language bindings);
> grow V2 off the concrete artifacts this produces. The richer "model meaning
> itself" ideas are recorded under *Future exploration* and deliberately NOT
> formalized in code yet.

## Three layers

```
DATA LAYER          canonical content graph — nodes + typed edges (the facts)
   │  projects to
   ├──▶ lang-pages   a render/authoring VIEW (the pages; radicals.json is a projection)
   └──▶ srs-tool     a CONSUMER — schedules concepts, owns review state, keyed by id
```

srs-tool scores **concepts (competencies), not cards**; surface content (glyph,
audio, image) stays here. See memory `srs-tool-data-model`.

## Substrate + bindings

The Han script is **language-neutral**: a glyph's shape, strokes, and composition
(木 = 一丨丿㇏; 林 = 木+木) are facts about the writing system, not about Chinese
or Japanese. Language-particular stuff (readings, meaning drift, usage, source
program) is a thin **binding** layer on top.

```
GLYPH NODE        neutral form (shape, strokes, composition)
   ▲  binds
   ├── CN binding   readings + gloss + Pandanese metadata
   └── JP binding   readings + gloss + WaniKani metadata
```

→ CN and JP are authored **independently**, sharing the script structure. "Build
up from WaniKani + Pandanese over time" = filling in each language's binding.
Where the *form itself* forks (学/學, 国/國) there are separate glyph nodes joined
by a `variant-of` edge, and each binding attaches to the variant it uses.

## Physical source of truth: `data/symbols/<glyph>.json`

The substrate is authored as **one file per glyph** — bare form + composition,
adopted wholesale from Unicode + Make-Me-a-Hanzi (custom only at the edges), plus
a **uniform `programs[]` instantiation list**. `role` / `source` / `lang` are
*fields on a uniform record*, never nesting keys, so the (role × program × lang)
cross-product never tangles and every projection is one linear pass. Native
CN/JP readings stay a fixed two-key `readings` map (the binding, not part of the
cross-product). `kangxi` tags radical-hood; `_spine.json` holds the editorial
order.

```
data/symbols/*.json ──┬─ build-pages.py ─▶ radicals.json · strokes.json · characters.json
                      └─ build-graph.py ─▶ nodes · bindings · edges  (round-trip proven)
```

Nothing about a glyph's *page* is stored on the atom — membership is a rule
(`symbols_io.on_radicals` / `on_characters` / `on_strokes`), so 泉/線 (composite
chars no program teaches as radicals, not Kangxi) fall off `/radicals/` and
surface on `/characters/` without being re-filed. The card files stay committed
(build-free deploy) but are generated; edit the symbols, never the cards.

## Edges vs facets

Most "associated concepts" are **neighbouring nodes (edges)**, not **facets**:
strokes / components / examples are *other nodes*; only the scored competencies
are facets. Keeping them apart is what stops the schema exploding.

## Node

```jsonc
// glyph node — neutral form, what lang-pages renders
{
  "id": "g:木",
  "kind": "glyph",
  "glyph": "木",
  "tier": "char",                 // stroke | component | char | word
  "media": { "animated": true, "image": "" },
  "tags": ["nature", "kangxi:75"]
}
```

## Binding (per language)

```jsonc
{ "id": "b:木@cn", "glyph_id": "g:木", "lang": "cn",
  "readings": ["mù"], "gloss": "tree; wood",
  "program": { "source": "pandanese" } }                 // filled as we add Pandanese

{ "id": "b:木@jp", "glyph_id": "g:木", "lang": "jp",
  "readings": { "on": ["モク","ボク"], "kun": ["き"] }, "gloss": "tree; wood",
  "program": { "source": "wanikani", "name": "Tree", "kind": "meaning", "level": 1 } }
```

`program.kind` = `meaning | mnemonic` (the transfers-vs-shape-only distinction) now
lives where it belongs: on the language binding that asserts it.

WaniKani ships **radical and kanji as separate items** on the same glyph. The
program's top-level fields describe the *radical*; `program.kanji` (added when the
kanji unlocks) describes the *kanji* — its real meaning plus on/kun reading:

```jsonc
"program": { "source": "wanikani",
  "name": "Big", "kind": "meaning", "level": 1,                    // radical item
  "kanji": { "name": "Big", "readings": ["ダイ","タイ"], "on": true, "level": 1 } }  // kanji item
```

`kanji.readings` is a **list** (mirrors the binding's `readings`) — a kanji often
has two on'yomi (大 → ダイ・タイ, 力 → リョク・リキ). They diverge from the radical
exactly at shape-mnemonic radicals: 八 is radical **Fins** (`mnemonic`, no reading)
but kanji **Eight** (real meaning, ハチ). Two items, never merged — so the
non-mapping radical mnemonic and the real kanji meaning coexist instead of one
overwriting the other. `kanji.on` = true → on'yomi (rendered katakana), else kun.
A glyph can carry a kanji with **no** radical (三 = kanji Three, no WK radical):
`program` then holds only `source` + `kanji`.
The lang-pages projection **collapses both onto one card** (radical + kanji stacked
in the WaniKani column); srs-tool keeps them as two concepts joined by an unlock
edge (radical → kanji). Vocabulary will land the same way later (`program.vocab`).

## Facets (= schedulable concepts)

Bounded, and split by where they live:

| level         | facets               | concept id form     |
|---------------|----------------------|---------------------|
| script (node) | `recognize`, `produce` | `木/recognize`     |
| binding       | `read`, `mean`       | `木@jp/read`        |

`produce` is scored against the HanziWriter median data (stroke order); `read`
against the binding's `readings`; `mean` against its `gloss`. CN/JP reading & meaning
split for free because they're binding-level. Tier tunes which facets exist
(strokes/components: `recognize` only; chars: all four).

`type_id` for every facet of a glyph = a **singleton type** `t:木` — the bridge to
srs-tool's type-based slots (see Projection).

## Edges (built now)

```jsonc
{ "from": "g:一", "to": "g:木", "kind": "composes" }                     // part → whole, ACYCLIC
{ "from": "g:扌", "to": "g:打", "kind": "composes", "role": "semantic" } // typed: 义符
{ "from": "g:丁", "to": "g:打", "kind": "composes", "role": "phonetic" } // typed: 声符
{ "from": "g:木", "to": "g:林", "kind": "composes" }                     // 木's example (reverse traversal)
{ "from": "g:學", "to": "g:学", "kind": "variant-of" }                   // form fork
{ "from": "g:木", "to": "r:tree", "kind": "denotes" }                    // → bare referent LABEL stub
```

- **`composes`** — the resolution ladder; acyclic (a part is always "smaller"). Maps
  to srs-tool composite slots. Reverse traversal gives a glyph's examples.
  - **`role`** *(optional)* — the part's FUNCTIONAL role in this specific whole:
    `semantic` (义符, contributes meaning), `phonetic` (声符, contributes sound), or
    `form` (记号, shape-only residue incl. stroke-level parts). Absent = not yet
    typed. Per-EDGE, not per-node (丁 is phonetic in 打 but can be semantic elsewhere).
    Lets the SRS scheduler propagate credit by channel; `form` transfers nothing.
    Source of truth is the hand-curated `data/composition-roles.json` overlay
    (WHAT each part does — kept separate from the symbol's `composes`, WHICH parts);
    `build-graph.py` joins it onto the composition edges and validates the vocabulary
    + that each entry hits a real edge.
- **`variant-of`** — links divergent forms of the same character.
- **`denotes`** — glyph/word → referent. For now the referent is just `{ "id":"r:tree",
  "label":"tree" }`, a plain handle, and the `/glyph/` 所指 row renders that label as a
  placeholder. **Direction:** the referent is meant to be anchored by *sense-data* — an
  image, a sound, a motion — not the label, which is only a gloss handle ("a picture and
  sound of an elephant IS the referent; 'a large grey animal' is a description of one").
  The sense-data overlay is `data/referents.json`; a composite referent (orchestra =
  players + instruments + emergent sound) decomposes the same way the glyph graph does,
  one layer up. (Graded/property + composite referents → Future exploration.)

## Worked cluster: 木

```jsonc
// nodes
{ "id":"g:木","kind":"glyph","glyph":"木","tier":"char","media":{"animated":true} }
{ "id":"g:林","kind":"glyph","glyph":"林","tier":"char","media":{"animated":true} }
{ "id":"g:一","kind":"glyph","glyph":"一","tier":"stroke" }
{ "id":"g:丨","kind":"glyph","glyph":"丨","tier":"stroke" }
{ "id":"g:丿","kind":"glyph","glyph":"丿","tier":"stroke" }
{ "id":"g:㇏","kind":"glyph","glyph":"㇏","tier":"stroke" }
{ "id":"r:tree","label":"tree" }

// bindings
{ "id":"b:木@cn","glyph_id":"g:木","lang":"cn","readings":["mù"],"gloss":"tree; wood" }
{ "id":"b:木@jp","glyph_id":"g:木","lang":"jp",
  "readings":{"on":["モク","ボク"],"kun":["き"]},"gloss":"tree; wood",
  "program":{"source":"wanikani","name":"Tree","kind":"meaning","level":1} }

// edges
{ "from":"g:一","to":"g:木","kind":"composes" }
{ "from":"g:丨","to":"g:木","kind":"composes" }
{ "from":"g:丿","to":"g:木","kind":"composes" }
{ "from":"g:㇏","to":"g:木","kind":"composes" }
{ "from":"g:木","to":"g:林","kind":"composes" }
{ "from":"g:木","to":"r:tree","kind":"denotes" }

// facets: 木/recognize, 木/produce, 木@cn/read, 木@cn/mean, 木@jp/read, 木@jp/mean
```

## Projection → srs-tool

```jsonc
// each facet → AtomicConceptDef, all sharing the glyph's singleton type
{ "id":"木@jp/mean", "type_id":"t:木", "name":"木 — JP meaning: tree" }
{ "id":"木/produce", "type_id":"t:木", "name":"木 — stroke production" }
// composition gate → CompositeConceptDef over the PART types
{ "id":"comp:木", "name":"木 (composition)",
  "required_slots":[
    {"concept_type_id":"t:一","min_count":1},
    {"concept_type_id":"t:丨","min_count":1},
    {"concept_type_id":"t:丿","min_count":1},
    {"concept_type_id":"t:㇏","min_count":1}
  ] }
```

**Open mapping question (deferred with cadence):** a glyph is both schedulable
(atomic facets) and a composition gate (composite over parts); srs-tool's composite
unlocks the composite itself, not "these atomics." Wiring "gate 木's facets on its
strokes" needs a convention or a small srs-tool change. Out of scope until cadence.

## Projection → lang-pages (radicals.json falls out)

A radical card = a `tier ∈ {component, char}` node + its bindings + its **forward
`composes` edge** as the `例` example:

```
g:木 ──composes──▶ g:林     ⇒   木 card, 例 = 林
g:力 ──composes──▶ g:男     ⇒   力 card, 例 = 男
```

So `radicals.json` becomes a *query* over the graph, not hand-authored content.

## Future exploration (recorded, NOT built now)

Interesting; revisit as V2 off the concrete artifacts above. Deliberately not
formalized in code yet — bias to easily-mechanizable bootstrapping over a
monolithic "optimize everything" mechanism.

- **Graded / property referents** — `r:tree` as a property cluster; things *have*
  treeness to a degree (一棵树 0.9, 森林 0.5). Prototype/feature semantics.
- **`assoc` enrichment edges** — weighted, cyclic referent↔referent (红↔火↔血).
- **Spreading-activation unlock** — soft priority instead of hard gates; encounter
  any node → propagate priority along edges both ways (backfill via `composes`
  upstream, enrichment via `assoc`). Honors random/out-of-order discovery. (srs-tool's
  own predecessor-boost is also future work.)
- **Corpus-derived weights** — learn edge weights from example-sentence
  co-occurrence rather than hand-setting.
- **External KB seed** — ConceptNet / WordNet / Wikidata as a referent backbone.

## Deferred (mechanics, not philosophy)

- SRS cadence / scheduling (srs-tool's job).
- `word` tier and multi-char vocabulary.
- The atomic-vs-composite-same-glyph mapping (open question above).
```
