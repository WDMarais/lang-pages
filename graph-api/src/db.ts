import 'dotenv/config'
import pg from 'pg'

const { Pool } = pg

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`Missing required env var ${name} (copy .env.example to .env)`)
  return value
}

// All connection config comes from the environment. No fallbacks, so a missing or
// wrong .env fails loudly instead of silently connecting somewhere unexpected.
// PGHOST points at the socket directory, which selects peer auth (no password).
export const pool = new Pool({
  host: required('PGHOST'),
  database: required('PGDATABASE'),
})

// Slice 3 probe: a single choke point for every DB round-trip the GraphQL layer
// makes. Counting in one place (rather than scattering counters) lets a per-request
// plugin measure the N+1 — and is the seam the DataLoader batching slots into.
export const stats = { queries: 0 }

export function query(text: string, params?: unknown[]) {
  stats.queries++
  return pool.query(text, params)
}
