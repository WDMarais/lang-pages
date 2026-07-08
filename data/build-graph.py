#!/usr/bin/env python3
"""Build the data-layer content graph from the committed card JSON.

Ingests the hand-authored projections —
    radicals/radicals.json   (tier: component | char)
    strokes/strokes.json     (tier: stroke)
— and emits the canonical graph:
    data/nodes.json      glyph nodes + referent stubs + frontier stubs
    data/bindings.json   one CN + one JP binding per glyph (WK metadata → JP binding)
    data/edges.json      composes (part→whole) + denotes (glyph→referent stub)

Then ROUND-TRIPS: regenerates each source card-file from the graph and checks
structural equality — proving the cards are just a projection of the graph.

Run: python3 data/build-graph.py
Schema: docs/content-graph-schema.md
"""
import sys

from paths import DATA, read_json, write_json
from symbols_io import (
    load_symbols,
    to_card,
    referent_slug,
    bind_programs,
    unbind_programs,
)
TIER = {"stroke": "stroke", "comp": "component", "char": "char"}
TAG = {v: k for k, v in TIER.items()}
ROLE_VALUES = {"semantic", "phonetic", "form"}  # functional role of a part in a whole


def load_roles():
    """Hand-curated functional role overlay (char → comp → role). Separate from
    the fetched decomposition.json so `fetch-decomp --refresh` never clobbers it."""
    p = DATA / "composition-roles.json"
    if not p.exists():
        return {}
    return {c: m for c, m in read_json(p).items() if not c.startswith("_")}


def source_of(sym):
    """Graph provenance (which authoring bucket) — derived from structural class
    now that page membership lives in the symbols_io projection rules."""
    return "strokes" if sym["class"] == "stroke" else "radicals"


# ── forward: cards → graph ──────────────────────────────────────────────────
def make_binding(glyph, lang, v, card):
    b = {
        "id": f"b:{glyph}@{lang}",
        "glyph_id": f"g:{glyph}",
        "lang": lang,
        "name": v["name"],
        "readings": [v["reading"]] if v.get("reading") else [],
        "gloss": v.get("gloss", ""),
        "extra": v.get("extra", ""),
    }
    if v.get("appearsIn"):
        ai = v["appearsIn"]
        b["appearsIn"] = {"glyph": ai["char"],
                          "reading": ai.get("reading", ""),
                          "gloss": ai.get("gloss", "")}
    # source-program metadata (WK on jp, Pandanese on cn) rides on the language
    # binding it belongs to; the per-tier flatten/nest rules live in symbols_io's
    # PROGRAM_TIERS registry so cards and graph agree on one shape. Kept in its own
    # tagged block so a release build can strip proprietary mnemonics wholesale.
    prog = bind_programs(lang, card)
    if prog:
        b["program"] = prog
    return b


