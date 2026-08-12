import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { pool } from './db'

const here = dirname(fileURLToPath(import.meta.url))
const DATA = resolve(here, '../../data') // the committed lang-pages data/ in this worktree

interface RawNode {
  id: string
  kind: string
  glyph?: string
  tier?: string
  source?: string
  label?: string
  media?: unknown
}

interface RawEdge {
  from: string
  to: string
  kind: string
  role?: string
}

async function main() {
  // 1. Apply the DDL contract, then start from empty. Re-seed == identical state.
  const ddl = await readFile(resolve(here, 'schema.sql'), 'utf8')
  await pool.query(ddl)
  // Truncate both in one statement so the edge→node FK doesn't block the reset.
  await pool.query('truncate edge, node')

  // 2. Read the source of truth from git-committed JSON and materialize it.
  const { nodes } = JSON.parse(await readFile(resolve(DATA, 'nodes.json'), 'utf8')) as {
    nodes: RawNode[]
  }

  for (const n of nodes) {
    await pool.query(
      `insert into node (id, kind, glyph, tier, source, label, media, raw)
       values ($1, $2, $3, $4, $5, $6, $7, $8)`,
      [
        n.id,
        n.kind,
        n.glyph ?? null,
        n.tier ?? null,
        n.source ?? null,
        n.label ?? null,
        n.media ? JSON.stringify(n.media) : null,
        JSON.stringify(n),
      ],
    )
  }

  const { rows } = await pool.query<{ kind: string; c: string }>(
    'select kind, count(*)::text as c from node group by kind order by kind',
  )
  console.log(`seeded ${nodes.length} nodes:`, Object.fromEntries(rows.map((r) => [r.kind, r.c])))

  // 3. Edges reference nodes (FK), so they load after the vertices exist.
  const { edges } = JSON.parse(await readFile(resolve(DATA, 'edges.json'), 'utf8')) as {
    edges: RawEdge[]
  }

  for (const e of edges) {
    await pool.query(
      `insert into edge (from_id, to_id, kind, role, raw)
       values ($1, $2, $3, $4, $5)`,
      [e.from, e.to, e.kind, e.role ?? null, JSON.stringify(e)],
    )
  }

  const { rows: edgeRows } = await pool.query<{ kind: string; c: string }>(
    'select kind, count(*)::text as c from edge group by kind order by kind',
  )
  console.log(
    `seeded ${edges.length} edges:`,
    Object.fromEntries(edgeRows.map((r) => [r.kind, r.c])),
  )
  await pool.end()
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
