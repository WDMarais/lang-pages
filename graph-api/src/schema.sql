-- Relational projection of the lang-pages content graph.
-- This file is the DDL contract; the DB is rebuilt from it + the committed
-- JSON on every `npm run seed`. Nothing lives only in the database.

-- Slice 1: the item layer (the compositional DAG's vertices).
create table if not exists node (
  id     text primary key,
  kind   text not null,          -- glyph | referent | word
  glyph  text,                   -- surface form, for glyph/word nodes
  tier   text,                   -- stroke | component | char | word (null for referents)
  source text,                   -- membership tag as-authored (see note in seed.ts)
  label  text,                   -- human label, for referent nodes
  media  jsonb,                  -- { hw, image }
  raw    jsonb not null          -- full source record, so nothing is lost in the projection
);

-- Slice 2: the relation layer (the graph's edges).
-- The edge set is heterogeneous: 4 kinds, and `association` carries extra fields
-- (type/symmetric/cluster/source). We promote only the two cross-cutting, queryable
-- attributes (kind, role) to columns; everything else survives in `raw` — the same
-- lossless-projection convention as node.raw. No unique key on (from_id,to_id,kind):
-- the data legitimately contains duplicate `association` triples, so a naive PK would
-- reject real rows. FK to node(id) is a deliberate integrity guarantee (0 dangling
-- refs verified at authoring time) — an edge cannot reference a non-existent vertex.
create table if not exists edge (
  from_id text not null references node(id),
  to_id   text not null references node(id),
  kind    text not null,         -- denotes | composes | variant | association
  role    text,                  -- semantic | phonetic (composes only; null otherwise)
  raw     jsonb not null         -- full source record (association extras, etc.)
);

-- Resolver-shaped indexes: components (to_id, kind) and composedInto (from_id, kind).
create index if not exists edge_to_kind_idx   on edge (to_id, kind);
create index if not exists edge_from_kind_idx on edge (from_id, kind);
