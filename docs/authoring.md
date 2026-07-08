# Authoring & Batch-Ingest Runbook

How content gets into lang-pages: what you hand-author, which scripts project it
into the graph and the pages, and in what order. Companion to
[content-graph-schema.md](content-graph-schema.md) (the *shape* of the data);
this doc is the *process*.

> Status: **validated by one real ingest (2026-07-08)** — the 止/川/子/人口/丆 batch
> was run end to end and the steps corrected against what actually happened. The one
> remaining **⟨verify-on-ingest⟩** marker is the audio-homing step (7), only dry-run
> so far. See *Known debt* at the bottom.

---

## The stance

`data/symbols/<glyph>.json` is the **single source of truth**. Everything else —
the page card files, the content graph, the audio — is a **projection** of it, and
is *generated* (but kept committed, so deploy stays build-free). You never
hand-edit a generated file; you edit a symbol (or a curated side-input) and re-run
the projection.

```
                                     ┌─▶ build-graph.py ─▶ data/{nodes,bindings,edges}.json   (+ round-trip proof)
 data/symbols/*.json  ──────────────┤
   (+ _spine.json order)            └─▶ build-pages.py ─▶ strokes/  characters/  kangxi/  *.json
                                                            │
 side-inputs (hand-curated):                                └─ pages render these + shared/*.js
   data/words.json              (word tier: 七つ ← 七)
   data/composition-roles.json  (edge roles: 打 ← 丁 phonetic)   ─▶ consumed by build-graph
   data/kangxi.json             (214-radical reference spine)    ─▶ consumed by build-pages
   data/referents.json          (referent → images)              ─▶ consumed by build-pages

 fetched (do NOT hand-edit):
   data/decomposition.json      ◀─ fetch-decomp.py   (Make-Me-a-Hanzi IDS + stroke overrides)
   shared/referents/*           ◀─ fetch-referent.py (Wikimedia Commons)
   */audio/*.mp3                ◀─ gen-audio.py       (edge-tts)
```

---

## The symbol file (source of truth)

`data/symbols/<glyph>.json` — one per glyph. Shape (from `大`, a Kangxi radical):

| field | req | notes |
|---|---|---|
| `glyph` | ✓ | the character; also the filename |
| `cp` | ✓ | codepoint, `"U+5927"` |
| `slug` | ✓ | ASCII key (audio filenames, referent lookup) |
| `class` | ✓ | `stroke` \| `comp` \| `char` — drives page membership |
| `kangxi` | – | Kangxi radical number (present → shows on `/kangxi/`) |
| `form` | ✓ | `{ "hw": bool, "image": str }` — `hw` = has HanziWriter stroke data |
| `composes` | – | authored structural note. ⟨verify-on-ingest⟩ **not** the edge source — `composes` edges come from `decomposition.json`; this field is sparse (many cards omit it). Flagged as debt below. |
| `readings` | ✓ | `{ cn: {...}, jp: {...} }`, each `{ name, reading, gloss, extra?, appearsIn? }` |
| `readings.*.appearsIn` | – | `{ char, reading, gloss }` — the "example" link; becomes a reverse `composes` edge |
| `programs` | – | list of course tiers; see below |
| `form_only` | – | CN-first stub (glyph + reading + strokes, no JP/programs yet). Shows only on `/kangxi/`. |

**`programs[]`** — each entry is `{ source, lang, role, …fields }`. The tier registry
is `PROGRAM_TIERS` in `symbols_io.py` (single source of truth for how these flatten
onto cards and nest into the graph). Current tiers:

| source | role | lang | card field | fields |
|---|---|---|---|---|
| wanikani | radical | jp | `wk` | name, level, kind (`meaning`\|`mnemonic`), glyph→altglyph, icon |
| wanikani | kanji | jp | `kanji` | name, readings, on, kun, level |
| pandanese | radical | cn | `pd` | name, level, kind, icon |
| pandanese | character | cn | `pdc` | name, kind, level |

Adding a new tier (e.g. WK vocab) is **one row** in `PROGRAM_TIERS`, not a parallel
edit across `to_card` / `bind_programs` / `emit_card`.

**Editorial order** lives in `data/symbols/_spine.json` (`{"order": [...]}`). Files
missing from the spine are appended sorted (nothing is silently dropped), but add
new glyphs to the spine to control where they land.

---

## Batch ingest — the steps

Batches arrive as a **terse, shotgun prompt**, not as files — a mixed list with
inline hints and deliberate uncertainty. That underspecification is expected; part
of the exercise is finding where a terse prompt is sufficient and where it needs
tightening, so keep this example realistic rather than idealized. A representative
batch:

> *"Ingest this batch: 止 (stop; radical — meaning or mnemonic?); 川 (river; confirm
> the reading); 子 (child; readings shi/su only); 人口 (population — a word); 丆 (leaf);
> also add an I-beam image for the existing 工 card."*

