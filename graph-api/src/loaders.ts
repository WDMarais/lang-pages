import DataLoader from 'dataloader'
import { query } from './db'

// One fresh set of loaders per request (wired in server.ts's context factory).
// DataLoader coalesces every .load(id) made in the same tick into ONE batched
// query, and caches within the request — so a nested query that touches a relation
// on N nodes fires a single `... = ANY($1)` instead of N round-trips. Per-request,
// never shared: cross-request caching would serve stale data between operations.

type Row = Record<string, unknown>

// DataLoader's contract: return an array lined up 1:1 with the requested keys.
// The batch query loses that alignment (it returns a flat, differently-ordered set),
// so we regroup rows under their originating key and map back over the key order.
// Keys with no rows must still get an entry ([]), or the resolver hangs.
function groupByKey(keys: readonly string[], rows: Row[], keyField: string): Row[][] {
  const byKey = new Map<string, Row[]>(keys.map((k) => [k, []]))
  for (const r of rows) byKey.get(r[keyField] as string)?.push(r)
  return keys.map((k) => byKey.get(k)!)
}

export function makeLoaders() {
  return {
    // composes edge: parent is the WHOLE (e.to_id); components are the parts (from nodes).
    components: new DataLoader<string, Row[]>(async (ids) => {
      const { rows } = await query(
        `select e.to_id as _key, n.* from node n
           join edge e on e.from_id = n.id
          where e.to_id = any($1) and e.kind = 'composes'
          order by n.id`,
        [ids as string[]],
      )
      return groupByKey(ids, rows, '_key')
    }),
    // composes edge: parent is a PART (e.from_id); composedInto are the wholes (to nodes).
    composedInto: new DataLoader<string, Row[]>(async (ids) => {
      const { rows } = await query(
        `select e.from_id as _key, n.* from node n
           join edge e on e.to_id = n.id
          where e.from_id = any($1) and e.kind = 'composes'
          order by n.id`,
        [ids as string[]],
      )
      return groupByKey(ids, rows, '_key')
    }),
    // denotes edge: parent is the DENOTER (e.from_id — a word or glyph); the denoted
    // referents are the to nodes. The denotes-kind analog of composedInto.
    denotes: new DataLoader<string, Row[]>(async (ids) => {
      const { rows } = await query(
        `select e.from_id as _key, n.* from node n
           join edge e on e.to_id = n.id
          where e.from_id = any($1) and e.kind = 'denotes'
          order by n.id`,
        [ids as string[]],
      )
      return groupByKey(ids, rows, '_key')
    }),
    // denotes edge: parent is the REFERENT (e.to_id); the denoters are the from nodes.
    // This is the reverse-denotes lookup ("who denotes r:size") — the analog of
    // components, and the batched fix for what would otherwise be an N+1 over referents.
    denotedBy: new DataLoader<string, Row[]>(async (ids) => {
      const { rows } = await query(
        `select e.to_id as _key, n.* from node n
           join edge e on e.from_id = n.id
          where e.to_id = any($1) and e.kind = 'denotes'
          order by n.id`,
        [ids as string[]],
      )
      return groupByKey(ids, rows, '_key')
    }),
    // All langs for each glyph in one query; the (lang:) filter is applied in the
    // resolver — a node has ≤2 bindings, so filtering in memory beats keying the
    // loader on (id, lang) and fragmenting the batch.
    bindings: new DataLoader<string, Row[]>(async (ids) => {
      const { rows } = await query('select * from binding where glyph_id = any($1) order by lang, id', [
        ids as string[],
      ])
      return groupByKey(ids, rows, 'glyph_id')
    }),
  }
}

export type Loaders = ReturnType<typeof makeLoaders>
