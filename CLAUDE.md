# lang-pages — agent guide

Knowledge-graph language-learning substrate. Read `docs/authoring.md` for the full
batch-ingest runbook and `docs/content-graph-schema.md` for the data model; this file
is the short list of things that are easy to get wrong.

## Source of truth & the build

- **Authored source:** `data/symbols/<glyph>.json` (one per glyph) and `data/words.json`
  (words). *Everything else is GENERATED* — `data/{nodes,edges,bindings}.json`,
  the `characters/` `kangxi/` `strokes/` card decks, and the `audio/` banks.
- **A glyph's parts are its authored `composes` field** — the glyph-level source of
  truth, read straight from the symbol by `build-graph.py`. There is no separate
  decomposition step (and no `decomposition.json`). MMAH is only an *authoring aid*:
  `python3 data/fetch-decomp.py <glyph>` suggests parts to paste into `composes`;
  the human value is authoritative and refines it (合 ← 𠆢 一 口, 広 ← 广 厶).
- **After ANY edit under `data/symbols/` or to `data/words.json`, run
  `python3 data/build.py`** (graph → pages → audio → check-source).
  `--no-audio` skips edge-tts.
- **The gate is `data/check-source.py`** (build.py runs it last). It must report
  `0 error(s)` before you commit — it validates `composes` (single glyphs, no
  self-loop), dangling parts, and authoring slips that the round-trip proof would
  otherwise pass straight through.

## Adding a frontier glyph vs. a word

- **New glyph:** write `data/symbols/<glyph>.json` (fill `composes` — `python3 data/fetch-decomp.py <glyph>`
  suggests parts), then `python3 shared/hanzi-data/fetch.py <glyph>` for `animated:true`
  stroke data (or `shared/hanzi-data/assemble.py` to lift + place parts for glyphs the
  CDN lacks, e.g. JP shinjitai), then `python3 data/build.py`.
- **Word reusing existing glyphs:** append to `data/words.json`, then `python3 data/build.py`.
  Before minting a `denotes` referent, hunt for an existing one to rejoin (see graph-api below).

## Git

- **Stage explicit paths only — never `git add -A`.** Commit generated outputs *together
  with* the source that produced them (deploy is build-free).
- **Commits and pushes are the user's explicit call, every time.** Force-push only when
  asked, and prefer `--force-with-lease`.

## Local tooling

- **Dev server already runs on :8765** — don't start a duplicate.
- **graph-api** (GraphQL over the graph, for rejoin-hunting): `npm --prefix graph-api run seed`
  then `npm --prefix graph-api run start` (:4000). Query `referents(near:"…"){ id label denotedBy{ id glyph } }`
  to find an existing referent before minting. It's a *lagging* projection rebuilt from the
  committed JSON — re-seed after each build. Config in `~/.lang-pages/.env`
  (DB `lang_pages_graph`, psql peer auth). NB: the `postgres` MCP tool points at a *different*
  (Odoo) database, not this one.