So the real first move is **route + resolve**, before any file is written:

- **Route** each item to its bucket — a *glyph* card (`symbols/`), a *word*
  (`words.json`, e.g. 人口), a *referent/asset* task (工's image), or an *edit to an
  existing* glyph (工 — and check whether 川/子 are already carded). One prompt
  routinely spans all four.
- **Resolve** the underspecified bits — decide the radical's `kind: meaning|mnemonic`,
  confirm the ?-marked reading (川), honour constraints (子 readings-subset) — and
  **surface the assumptions back** ("took 止 as meaning; 川 already carded, patched
  the JP layer only"). Fill in what's *readily in reach* from the glyph itself (子's
  kun こ alongside the batch's シ・ス; 止's on/kun) but **omit** metadata that needs a
  course lookup (WK `level`) rather than fabricate it — the registry skips an absent
  `level` cleanly, so an under-filled program is honest, not broken.
- **Derive** the mechanical fields the prompt omits — `cp`, `kangxi` number,
  decomposition, `slug`. (A scaffolder should do this — see Known debt.)

Then, per routed item:

1. **Write the symbol files.** One `data/symbols/<glyph>.json` per glyph (schema
   above). Add each new glyph to `data/symbols/_spine.json` in editorial position.
   - **Stroke data for `hw:true` glyphs.** The animation loads
     `shared/hanzi-data/<glyph>.json`; if it isn't already committed, fetch it:
     `python3 shared/hanzi-data/fetch.py <glyph>`. For a component NOT in the base
     dataset (丆, katakana-shaped parts), *lift* its strokes out of a character that
     contains it — and that source char is usually also its `appearsIn`, so one
     char gives you both: `python3 shared/hanzi-data/fetch.py --lift 午:0,1 --as 𠂉`.
     A component with no available source stays `hw:false` (a valid stub) until a
     char using it is carded.

2. **Curate side-inputs as needed:**
   - new **words** → `data/words.json`
   - **component roles** (semantic/phonetic/form) → `data/composition-roles.json`
     (keyed `char → comp → role`; incremental — untyped is fine)
   - new Kangxi radicals must exist in `data/kangxi.json`'s 214 spine (usually already there)

3. **Fetch structural decomposition** → `python3 data/fetch-decomp.py`
   Writes `data/decomposition.json` (immediate components per glyph), reading the
   glyph set straight from `load_symbols()`. Hand-fix the stroke-floor cases — parts
   MMAH truncates to `？` (八 ← 丿 ㇏) or glyphs not in the dataset at all (丆 ← 一 丿)
   — in the script's `STROKE_OVERRIDE` map, not in the JSON. A carded glyph MMAH
   *does* know decomposes automatically (止 ← 上 丨).

4. **Fetch referent images** (optional, multipass) →
   `python3 data/fetch-referent.py <slug> "<query>" -n N`
   Needs `export WIKIMEDIA_CONTACT="you@example.com"`. Registers into
   `data/referents.json`, images into `shared/referents/`.

5. **Build the graph** → `python3 data/build-graph.py`
   Emits `data/{nodes,bindings,edges}.json`. Must print `round-trip … ✓` for every
   page and zero `⚠ composition-roles` warnings.

6. **Build the pages** → `python3 data/build-pages.py`
   Emits `strokes/strokes.json`, `characters/characters.json`, `kangxi/kangxi.json`.
   Emit/parse assertions guard validity.

7. **Generate audio** → `python3 data/gen-audio.py all` (or a specific module)
   Needs `uv tool install edge-tts`. `--dry-run` to preview.
   ⟨verify-on-ingest⟩ glyph audio is homed under `radicals/audio/` and cards point at
   it via `audioBase: "../radicals/"` (the "asset bridge" — see Known debt).

8. **Sanity-check locally** → serve the root (`python3 -m http.server`) and open the
   affected pages + `/graph/`.

9. **Commit** the symbol files, side-inputs, *and* the regenerated outputs together
   (generated files are committed so deploy is build-free).

**Ordering (resolved by an ingest run).** Every step is strictly downstream of the
symbols — `fetch-decomp` reads `load_symbols()` directly, not the page files
build-pages writes — so the order is linear with no back-edge:
symbols → decomp → graph → pages → audio. Each step is idempotent (deterministic
output over the same inputs), so a **partial batch plus a re-run is safe**: prefer
shipping 70% now and taking another pass over blocking on 100%.

---

## Mechanical helpers & guarantees

These are the self-checks that make a batch safe to trust:

- **Round-trip proof** (`build-graph.py`) — regenerates each source card from the
  graph and asserts structural equality. Proves cards are a faithful projection.
- **Emit/parse assertions** (`build-pages.py`) — the hand-formatted card files are
  re-parsed and compared to the projection before writing.
- **Role-overlay validation** (`build-graph.py`) — warns on unknown role values and
  on `composition-roles.json` entries that hit no real edge (typo catch).
- **`PROGRAM_TIERS`** (`symbols_io.py`) — one registry drives card-flatten,
  graph-nest, and page-emit for every course tier.
- **`STROKE_OVERRIDE`** (`fetch-decomp.py`) — hand-authored decompositions for the
  sub-radical strokes MMAH can't see (八 ← 丿 ㇏).

---

## Rules of thumb

- **Never hand-edit a generated file**: `data/{nodes,bindings,edges}.json`,
  `strokes/strokes.json`, `characters/characters.json`, `kangxi/kangxi.json`,
  `data/decomposition.json`. Edit a symbol or a curated side-input and re-run.
- **Functional roles** go in `composition-roles.json` (curated), **structural parts**
  come from `decomposition.json` (fetched) — separate concerns, separate files.
- **Page membership is a rule, not a stored field** — see the `on_*` predicates in
  `symbols_io.py`. A glyph can project onto multiple pages (大 is both a character and
  a Kangxi radical).

---

## Known debt / consolidation candidates

Surfaced while tracing; not yet fixed. Ranked roughly by bite:

1. **~~`fetch-decomp` reads retired `radicals/radicals.json`~~ — FIXED.**
   `needed_glyphs()` now reads `load_symbols()` directly, so the script no longer
   crashes on run, the step-3/6 circularity is gone, and the stale decomposition
   (55 → 227 glyphs) is restored. Still open: `gen-audio.py`'s `radicals` job reads
   the *same* retired file (its audio bucket) — folds into candidate #2.
2. **`source` / audio bucket vs page mismatch.** `build-graph` tags glyphs
   `source: radicals|strokes`; pages are `strokes|characters|kangxi`; kangxi cards
   carry `audioBase: "../radicals/"` — an explicit "bridge until the audio-reconcile
   pass." The `radicals/` dir persists as an *asset* bucket after the *page* retired.
3. **No orchestration.** A batch is 5 manual script runs in a specific order. A
   `data/build.py` (or Makefile) chaining decomp → graph → pages → audio would make a
   batch one command and encode the ordering.
4. **Landing page is hand-maintained** (`index.html`). The module grid is fully
   hardcoded and mixes real substrate pages (strokes/kangxi/characters), standalone
   decks (yan-se, xi-zhuang — a *separate* content system, not symbol-projected), and
   dev/demo pages (`/ui/…`). Candidate: a small module manifest both the landing page
   and README derive from.
5. **`composes` field on symbols is vestigial** — sparsely authored and not the edge
   source. Either make it authoritative (feed the graph) or drop it.
6. **Card scaffolder (high leverage for ingest).** Nothing turns a bare glyph into a
   symbol stub; `cp`, `class`, `kangxi` #, decomposition, and `slug` are looked up by
   hand every time. A `data/scaffold.py <glyph>…` emitting a stub with those derived
   and `TODO` markers on the judgment fields (readings, program `kind`) would cut most
   of the per-glyph toil in Step 1.
7. **Referent (shared) vs glyph-specific images.** `referents.json` is meaning-homed
   — one asset per gloss, shared by every glyph that denotes it. The test for where an
   image lives is NOT shape-vs-meaning but **generalization**: *would it make sense on
   a different glyph with the same gloss?* A fire photo serves any glyph meaning "fire"
   (火/灯/炎) → referent-homed. An I-beam fits 工 on both shape *and* concept, but only
   工 — it wouldn't serve 劳/工作 → glyph-homed (a mnemonic slot, see #8), else it
   leaks to every work-glyph. Pictographs (火, 山, 木) are the easy case where origin,
   shape, and meaning coincide; shape re-readings like 工's I-beam are the trap — apt,
   but glyph-specific. Decide and document the split before it gets conflated.
8. **No first-class "substantive mnemonic" slot.** Today "mnemonic" means only the
   WK/PD `program.kind: mnemonic` cue — program-scoped, negatively-valenced (a
   *warning* that a course's radical name is shape-only and doesn't transfer to the
   real meaning; red/dashed + line-icon). There's no glyph-homed, program-independent
   slot for a *positive*, curated aid that resonates substantively with form+meaning
   without being the definitional referent (I-beam↔工). `form.image` exists but is
   unused (0 cards). Candidate: a glyph-level `mnemonic` block (image and/or note) —
   the de-proprietized generalization of the WK/PD idea, marked **non-definitional**
   like `kind: mnemonic` already is (transfers recall, not semantic authority).
   Distinct from the referent (#7, shared + definitional) and the program cue
   (proprietary); optionally graded by substantiveness (I-beam vs arbitrary shock).
