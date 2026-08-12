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

-- Slice 2 (bindings): the per-language overlay on the neutral node.
-- This is the node→binding seam. In the source, per-language *audio* keys leak onto
-- the node itself (node.cnAudioKey / node.jpAudioKey / …); readings/gloss already live
-- in bindings.json. We keep `node` neutral (glyph/tier/source/media) and land ALL
-- per-language data here, keyed by (glyph_id, lang). The audio columns are populated
-- by a join-migrate at seed time — pulling node.<lang>AudioKey across the boundary —
-- not by reading the binding's own record, so they are nullable (461/650 have reading
-- audio, 171/650 example audio). Unlike `edge`, the data has no duplicate ids, so `id`
-- is a real PRIMARY KEY — the constraint is earned, not assumed. `raw` stays faithful
-- to the binding's own source record (the migrated audio is a projection-layer join).
create table if not exists binding (
  id            text primary key,
  glyph_id      text not null references node(id),
  lang          text not null,        -- cn | jp
  name          text,
  readings      jsonb not null,       -- string[] (may be empty)
  gloss         text,
  audio_key     text,                 -- migrated from node.<lang>AudioKey (reading audio)
  ex_audio_key  text,                 -- migrated from node.<lang>ExAudioKey (example audio)
  raw           jsonb not null        -- full binding source record (extra/appearsIn/program)
);

-- Resolver-shaped index: Node.bindings(lang) filters by (glyph_id, lang).
create index if not exists binding_glyph_lang_idx on binding (glyph_id, lang);
