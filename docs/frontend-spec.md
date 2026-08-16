# Front-end spec — what we support, and the shape to converge on

> Status: **draft / target**. A map of every page, one render contract to converge on,
> and the keep/cut/merge calls — so cleanup is a coherent push toward a stated target
> rather than a blind rewrite. Design stance unchanged: **bootstrap, don't boil the
> ocean** — consolidate the one thing that drifts, migrate pages incrementally, keep
> the working animation/audio/graph. Vocabulary: [glossary.md](glossary.md).

## The site in one sentence

A static, multi-page 中文/日本語 study site: **study decks** (character/radical/stroke
cards), **phonetics banks** (tones, zhuyin, kana), **bespoke lessons** (themed vocab),
and a **content-graph probe/console** for authoring — all over one generated substrate
(`data/*.json` from `data/symbols/`), sharing one design vocabulary.

## Page inventory

Five families. "Decision" is the recommendation this spec proposes.

### 1. Study decks — the cards3 cluster (CORE, the spine)
Shared renderer `shared/cards3.js` + `cards3.css`; each page is `<div id="cards"
data-src="X.json">` + a local built JSON. Same template, differ only by data + a layout flag.

| page | shows | data | decision |
|------|-------|------|----------|
| `/characters/` | standalone/composite chars, 3-view (中·日·WK) | `characters.json` | **keep** |
| `/kangxi/` | the 214 Kangxi radicals (cards + grey stubs) | `kangxi.json` | **keep** |
| `/strokes/` | the 8 basic strokes, animated | `strokes.json` | **keep** |
| `/jp/` | JP-first focus view (音/訓/語彙) | graph substrate | **keep — fold renderer** (see contract) |

### 2. Content-graph cluster — probe + console (CORE tooling / EXPERIMENT)
`shared/graphdata.js` over `nodes/edges/bindings.json`, + cards3 + confusable panel.

| page | shows | decision |
|------|-------|----------|
| `/glyph/` | glyph dossier: one node's shape, parts, appears-in, confusables, referent (所指), assets; hash-addressable | **keep — core probe; fold renderer** |
| `/graph/` | author/debug console: coverage, invariants, frontier worklist, ego view | **keep as tooling** — explicitly "seams showing"; not a study surface, don't polish as one |

### 3. Phonetics banks (CORE)
Enumerable sound boards; tap to hear. Own tiny renderer fetching a local `data.json`
built by a `data/build-*.py`.

| page | shows | data | decision |
|------|-------|------|----------|
| `/tones/` | 4 tones + neutral, SVG pitch-contours | bespoke SVG (no data file) | **keep** |
| `/zhuyin/` | bopomofo chart + syllable bank | `zhuyin/data.json` | **keep** |
| `/kana/` | hiragana/katakana mora bank | `kana/data.json` | **keep** |

