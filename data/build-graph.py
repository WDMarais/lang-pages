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
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES = [("radicals", ROOT / "radicals/radicals.json"),
           ("strokes",  ROOT / "strokes/strokes.json")]
TIER = {"stroke": "stroke", "comp": "component", "char": "char"}
TAG = {v: k for k, v in TIER.items()}


def load_cards(path):
    d = json.loads(path.read_text())
    return [c for grp in d["groups"] for c in grp["cards"]]


# ── forward: cards → graph ──────────────────────────────────────────────────
def make_binding(glyph, lang, v, wk, kanji=None):
    b = {
        "id": f"b:{glyph}@{lang}",
        "glyph_id": f"g:{glyph}",
        "lang": lang,
        "name": v["name"],
        "readings": [v["reading"]] if v.get("reading") else [],
        "gloss": v.get("gloss", ""),
        "extra": v.get("extra", ""),
    }
    if v.get("ex"):
        ex = v["ex"]
        b["example"] = {"glyph": ex["char"],
                        "reading": ex.get("reading", ""),
                        "gloss": ex.get("gloss", "")}
    # source-program metadata lives on the language binding it belongs to.
    # WaniKani ships radical + kanji as SEPARATE items on the same glyph; the
    # program's top-level fields describe the radical, program.kanji the kanji
    # (its real meaning + on/kun reading). They diverge for shape-mnemonic
    # radicals — 八 is radical "Fins" (mnemonic) but kanji "Eight" (meaning).
    if lang == "jp" and (wk or kanji):
        prog = {"source": "wanikani"}
        if wk:
            prog.update({"name": wk["name"], "kind": wk["kind"], "level": wk["level"]})
            if wk.get("glyph"):
                prog["altglyph"] = wk["glyph"]
            if wk.get("icon"):
                prog["icon"] = wk["icon"]
        if kanji:
            prog["kanji"] = {"name": kanji["name"],
                             "readings": kanji.get("readings", []),
                             "on": kanji.get("on", False),
                             "level": kanji.get("level", 1)}
        b["program"] = prog
    return b


def build():
    nodes, bindings, edges = {}, [], []
    seen_edge = set()
    real = {c["glyph"] for _, path in SOURCES for c in load_cards(path)}

    for src, path in SOURCES:
        for c in load_cards(path):
            g = c["glyph"]
            nodes[f"g:{g}"] = {
                "id": f"g:{g}", "kind": "glyph", "glyph": g,
                "tier": TIER[c["tag"]], "slug": c["slug"], "source": src,
                "media": {"hw": c.get("hw", False), "image": c.get("image", "")},
            }
            bindings.append(make_binding(g, "cn", c["cn"], None))
            bindings.append(make_binding(g, "jp", c["jp"], c.get("wk"), c.get("kanji")))

            # denotes → bare referent stub (English gloss as label; shared meaning later)
            rid = f"r:{c['slug']}"
            nodes.setdefault(rid, {"id": rid, "kind": "referent",
                                   "label": c["cn"].get("gloss") or c["jp"].get("gloss", "")})
            edges.append({"from": f"g:{g}", "to": rid, "kind": "denotes"})

            # composes ← example chars (union CN+JP, dedup); seed frontier stubs
            for v in (c["cn"], c["jp"]):
                ex = v.get("ex")
                if not ex:
                    continue
                tgt = ex["char"]
                if (g, tgt) not in seen_edge:
                    seen_edge.add((g, tgt))
                    edges.append({"from": f"g:{g}", "to": f"g:{tgt}", "kind": "composes"})
                if tgt not in real:
                    nodes.setdefault(f"g:{tgt}", {
                        "id": f"g:{tgt}", "kind": "glyph", "glyph": tgt,
                        "tier": None, "frontier": True})

    # structural decomposition edges (component → char) from Make-Me-a-Hanzi IDS.
    # These are the real 'parts' the cards lack (男 ← 田 力, 七 ← 一 乚).
    decomp_path = DATA / "decomposition.json"
    if decomp_path.exists():
        decomp = json.loads(decomp_path.read_text())
        for char, comps in decomp.items():
            if f"g:{char}" not in nodes:
                continue  # only decompose glyphs already in the graph
            for comp in comps:
                if (comp, char) not in seen_edge:
                    seen_edge.add((comp, char))
                    edges.append({"from": f"g:{comp}", "to": f"g:{char}", "kind": "composes"})
                if comp not in real:
                    nodes.setdefault(f"g:{comp}", {
                        "id": f"g:{comp}", "kind": "glyph", "glyph": comp,
                        "tier": None, "frontier": True})

    return list(nodes.values()), bindings, edges


# ── reverse: graph → cards (the lang-pages projection) ──────────────────────
def view(b):
    v = {"name": b["name"],
         "reading": b["readings"][0] if b["readings"] else "",
         "gloss": b["gloss"], "extra": b["extra"]}
    if "example" in b:
        e = b["example"]
        v["ex"] = {"char": e["glyph"], "reading": e["reading"], "gloss": e["gloss"]}
    return v


def wk_from(jp):
    p = jp.get("program")
    if not p or p.get("source") != "wanikani" or "name" not in p:
        return None
    wk = {"name": p["name"], "level": p["level"], "kind": p["kind"]}
    if "altglyph" in p:
        wk["glyph"] = p["altglyph"]
    if "icon" in p:
        wk["icon"] = p["icon"]
    return wk


def kanji_from(jp):
    p = jp.get("program")
    k = p.get("kanji") if p else None
    if not k:
        return None
    return {"name": k["name"], "readings": k.get("readings", []),
            "on": k.get("on", False), "level": k.get("level", 1)}


def project_cards(source, nodes, bindings):
    bb = {b["id"]: b for b in bindings}
    cards = []
    for n in nodes:
        if n.get("source") != source:
            continue
        g = n["glyph"]
        jp = bb[f"b:{g}@jp"]
        card = {
            "glyph": g, "slug": n["slug"], "tag": TAG[n["tier"]],
            "image": n["media"]["image"], "hw": n["media"]["hw"],
            "cn": view(bb[f"b:{g}@cn"]),
            "jp": view(jp),
            "wk": wk_from(jp),
        }
        kanji = kanji_from(jp)
        if kanji:
            card["kanji"] = kanji
        cards.append(card)
    return cards


def main():
    nodes, bindings, edges = build()
    DATA.mkdir(exist_ok=True)
    for name, payload in [("nodes", {"nodes": nodes}),
                          ("bindings", {"bindings": bindings}),
                          ("edges", {"edges": edges})]:
        (DATA / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    glyphs = [n for n in nodes if n["kind"] == "glyph"]
    print(f"nodes:    {len(nodes)}  "
          f"({sum(1 for n in glyphs if not n.get('frontier'))} real glyph, "
          f"{sum(1 for n in glyphs if n.get('frontier'))} frontier, "
          f"{sum(1 for n in nodes if n['kind']=='referent')} referent)")
    print(f"bindings: {len(bindings)}")
    print(f"edges:    {len(edges)}  "
          f"({sum(1 for e in edges if e['kind']=='composes')} composes, "
          f"{sum(1 for e in edges if e['kind']=='denotes')} denotes)")

    # round-trip proof
    ok = True
    for src, path in SOURCES:
        original = load_cards(path)
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
