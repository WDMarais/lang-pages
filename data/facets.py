#!/usr/bin/env python3
"""Project the content graph onto its schedulable facets — and report coverage.

A *facet* is one SRS candidate: a (node × skill × context) an SRS tool could
schedule. It is NOT stored anywhere — it is a pure query over the committed graph
(nodes + bindings + edges), computed on demand. This module is that query, and
the second consumer of the substrate after build-pages / build-graph.

A facet exists exactly where a groundable answer exists — so `skill` is derived
from the *presence of grounding data*, not from tier (tier is only a display hint):

    recognize  <= node has a renderable form            (glyph present)
    produce    <= node has stroke-order data            (media.animated)
    read       <= a binding@ctx (or word node) has readings
    mean       <= a binding@ctx (or word node) has a gloss
                  ...sense-grounded iff a denotes->referent carries real media

The `mean` grounding share is a live KPI: it measures how much "meaning" the deck
would teach as a WORD (a gloss string) rather than as a REFERENT (an image / sound
/ motion) — the gap the "answer = sense-data, not description" thesis exists to
close. It should climb as data/referents.json gains media.

Run: python3 data/facets.py
"""
from collections import Counter, defaultdict

from paths import DATA, read_json

SKILLS = ("recognize", "produce", "read", "mean")


def load():
    return (
        read_json(DATA / "nodes.json")["nodes"],
        read_json(DATA / "bindings.json")["bindings"],
        read_json(DATA / "edges.json")["edges"],
        read_json(DATA / "referents.json"),
    )


def _grounded(referent_id, referents):
    """r:fire -> True iff referents.json['fire'] carries at least one image."""
    slug = referent_id[2:] if referent_id.startswith("r:") else referent_id
    entry = referents.get(slug)
    return bool(entry and entry.get("images"))


def project(nodes, bindings, edges, referents):
    """Return the facet list [(node_id, skill, ctx)] — the projection itself."""
    bind_by_glyph = defaultdict(list)
    for b in bindings:
        bind_by_glyph[b["glyph_id"]].append(b)
    denotes = defaultdict(list)
    for e in edges:
        if e["kind"] == "denotes":
            denotes[e["from"]].append(e["to"])

    facets = []
    for n in nodes:
        nid, is_word = n["id"], n.get("kind") == "word"
        if n.get("glyph"):
            facets.append((nid, "recognize", "-"))
        if n.get("media", {}).get("animated"):
            facets.append((nid, "produce", "-"))

        # read / mean live per language context: on the node itself for words
        # (inherently single-language), on each binding for neutral glyphs.
        if is_word:
            ctx = n.get("audience", "?")
            if n.get("reading"):
                facets.append((nid, "read", ctx))
            if n.get("gloss"):
                facets.append((nid, "mean", ctx))
        else:
            for b in bind_by_glyph.get(nid, []):
                if b.get("readings"):
                    facets.append((nid, "read", b["lang"]))
                if b.get("gloss"):
                    facets.append((nid, "mean", b["lang"]))
    return facets


def report(nodes, bindings, edges, referents):
    facets = project(nodes, bindings, edges, referents)
    by_skill = Counter(f[1] for f in facets)

    print(f"nodes: {len(nodes)}   facets: {len(facets)} (a projection, stored nowhere)")
    for s in SKILLS:
        print(f"  {s:10} {by_skill[s]}")

    # read coverage by tier — shows the determinant is grounding, not tier
    read_nodes = {f[0] for f in facets if f[1] == "read"}
    cov = defaultdict(lambda: [0, 0])
    for n in nodes:
        if n.get("kind") == "referent":
            continue
        cov[n.get("tier")][1] += 1
        cov[n.get("tier")][0] += n["id"] in read_nodes
    print("\nread coverage by tier (char/stroke saturate; component splits):")
    for t, (r, tot) in sorted(cov.items(), key=lambda x: -x[1][1]):
        print(f"  {str(t):10} {r}/{tot}")

    # the telos KPI: referents that are sense-data vs prose-only stubs
    refs = [n for n in nodes if n.get("kind") == "referent"]
    grounded = sum(1 for slug, e in referents.items() if e.get("images"))
    print("\nreferent grounding (the telos KPI):")
    print(f"  {grounded}/{len(refs)} referents carry sense-data "
          f"({100 * grounded // (len(refs) or 1)}%) — "
          f"{len(refs) - grounded} are prose-only label stubs")
    return facets


if __name__ == "__main__":
    report(*load())
