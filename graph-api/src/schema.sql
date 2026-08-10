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
