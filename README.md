# 中文学习 · lang-pages

A self-study Chinese reference and study substrate — a static, build-less site
that models the writing system as a clean, reusable content graph and projects it
into several browseable learning modules.

The primary target is **Mandarin / simplified Chinese**. Han script is modeled as
one neutral graph, with per-language *bindings* layered on top; Japanese appears
only as a secondary comparison layer on the foundational character cards.

## Goals

Four goals it serves at once — two outcomes, two about the craft:

- **Study aid.** Content is shaped to feed spaced-repetition study, not just to be read.
- **A clean content graph as the core artifact.** The structured, reusable data layer
  is a first-class goal in itself, not merely scaffolding for the pages. Views are
  disposable; the graph is not.
- **Faithful rendering.** High-quality stroke-order animation and audio — *leased*
  from existing projects (HanziWriter / Make-Me-a-Hanzi stroke data, edge-tts voices)
  rather than rebuilt. Own the curated structure; borrow the rendering-grade assets.
- **Practical payoff.** Foundational character work sits alongside situational,
  domain-specific vocabulary (colours, tailoring, scenes) aimed at real use.

## Modules

Foundational:

- **笔画 · strokes/** — the basic strokes, three views (中文 · 日本語 · Wanikani),
  with stroke-order animation and audio.
- **部件 · 单字 · radicals/** — components and single characters that double as
  radicals; Wanikani names split into real-meaning vs shape-mnemonic.
- **字形图 · graph/** — a current-glyph-centered local-graph view over the data
  layer (a compact tier ladder + a radial ego graph). The browse/lookup consumer
  of the content graph.

Situational vocabulary:

- **颜色 · yan-se/** — colour swatches with the 浅/深 modifier pattern.
- **西装定制 · xi-zhuang/** — fabric-market vocabulary (choosing fabric, measurement,
  alterations).
- **场景 · ui/scene-*.html** — shape × size × colour pickers that assemble compound
  descriptive phrases.

Reference:

- **组件库 · ui/** — design tokens, vocab cards, and interactive components.

## Data model

The canonical layer is a small content graph under `data/`:

- `nodes.json` — glyph / referent / frontier nodes (neutral Han script + meanings).
- `edges.json` — `composes` (part → whole) and `denotes` (glyph → meaning) edges.
- `bindings.json` — per-language surface data (`@cn`, `@jp`): name, readings, gloss,
  `appearsIn`, program (e.g. Wanikani/kanji facts).

The hand-authored card files (`radicals/radicals.json`, `strokes/strokes.json`) are
**projections** of this graph. `data/build-graph.py` builds the graph from the cards
and round-trips back to prove the two stay in sync. This graph is designed to be
consumed directly by external SRS/graph tooling, not just this site's UI.

## Rendering

Shared, dependency-light front end under `shared/`:

- `base.js` — page chrome, audio playback, and a small escaping `html`` `` tagged
  template (the whole templating layer; escapes interpolated data by default).
- `cards3.js` / `cards3.css` — the three-view (中文 · 日本語 · Wanikani) card renderer.
- `hanzi-data/` — self-hosted per-character stroke data (outlines + medians);
  `vendor/hanzi-writer.min.js` animates it via clip-path + `stroke-dashoffset`.

## Data tooling (`data/`)

- `build-graph.py` — cards → content graph (+ round-trip check).
- `fetch-decomp.py` — pulls character decomposition from a locally cached
  Make-Me-a-Hanzi dictionary.
- `gen-audio.py` — derives TTS text from the card JSON and generates audio via
  edge-tts (`radicals` / `strokes` / `xi-zhuang` / `all`, `--dry-run` supported).
- `shared/hanzi-data/fetch.py` — lifts stroke data into `shared/hanzi-data/`.

## Running

Pure static — serve the directory and open it:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000/`.

## License & provenance

- Site code: **MIT** (see `LICENSE`).
- Stroke data (`shared/hanzi-data/*.json`): **Arphic Public License**, derived from
  the Arphic PL UKai font via Make-Me-a-Hanzi. The APL notice travels with the data
  and its copyleft covers the glyph data only — see `shared/hanzi-data/LICENSE.md`.
- HanziWriter (`shared/vendor/hanzi-writer.min.js`): **MIT**.