def build():
    nodes, bindings, edges = {}, [], []
    seen_edge = set()
    symbols = load_symbols()
    real = set(symbols)

    roles = load_roles()
    role_used = set()

    def role_of(char, comp):
        r = roles.get(char, {}).get(comp)
        if r is not None:
            role_used.add((char, comp))
        return r

    def cedge(from_id, to_id, role=None):
        e = {"from": from_id, "to": to_id, "kind": "composes"}
        if role:
            e["role"] = role
        return e
    cards_by_source = {"radicals": [], "strokes": []}
    for sym in symbols.values():
        cards_by_source[source_of(sym)].append(to_card(sym))

    for src in ("radicals", "strokes"):
        for c in cards_by_source[src]:
            g = c["glyph"]
            nodes[f"g:{g}"] = {
                "id": f"g:{g}", "kind": "glyph", "glyph": g,
                "tier": TIER[c["tag"]], "slug": c["slug"], "source": src,
                "media": {"hw": c.get("hw", False), "image": c.get("image", "")},
            }
            bindings.append(make_binding(g, "cn", c["cn"], c))
            bindings.append(make_binding(g, "jp", c["jp"], c))

            # denotes → bare referent stub, keyed by the ASCII meaning-slug so the
            # concept spine carries no CN/JP bias; the full gloss rides as label.
            gloss = c["cn"].get("gloss") or c["jp"].get("gloss", "")
            rid = f"r:{referent_slug(gloss)}"
            nodes.setdefault(rid, {"id": rid, "kind": "referent", "label": gloss})
            edges.append({"from": f"g:{g}", "to": rid, "kind": "denotes"})

            # composes ← example chars (union CN+JP, dedup); seed frontier stubs
            for v in (c["cn"], c["jp"]):
                ai = v.get("appearsIn")
                if not ai:
                    continue
                tgt = ai["char"]
                if (g, tgt) not in seen_edge:
                    seen_edge.add((g, tgt))
                    edges.append(cedge(f"g:{g}", f"g:{tgt}", role_of(tgt, g)))
                if tgt not in real:
                    nodes.setdefault(f"g:{tgt}", {
                        "id": f"g:{tgt}", "kind": "glyph", "glyph": tgt,
                        "tier": None, "frontier": True})

    # structural decomposition edges (component → char) from Make-Me-a-Hanzi IDS.
    # These are the real 'parts' the cards lack (男 ← 田 力, 七 ← 一 乚).
    decomp_path = DATA / "decomposition.json"
    if decomp_path.exists():
        decomp = read_json(decomp_path)
        for char, comps in decomp.items():
            if f"g:{char}" not in nodes:
                continue  # only decompose glyphs already in the graph
            for comp in comps:
                if (comp, char) not in seen_edge:
                    seen_edge.add((comp, char))
                    edges.append(cedge(f"g:{comp}", f"g:{char}", role_of(char, comp)))
                if comp not in real:
                    nodes.setdefault(f"g:{comp}", {
                        "id": f"g:{comp}", "kind": "glyph", "glyph": comp,
                        "tier": None, "frontier": True})

    # ── word tier: concrete lexemes instantiating the concept spine ─────────────
    # Words are a SEPARATE graph from the character/concept layer: a word both
    # composes-from its glyph parts (七つ ← 七) and denotes/instantiates a referent
    # (七つ → r:qi "seven"). Unlike glyph nodes — one neutral node with CN+JP
    # bindings — word nodes are audience-tagged and fork per language (七つ is JP;
    # a CN counterpart is a different node), rejoining only at the shared referent.
    # Surface/reading therefore live ON the node, not in a binding.
    words_path = DATA / "words.json"
    if words_path.exists():
        for w in read_json(words_path).get("words", []):
            wid = f"w:{w['surface']}"
            node = {"id": wid, "kind": "word", "tier": "word",
                    "audience": w["audience"], "glyph": w["surface"],
                    "slug": w["slug"], "reading": w.get("reading", ""),
                    "gloss": w.get("gloss", "")}
            if w.get("okurigana"):
                node["okurigana"] = w["okurigana"]
            if w.get("program"):
                node["program"] = w["program"]
            nodes[wid] = node
            for part in w.get("parts", []):
                if (part, w["surface"]) not in seen_edge:
                    seen_edge.add((part, w["surface"]))
                    edges.append(cedge(f"g:{part}", wid))
                if part not in real:
                    nodes.setdefault(f"g:{part}", {
                        "id": f"g:{part}", "kind": "glyph", "glyph": part,
                        "tier": None, "frontier": True})
            if w.get("denotes"):
                # A single-glyph word rejoins its head glyph's referent (already
                # minted by the glyph card). A compound word (二人) denotes a
                # referent no glyph card owns, so the word mints it here.
                rid = f"r:{w['denotes']}"
                nodes.setdefault(rid, {"id": rid, "kind": "referent",
                                       "label": w.get("gloss", "")})
                edges.append({"from": wid, "to": rid, "kind": "denotes"})

    # validate the role overlay: in-vocabulary values, and every declared pair
    # actually landed on a composes edge (an unused entry means a typo'd char/comp).
    for char, m in roles.items():
        for comp, r in m.items():
            if r not in ROLE_VALUES:
                print(f"⚠ composition-roles: {char}←{comp} unknown role {r!r} "
                      f"(expected {sorted(ROLE_VALUES)})", file=sys.stderr)
    declared = {(c, k) for c, m in roles.items() for k in m}
    for char, comp in sorted(declared - role_used):
        print(f"⚠ composition-roles: {char}←{comp} matches no composes edge (typo?)",
              file=sys.stderr)

    return list(nodes.values()), bindings, edges


