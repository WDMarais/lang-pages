# lang-pages — agent guide

Knowledge-graph language-learning substrate. Read `docs/authoring.md` for the full
batch-ingest runbook and `docs/content-graph-schema.md` for the data model; this file
is the short list of things that are easy to get wrong.

## Source of truth & the build

- **Authored source:** `data/symbols/<glyph>.json` (one per glyph) and `data/words.json`
  (words). *Everything else is GENERATED* — `data/{nodes,edges,bindings,decomposition}.json`,
  the `characters/` `kangxi/` `strokes/` card decks, and the `audio/` banks.
- **After ANY edit under `data/symbols/` or to `data/words.json`, run
  `python3 data/build.py`** (decomposition → graph → pages → audio → check-source).
  `--no-audio` skips edge-tts; `--refresh` re-pulls the MMAH dictionary.
- **Do not hand-run a single build step.** `build-graph.py` alone silently
  *under-integrates* a newly-added glyph: a glyph's parts come from `decomposition.json`,
  which only the decomposition step (`fetch-decomp.py`) refreshes. `data/build.py` runs
  the steps in the right order so this can't happen.
- **The gate is `data/check-source.py`** (build.py runs it last). It must report
  `0 error(s)` before you commit — it catches under-integrated symbols, dangling parts,
  and authoring slips that the round-trip proof would otherwise pass straight through.

## Adding a frontier glyph vs. a word

- **New glyph:** write `data/symbols/<glyph>.json`, then `python3 shared/hanzi-data/fetch.py <glyph>`
  for `hw:true` stroke data, then `python3 data/build.py`.
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
