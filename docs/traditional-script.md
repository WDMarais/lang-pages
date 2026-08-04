# The `script` block (simplified ↔ traditional)

How a symbol records the simplified/traditional (繁體) Han correspondence.
Companion to [authoring.md](authoring.md) (the symbol-file schema) — this doc
specifies one block it adds. Supersedes the interim "note `繁: X` / `简: X`
inline in `cn.extra`" convention (see memory *cn-traditional-handling*).

## Decision

- **A field, not an edge.** Simplified and traditional forms are *orthographic
  alternates of one teaching unit*, not independently-taught characters — so they
  live as an attribute on the symbol, minting no graph nodes/edges. (Contrast
  `association` confusable/cognate, where both glyphs are real things you learn
  separately → edges. A specific form can be *promoted* to a real node later if it
  ever needs teaching in its own right.)
- **Symmetric — neither script is implicitly "the main one."** The card `glyph`
  is the node's single identity (one face on the card), but it may sit on *either*
  Han axis: most CN symbols key on the simplified form (可, 从), while Kangxi-radical
  and JP-authored nodes key on the traditional form (車, 魚, 億). The `script` block
  names the axis the glyph occupies (`keyed`) and records the *other* Han form(s)
  under its own slot (`simplified` / `traditional`). Both slots are first-class; the
  keyed one is simply omitted because the `glyph` already is it.
- **The JP shinjitai axis is already stored** as `readings.jp.name` (従, 個, 業…),
  so the block only ever carries Han forms. The one exception is a glyph *keyed on*
  the shinjitai (円) — see below.

## Schema

`script` — sibling of `readings`/`programs`/`composes` on the symbol:

```jsonc
script: {
  keyed?: "simplified" | "traditional" | "shinjitai",  // axis the card `glyph` occupies; default "simplified"
  same?: true,                                          // the two Han forms coincide (verified) — axis-neutral
  simplified?: [ { glyph, when? } ],                    // named iff it is NOT the keyed glyph
  traditional?: [ { glyph, when? } ],                   // named iff it is NOT the keyed glyph
}
```

| field | meaning |
|---|---|
| `keyed` | which axis the `glyph` sits on. Default `"simplified"`. Set `"traditional"` for trad-keyed nodes (Kangxi radicals, JP-authored 億), `"shinjitai"` for the 円 case. |
| `same: true` | verified no-divergence (繁简同形). Mutually exclusive with naming a Han slot; only valid on a Han-keyed glyph. Distinct from an **absent** `script`, which means *unclassified*. |
| `simplified` / `traditional` | the Han form(s) on that axis. **Omit the slot matching `keyed`** — the `glyph` already is that form; restating it is an error. |

A **form entry** is `{ "glyph": "體", "when"?: "<sense>" }`:
- `glyph` (req) — a single traditional/simplified CJK character.
- `when` (opt) — the sense under which this form applies; used when a slot lists
  several forms that split by meaning (merge cases). A plain 1:1 omits it, and the
  *default* form in a multi-entry list may omit it while the special-case carries one.

The absent/`same`/named distinction is the point: it separates *unknown* from
*checked-identical* from *checked-divergent*, so the gate can flag the real backlog
instead of silently passing everything.

## Examples

```jsonc
// 可, 如 — simplified-keyed, verified identical
"script": { "same": true }

// 从 — simplified-keyed, traditional differs (1:1)
"script": { "traditional": [ { "glyph": "從" } ] }

// 后 — simplified-keyed; sense-conditioned merge. 後 for "after"; queen-sense 后 unchanged
"script": { "traditional": [ { "glyph": "後", "when": "after; behind; time & position" },
                             { "glyph": "后", "when": "empress; queen (unchanged)" } ] }

// 个 — simplified-keyed, one glyph → several traditional forms (個 default, 箇 literary)
"script": { "traditional": [ { "glyph": "個" },
                             { "glyph": "箇", "when": "classifier; literary" } ] }

// 車, 魚, 億 — TRADITIONAL-keyed (glyph IS the trad form); simplified named
"script": { "keyed": "traditional", "simplified": [ { "glyph": "车" } ] }

// 円 — shinjitai-keyed (glyph is neither Han form); both Han axes named
"script": { "keyed": "shinjitai",
            "simplified":  [ { "glyph": "圆" } ],
            "traditional": [ { "glyph": "圓" } ] }
```

### The inversion, resolved

Earlier, trad-keyed nodes (車/魚/億, keyed on the traditional glyph because that's
the Kangxi radical or the form a decomposition needs) recorded their simplified form
as inline `简: X` prose — a separate, asymmetric mechanism from the `繁: X` prose the
field replaced. The symmetric block folds both directions into one structure: a
simplified-keyed glyph names `traditional`, a traditional-keyed glyph names
`simplified`, and the render labels each with 简/繁 accordingly. There is no longer a
"primary" script baked into the schema — only which axis this particular `glyph`
happens to sit on.

## Projection & tooling

- **`to_card`** (`symbols_io.py`) passes the whole `script` block through onto the
  card verbatim — so both build-pages (render) and build-graph (node + round-trip)
  see it and round-trip stays ✓. The projection is schema-agnostic; only the two
  ends below encode the shape.
- **Card render** (`cards3.*`): a corner chip beside the glyph. For each named Han
  slot it emits a labelled segment (`简`/`繁`) with the form(s); a `when` qualifier
  becomes a hover tooltip; `same: true` renders a faint `繁=简`; an absent block
  renders nothing. A shinjitai-keyed glyph shows both segments (円 → `简 圆  繁 圓`).
- **`check-source` gate** (`check_script`): validates `keyed` ∈ the three axes; that
  the keyed Han slot is **not** restated; that `same` is exclusive with a named form
  and Han-keyed; that each named slot is a non-empty list of single-char `glyph`
  entries with non-empty `when` when present. The **repo-wide "unclassified" warning
  stays OFF** for now — backfill is incremental (classify known glyphs, gate quiet),
  same play as the frontier word-part warnings.

## Backfill

Shipped: the mechanism plus every glyph that carried inline `繁: X` or `简: X` prose,
stripping the now-redundant fragment from `cn.extra`:

- **simplified-keyed:** 万→萬 · 与→與 · 业→業 · 个→個/箇 · 义→義 · 于→於 · 从→從 ·
  体→體 · 儿→兒 · 后→後(+后 queen) · 可→same · 如→same
- **traditional-keyed** (inversion): 車→车 · 魚→鱼 · 億→亿
- **shinjitai-keyed:** 円 → simplified 圆 + traditional 圓

Remaining trad-keyed Kangxi radicals (貝→贝, 見→见, 門→门) take a
`{ "keyed": "traditional", "simplified": [ { "glyph": "…" } ] }` block as they gain
PD bindings — no more inline `简:` prose.
