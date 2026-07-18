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
| `/glyph/` | glyph dossier: one node's shape, parts, appears-in, confusables, meaning, assets; hash-addressable | **keep — core probe; fold renderer** |
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

**The target.** One canonical card shape, one `node + bindings → card` projection, one
HanziWriter lifecycle. Every surface *consumes* the shape; none rebuilds it.

```
card = {
  glyph, tag,                       // identity ('char' | 'comp' | 'stroke')
  hw, image?, kx?,                  // media + Kangxi №
  cn: { name, reading, gloss, extra, appearsIn? },   // reading views (per language)
  jp: { name, reading, gloss, extra, appearsIn? },
  wk?, kanji?, pd?, pdc?,           // program-tier annotations (see glossary)
  referents?[],                     // meaning: label + images
  audioKeys,                        // content-keyed clip ids (cn/jp + example)
}
```

- **Consumers:** `renderCard` (full tile), `jpFocusCard` (JP projection of the same
  shape), the /glyph/ dossier, /graph/ ego view. Each is a *view function* over `card`,
  not a parallel builder.
- **Projection:** move `gdView`/`jpFocusCard`'s node→card logic into one
  `shared/card.js` (`cardFromNode(node, bindings)`), so it can't drift from
  `symbols_io.to_card`. (Ideally the two agree by construction — same field set.)
- **HanziWriter:** one `hanzi.js` owning create/observe/pause/resume + the loop, used by
  both grid tiles and the JP focus pane (kills the duplicate lifecycle and the leak class).

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

## The bespoke-lesson decision (xi-zhuang / yan-se)

The one genuine fork this spec surfaces — these are real content on an old, divergent
template. Two coherent paths:

- **(A) Migrate to substrate** — express their vocab as words/glyphs in the graph and
  render via the shared card/lesson renderer. Most consistent; but their *narrative*
  layout (themed sections, SVG cover, 浅/深 pattern) isn't a plain card grid, so it needs
  a "lesson" template, not just cards3.
- **(B) Keep bespoke, adopt the design layer** — leave the hand-authored narrative, but
  pull styling from shared component CSS and audio from the standard path. Cheapest;
  preserves their character; accepts they stay one-offs.

Recommendation: **(B) now, (A) if/when a lesson template earns its keep** — matches
bootstrap. Don't rewrite working lessons to prove a point.

## Roadmap (ordered, incremental)

1. **Card consolidation** — `shared/card.js` (`cardFromNode`) + `shared/hanzi.js` (one
   lifecycle); point /graph/, /glyph/, /jp/ at them. *Kills the drift class; no visual change.*
2. **Cognate panel** — the open enrichment slot.
3. **Component CSS layer** — extract shared card/tile/panel/vcard classes.
4. **Bespoke lessons** — path (B): reskin xi-zhuang/yan-se onto the component layer.
5. **Prune** — move /ui/ experiments out; resolve /radicals/ tombstone.
6. **Landing, graph-driven** — live counts + composes-derived links on `/` (see
   `landing-interlinking-static`, `graph-pivot-direction`).

Nothing here is a big-bang rewrite: each step ships independently and leaves the site working.