`kana` and `zhuyin` are structural twins (same mini-renderer pattern); `tones` is the
hand-authored cousin. Candidate for a shared "bank" helper later — low priority (they're small and stable).

### 4. Bespoke lessons (CORE content, one-off — the real open question)
The oldest pages, predating cards3; own vcard schema, hand-authored.

| page | shows | decision |
|------|-------|----------|
| `/xi-zhuang/` | tailoring/fabric-market vocab; own `cards.json` renderer (`xi-zhuang.js`) | **decide** (see below) |
| `/yan-se/` | colours lesson; fully inline vcards, no own JS | **decide** (see below) |

### 5. Static / utility (keep small, prune experiments)

| page | is | decision |
|------|----|----------|
| `/` (root) | site TOC / landing (static anchor grid) | **keep**; make graph-driven later (live counts, composes links) — see `landing-interlinking-static` |
| `/credits/` | referent-image attribution (fetches `referents.json`) | **keep** (utility) |
| `/ui/` | component kitchen-sink + design tokens | **keep as dev reference**; **move** the stray `scene-demo.html`/`scene-grid.html`/`fit-slider.html` demos into a clearly-marked `/ui/experiments/` or delete |
| `/radicals/` | retired redirect → `/kangxi/` | **keep as tombstone** (or delete once no inbound links) |

## The one thing to consolidate: the card contract

**The problem.** "A glyph card" is projected in **three** places from three inputs:
- `cards3.renderCard(c)` ← the built page JSON (`symbols_io.to_card`, Python)
- `graphdata.gdView(b)` ← a binding, for /graph/ + /glyph/ (JS reimplementation)
- `cardsJP.jpFocusCard(…)` ← graph node + binding, JP view (JS reimplementation)

…plus **two** HanziWriter lifecycles (`cards3.initHanzi` + `cardsJP.jpFocusHanzi`). Adding
a field to "a card" means threading it through three renderers; the `/jp/` writer leak
happened precisely because cardsJP reimplemented cards3's init.

**The target: a language-neutral core + a per-language interface over it.** The general
`card` schema carries only what every language shares; each language's fields ride a
*binding* layered on top. This mirrors the data layer, where a `node` (core) already holds
the shared facts and a `binding` holds the per-language card data — the consumer
projection keeps the same seam.

```
core = {                     // language-neutral — the general contract
  glyph, tag,                // identity ('char' | 'comp' | 'stroke')
  animated, image?, kx?,     // media + Kangxi №
  referents?[],              // meaning (language-neutral): label + images
}
binding[lang] = {            // ONE per language — the interface OVER the core
  name, reading, gloss, extra, appearsIn?,   // this language's rendering of the meaning
  programs?,                 // wk / kanji (jp side) · pd / pdc (cn side)
  vocab?,                    // 語彙 — the words this glyph composes into
  audioKeys,                 // content-keyed by SOUND, so per-language
}
```

- **The core never names a language.** `cn`/`jp`-specific fields live in bindings, never in
  the general schema. The **referent** is the shared meaning; a binding's `gloss` is just
  *that language's* rendering of it — which is exactly why `gloss` is per-language while
  `referents` are core.
- **Renderers select interfaces over one core.** The comparison card (cards3) renders
  core + *both* bindings side by side; the JP focus card (cardsJP) renders core + the *JP*
  binding, JP-forward. Neither widens a shared schema; each asks for the interfaces it draws.
- **Strict at ingest, tolerant at render.** A binding may carry a field a given renderer
  doesn't handle yet (a future JP pitch-accent); the renderer quietly ignores it and
  nothing breaks (additive / monotonic enrichment). The guard against that hiding *typos*
  is the authoring layer, which stays strict — `check-source.py` / `build-graph.py`
  hard-error on a bad ref. Forgiving at draw, unforgiving at ingest.
- **One graph-read layer.** `graphdata.loadGraph()` is the single read model (core +
  bindings + vocab + referents). `cardFromNode` projects the core; `gdView` / `jpFocusCard`
  are interface *views* over it. `/jp/` consumes `loadGraph()` too, instead of hand-rolling
  its own graph fetch+index (the last duplicated projection).
- **HanziWriter:** one `hzCreate()` owns the create contract (colours, speed, APL loader);
  the grid (IO-culled, many) and the JP focus pane (single-replace) are two lifecycles over
  it that can no longer drift on options — which is where the `/jp/` leak was born.

## Panels (over-the-card enrichment)

Rendered above/beside a card from authored `association` clusters (see glossary):

| panel | source | status |
|-------|--------|--------|
| **confusable** (易混 / look-alikes) | `confusOf` (type=confusable) | **exists** — `shared/confusable.js`, visual-first member tiles + examples + audio |
| **cognate** (同族 / shared origin) | `cognateOf` (type=cognate) | **TODO** — the open slot; enrichment styling (not a 易混 warning); data indexed + ready |

The cognate panel is the natural next build: same member-tile machinery as confusable,
different framing (origin note, not "don't confuse").

## Design-system layer

`base.css` already defines **10 shared tokens** (`--navy --gold --green --red --ink
--cream --muted --border --scale …`) used across all 15 pages — the palette is *not*
fragmented. The gap is a **component layer** between tokens and page CSS:

```
tokens (base.css)  →  components (card / tile / panel / vcard / bank)  →  page css
```

Today `cards3.css`, `cardsJP.css`, `confusable.css` are de-facto component CSS, but the
bespoke lessons re-author their own vcard styling. Target: extract shared component
classes so `xi-zhuang`/`yan-se` (and future lessons) style from the same vocabulary.

## The bespoke-lesson decision (xi-zhuang / yan-se) — RESOLVED: path B

The one genuine fork this spec surfaces — these are real content on an old, divergent
template. Two coherent paths:

- **(A) Migrate to substrate** — express their vocab as words/glyphs in the graph and
  render via the shared card/lesson renderer. Most consistent; but their *narrative*
  layout (themed sections, SVG cover, 浅/深 pattern) isn't a plain card grid, so it needs
  a "lesson" template, not just cards3.
- **(B) Keep bespoke, adopt the design layer** — leave the hand-authored narrative, but
  pull styling from shared component CSS and audio from the standard path. Cheapest;
  preserves their character.

**Decision: (B) — and B is *not* a way-station to A.** The whole value of a bespoke
lesson page is the freedom to do *whatever the content wants* without first solving "how
does this fit the substrate template." Bolting a lesson to the substrate schema **at
ingestion time** would tax exactly the thing the escape hatch exists to protect. So
bespoke lessons are a **permanent first-class surface**, not a temporary state awaiting
migration.

What B buys and doesn't:
- **Does** share the *design layer* — component CSS + the standard audio path — so a
  bespoke page looks native and plays sound like everything else (roadmap step 4).
- **Does not** require the *data layer* — a lesson may stay fully hand-authored forever.

**Mining is an optional runbook, never a gate.** Pulling a lesson's vocab *into* the
substrate (so its glyphs/words join the graph, gain cards, get scheduled) is worthwhile
sometimes — but it's a **separate, after-the-fact, opt-in** operation, applied to *this*
page or *any* externally-fed content when it earns its keep. That belongs in a
`docs/mining-runbook.md` (strategy for "how to distil a lesson/handout into symbols +
words + edges"), **not** in the ingestion path. Freedom to author first, mechanize later.

## Roadmap (ordered, incremental)

1. **Card consolidation** — ✅ DONE, two moves. (1a) one `hzCreate()` create contract in
   `cards3.js` for both HanziWriter lifecycles. (1b) `/jp/` consumes `graphdata.loadGraph()`
   (extended with `vocabOf`/`refOf`) instead of its own fetch+index — one read layer, core +
   per-language interface. *Killed the drift class; no visual change.* Not yet built: a
   `langView(core, binding)` helper to fully collapse `gdView`/`jpFocusCard` into one view
   function — deferred until a third consumer makes it pay.
2. **Cognate panel** — the open enrichment slot.
3. **Component CSS layer** — extract shared card/tile/panel/vcard classes.
4. **Bespoke lessons** — path (B): reskin xi-zhuang/yan-se onto the component layer +
   standard audio. *Reskin only — no data-layer migration.* Distilling a lesson into the
   substrate is a separate opt-in `docs/mining-runbook.md`, not part of this step.
5. **Prune** — move /ui/ experiments out; resolve /radicals/ tombstone.
6. **Landing, graph-driven** — live counts + composes-derived links on `/` (see
   `landing-interlinking-static`, `graph-pivot-direction`).

Nothing here is a big-bang rewrite: each step ships independently and leaves the site working.
