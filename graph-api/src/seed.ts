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

async function main() {
  // 1. Apply the DDL contract, then start from empty. Re-seed == identical state.
  const ddl = await readFile(resolve(here, 'schema.sql'), 'utf8')
  await pool.query(ddl)
  await pool.query('truncate node')

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
  await pool.end()
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