# ── reverse: graph → cards (the lang-pages projection) ──────────────────────
def view(b):
    v = {"name": b["name"],
         "reading": b["readings"][0] if b["readings"] else "",
         "gloss": b["gloss"]}
    # `extra` is present iff meaningful — mirrors to_card, which carries the raw
    # reading dict (thin form_only symbols have no JP extra yet). Emitting extra:""
    # unconditionally would break the graph↔card round-trip for those.
    if b.get("extra"):
        v["extra"] = b["extra"]
    if "appearsIn" in b:
        e = b["appearsIn"]
        v["appearsIn"] = {"char": e["glyph"], "reading": e["reading"], "gloss": e["gloss"]}
    return v


def project_cards(source, nodes, bindings):
    bb = {b["id"]: b for b in bindings}
    cards = []
    for n in nodes:
        if n.get("source") != source:
            continue
        g = n["glyph"]
        cn, jp = bb[f"b:{g}@cn"], bb[f"b:{g}@jp"]
        card = {
            "glyph": g, "slug": n["slug"], "tag": TAG[n["tier"]],
            "image": n["media"]["image"], "hw": n["media"]["hw"],
            "cn": view(cn),
            "jp": view(jp),
        }
        # recover the flat card tiers from each binding's `program` (inverse of the
        # bind_programs projection above) — one registry, both directions.
        card.update(unbind_programs(cn.get("program"), "cn"))
        card.update(unbind_programs(jp.get("program"), "jp"))
        cards.append(card)
    return cards


def main():
    nodes, bindings, edges = build()
    DATA.mkdir(exist_ok=True)
    for name, payload in [("nodes", {"nodes": nodes}),
                          ("bindings", {"bindings": bindings}),
                          ("edges", {"edges": edges})]:
        write_json(DATA / f"{name}.json", payload)

    glyphs = [n for n in nodes if n["kind"] == "glyph"]
    print(f"nodes:    {len(nodes)}  "
          f"({sum(1 for n in glyphs if not n.get('frontier'))} real glyph, "
          f"{sum(1 for n in glyphs if n.get('frontier'))} frontier, "
          f"{sum(1 for n in nodes if n['kind']=='referent')} referent, "
          f"{sum(1 for n in nodes if n['kind']=='word')} word)")
    print(f"bindings: {len(bindings)}")
    composes = [e for e in edges if e["kind"] == "composes"]
    print(f"edges:    {len(edges)}  "
          f"({len(composes)} composes [{sum(1 for e in composes if e.get('role'))} typed], "
          f"{sum(1 for e in edges if e['kind']=='denotes')} denotes)")

    # round-trip proof: the graph must faithfully re-emit the symbol projection
    ok = True
    syms = load_symbols()
    by_source = {"radicals": [], "strokes": []}
    for sym in syms.values():
        by_source[source_of(sym)].append(to_card(sym))
    for src in ("radicals", "strokes"):
        original = by_source[src]
        rebuilt = project_cards(src, nodes, bindings)
        if original == rebuilt:
            print(f"round-trip {src+'.json':16} ✓  ({len(rebuilt)} cards identical)")
        else:
            ok = False
            print(f"round-trip {src+'.json':16} ✗  MISMATCH")
            for o, r in zip(original, rebuilt):
                if o != r:
                    diff = [k for k in o if o.get(k) != r.get(k)]
                    print(f"    {o['glyph']}: differs in {diff}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
