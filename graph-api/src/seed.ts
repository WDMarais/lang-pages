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

interface RawBinding {
  id: string
  glyph_id: string
  lang: string
  name?: string
  readings?: string[]
  gloss?: string
}

async function main() {
  // 1. Apply the DDL contract, then start from empty. Re-seed == identical state.
  const ddl = await readFile(resolve(here, 'schema.sql'), 'utf8')
  await pool.query(ddl)
  // Truncate all three in one statement so the FKs to node don't block the reset.
  await pool.query('truncate binding, edge, node')

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

  // 4. Bindings: the per-language overlay. This is the node→binding seam. The audio
  // keys leak onto the node in source (node.<lang>AudioKey), so we join-migrate them
  // across the boundary onto Binding(lang) at ingest — keeping `node` neutral. A lookup
  // by node id lets us pull the right per-language audio for each binding's lang.
  const nodeById = new Map(nodes.map((n) => [n.id, n as Record<string, unknown>]))
  const { bindings } = JSON.parse(await readFile(resolve(DATA, 'bindings.json'), 'utf8')) as {
    bindings: RawBinding[]
  }

  let migratedAudio = 0
  for (const b of bindings) {
    const node = nodeById.get(b.glyph_id)
    const audioKey = (node?.[`${b.lang}AudioKey`] as string | undefined) ?? null
    const exAudioKey = (node?.[`${b.lang}ExAudioKey`] as string | undefined) ?? null
    if (audioKey) migratedAudio++
    await pool.query(
      `insert into binding (id, glyph_id, lang, name, readings, gloss, audio_key, ex_audio_key, raw)
       values ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        b.id,
        b.glyph_id,
        b.lang,
        b.name ?? null,
        JSON.stringify(b.readings ?? []),
        b.gloss ?? null,
        audioKey,
        exAudioKey,
        JSON.stringify(b),
      ],
    )
  }

  const { rows: bindRows } = await pool.query<{ lang: string; c: string }>(
    'select lang, count(*)::text as c from binding group by lang order by lang',
  )
  console.log(
    `seeded ${bindings.length} bindings (${migratedAudio} with migrated audio):`,
    Object.fromEntries(bindRows.map((r) => [r.lang, r.c])),
  )
  await pool.end()
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
