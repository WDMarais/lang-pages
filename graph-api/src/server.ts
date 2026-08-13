import { createServer } from 'node:http'
import { createYoga, createSchema } from 'graphql-yoga'
import { query, stats } from './db'
import { makeLoaders, type Loaders } from './loaders'

type Ctx = { loaders: Loaders }

// Schema-first: the SDL is the contract between client and server, the same way
// tests are the contract between spec and implementation.
const typeDefs = /* GraphQL */ `
  type Node {
    id: ID!
    kind: String!
    glyph: String
    tier: String
    label: String
    "Parts this node is built from (incoming composes edges)."
    components: [Node!]!
    "Wholes this node is a component of (outgoing composes edges)."
    composedInto: [Node!]!
    "Referents this node denotes (outgoing denotes edges)."
    denotes: [Node!]!
    "Nodes that denote this one (incoming denotes edges) — the reverse-denotes lookup, meaningful on referent nodes."
    denotedBy: [Node!]!
    "Per-language overlays on this (neutral) node. Optionally filtered by lang."
    bindings(lang: String): [Binding!]!
  }

  "A per-language overlay on a node: readings, gloss, and audio for one language."
  type Binding {
    id: ID!
    lang: String!
    name: String
    readings: [String!]!
    gloss: String
    "Reading-audio key, migrated from the node across the neutral/overlay seam."
    audioKey: String
    "Example-word-audio key, migrated from the node across the same seam."
    exAudioKey: String
  }

  type Query {
    node(id: ID!): Node
    nodes(kind: String, first: Int = 20): [Node!]!
    "Referent nodes whose label matches (case-insensitive substring). The rejoin-hunt entrypoint: find an existing referent to reuse before minting a new one."
    referents(near: String, first: Int = 20): [Node!]!
  }
`

const resolvers = {
  Query: {
    node: async (_parent: unknown, args: { id: string }) => {
      const { rows } = await query('select * from node where id = $1', [args.id])
      return rows[0] ?? null
    },
    nodes: async (_parent: unknown, args: { kind?: string; first: number }) => {
      const { rows } = args.kind
        ? await query('select * from node where kind = $1 order by id limit $2', [
            args.kind,
            args.first,
          ])
        : await query('select * from node order by id limit $1', [args.first])
      return rows
    },
    // Referent search over label. `near` is a case-insensitive substring (ILIKE);
    // omitting it lists referents. The one place the DB does the matching so callers
    // never hand-write the rejoin query.
    referents: async (_parent: unknown, args: { near?: string; first: number }) => {
      const { rows } = await query(
        `select * from node
          where kind = 'referent' and ($1::text is null or label ilike '%' || $1 || '%')
          order by id limit $2`,
        [args.near ?? null, args.first],
      )
      return rows
    },
  },
  // Relation resolvers go through per-request DataLoaders (see loaders.ts): every
  // .load(id) in a tick coalesces into one batched query. This is the collapse of
  // the N+1 the probe measured — 2N+1 queries become a constant 3.
  Node: {
    components: (parent: { id: string }, _args: unknown, ctx: Ctx) =>
      ctx.loaders.components.load(parent.id),
    composedInto: (parent: { id: string }, _args: unknown, ctx: Ctx) =>
      ctx.loaders.composedInto.load(parent.id),
    denotes: (parent: { id: string }, _args: unknown, ctx: Ctx) =>
      ctx.loaders.denotes.load(parent.id),
    denotedBy: (parent: { id: string }, _args: unknown, ctx: Ctx) =>
      ctx.loaders.denotedBy.load(parent.id),
    // The loader returns all langs for the glyph; apply the (lang:) filter in memory
    // (≤2 rows) so the batch stays keyed on node id alone.
    bindings: async (parent: { id: string }, args: { lang?: string }, ctx: Ctx) => {
      const rows = await ctx.loaders.bindings.load(parent.id)
      return args.lang ? rows.filter((r) => r.lang === args.lang) : rows
    },
  },
  // The DB stores the migrated audio in snake_case; the SDL exposes camelCase.
  // (readings is jsonb → pg already hands it back as a JS array.)
  Binding: {
    audioKey: (b: { audio_key: string | null }) => b.audio_key,
    exAudioKey: (b: { ex_audio_key: string | null }) => b.ex_audio_key,
  },
}

// Slice 3 probe: snapshot the global query counter around each GraphQL operation
// and log the per-request delta, so the N+1 is measurable rather than asserted.
// Opt-in via GRAPH_API_PROBE — left in as an observability hook, off by default.
const queryCountProbe = {
  onExecute() {
    const before = stats.queries
    return {
      onExecuteDone() {
        console.log(`[probe] ${stats.queries - before} DB queries this operation`)
      },
    }
  },
}

const yoga = createYoga({
  schema: createSchema({ typeDefs, resolvers }),
  // Fresh loaders per request — batching + caching are request-scoped by design.
  context: (): Ctx => ({ loaders: makeLoaders() }),
  plugins: process.env.GRAPH_API_PROBE ? [queryCountProbe] : [],
})

createServer(yoga).listen(4000, () => {
  console.log('graph-api → http://localhost:4000/graphql')
})
