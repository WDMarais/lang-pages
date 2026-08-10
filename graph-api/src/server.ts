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
}

const yoga = createYoga({ schema: createSchema({ typeDefs, resolvers }) })

createServer(yoga).listen(4000, () => {
  console.log('graph-api → http://localhost:4000/graphql')
})
