# lang-pages graph-api

A GraphQL + Postgres projection over the lang-pages content graph.

**Design stance:** the git-committed JSON in `../data/` is the *source of truth*.
Postgres is a **disposable build artifact**, rebuilt from `schema.sql` plus that JSON
on every seed. Nothing lives only in the database, so the whole thing spins up from
the repo with no external state.

## Clone-and-go

```sh
createdb lang_pages_graph        # once
cp .env.example .env             # sets PGHOST / PGDATABASE (edit if yours differ)
npm install
npm run seed                     # apply schema.sql + ingest ../data/*.json
npm run dev                      # GraphQL at http://localhost:4000/graphql
```

Drop and recreate the DB any time; `npm run seed` returns it to an identical state.

## Try it

```graphql
{
  node(id: "g:一") { id kind glyph tier }
  nodes(kind: "glyph", first: 5) { id glyph tier }
  # walk the compositional graph: 分 is built from 八 + 刀
  compound: node(id: "g:分") { glyph components { glyph } }
  # per-language overlays; audio is migrated from the node across the seam
  overlays: node(id: "g:一") { glyph bindings { lang readings gloss audioKey } }
}
```

## Layout

| file             | role                                                    |
|------------------|---------------------------------------------------------|
| `src/schema.sql` | relational DDL: the storage contract                    |
| `src/seed.ts`    | ingest: apply DDL, read committed JSON, build the links |
| `src/server.ts`  | GraphQL Yoga server; SDL is the client/server contract  |
| `src/loaders.ts` | per-request DataLoaders that batch the relation queries |
| `src/db.ts`      | pg pool + a `query()` choke point that counts round-trips |

## Performance — the N+1 and its fix

The relation fields (`components`, `composedInto`, `bindings`) naively fire one
query per parent node: a request over N nodes costs 2N+1 round-trips. Per-request
DataLoaders (`src/loaders.ts`) coalesce every `.load(id)` in a tick into a single
`... = ANY($1)` batch, collapsing that to a constant 3.

It's measurable, not asserted: set `GRAPH_API_PROBE=1` to log the DB-query count
per operation. The query in *Try it* above over 20 glyphs drops from **41 → 3**.

## Config

Connection settings come from `.env` (see `.env.example`). The app fails fast if
they are unset rather than guessing a default.
