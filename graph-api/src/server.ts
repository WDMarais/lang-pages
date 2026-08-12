import { createServer } from 'node:http'
import { createYoga, createSchema } from 'graphql-yoga'
import { pool } from './db'

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
  }
`

const resolvers = {
  Query: {
    node: async (_parent: unknown, args: { id: string }) => {
      const { rows } = await pool.query('select * from node where id = $1', [args.id])
      return rows[0] ?? null
    },
    nodes: async (_parent: unknown, args: { kind?: string; first: number }) => {
      const { rows } = args.kind
        ? await pool.query('select * from node where kind = $1 order by id limit $2', [
            args.kind,
            args.first,
          ])
        : await pool.query('select * from node order by id limit $1', [args.first])
      return rows
    },
  },
  // Relation resolvers walk composes edges. One query per field per node → this is
  // the deliberate N+1 point that slice 3's per-request dataloader will collapse.
  Node: {
    components: async (parent: { id: string }) => {
      const { rows } = await pool.query(
        `select n.* from node n
           join edge e on e.from_id = n.id
          where e.to_id = $1 and e.kind = 'composes'
          order by n.id`,
        [parent.id],
      )
      return rows
    },
    composedInto: async (parent: { id: string }) => {
      const { rows } = await pool.query(
        `select n.* from node n
           join edge e on e.to_id = n.id
          where e.from_id = $1 and e.kind = 'composes'
          order by n.id`,
        [parent.id],
      )
      return rows
    },
    // Per-language overlays. Same N+1 shape as the composes relations above —
    // slice 3's dataloader will batch these by (glyph_id, lang) too.
    bindings: async (parent: { id: string }, args: { lang?: string }) => {
      const { rows } = args.lang
        ? await pool.query(
            'select * from binding where glyph_id = $1 and lang = $2 order by id',
            [parent.id, args.lang],
          )
        : await pool.query('select * from binding where glyph_id = $1 order by lang, id', [
            parent.id,
          ])
      return rows
    },
  },
  // The DB stores the migrated audio in snake_case; the SDL exposes camelCase.
  // (readings is jsonb → pg already hands it back as a JS array.)
  Binding: {
    audioKey: (b: { audio_key: string | null }) => b.audio_key,
    exAudioKey: (b: { ex_audio_key: string | null }) => b.ex_audio_key,
  },
}

const yoga = createYoga({ schema: createSchema({ typeDefs, resolvers }) })

createServer(yoga).listen(4000, () => {
  console.log('graph-api → http://localhost:4000/graphql')
})
