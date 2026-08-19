#!/usr/bin/env python3
"""Build the data-layer content graph from the symbol source of truth.

Ingests `data/symbols/*.json` (via symbols_io.load_symbols) plus the curated
side-inputs (composition-roles.json, words.json) and emits
the canonical graph:
    data/nodes.json      glyph nodes + referent stubs + frontier stubs
    data/bindings.json   one CN + one JP binding per glyph (WK metadata → JP binding)
    data/edges.json      composes (part→whole) + denotes (glyph→referent stub)

Then ROUND-TRIPS: regenerates each source card projection from the graph and
checks structural equality — proving the cards are just a projection of the graph.

Run: python3 data/build-graph.py
Schema: docs/content-graph-schema.md
"""
import sys
from itertools import combinations

from paths import DATA, read_json, write_json
from phonetics import sentence_key, word_key
from phonetics_jp import kana_key
from symbols_io import (
    load_symbols,
    to_card,
    card_audio_keys,
    referent_slug,
    bind_programs,
    unbind_programs,
)
TIER = {"stroke": "stroke", "comp": "component", "char": "char"}
TAG = {v: k for k, v in TIER.items()}
ROLE_VALUES = {"semantic", "phonetic", "form"}  # functional role of a part in a whole
AUDIO_LANGS = {"cn", "jp"}                        # languages the sentence bank can voice
# Authored enrichment edges all share ONE graph kind, `association` (soft, symmetric,
# non-gating — docs/authored-edges.md), discriminated by `type` (the relation) and
# `basis` (the reason — a render hint; traversal/gating are identical across bases).
# The two axes are orthogonal: a pair can be confusable (form/sound/sense MIX-UP, a
# warning), cognate (shared ORIGIN, enrichment), both (西/襾), or neither. Each type
# owns a cluster-id prefix + its own basis vocabulary; a basis from one type is not
# valid on another. Glossary: docs/glossary.md.
ASSOCIATION_KIND = "association"
ASSOCIATION_TYPES = {
    "confusable": {"prefix": "cf", "basis": {"visual", "phonetic", "semantic"}},
    "cognate": {"prefix": "cg", "basis": {"historical", "etymological", "orthographic"}},
}


def load_roles():
    """Hand-curated functional role overlay (char → comp → role). Separate from
    the `composes` structure (WHICH parts) — this is the WHAT-each-part-does layer,
    overlaid onto the composition edges by role_of()."""
    p = DATA / "composition-roles.json"
    if not p.exists():
        return {}
    return {c: m for c, m in read_json(p).items() if not c.startswith("_")}


def load_authored():
    """Hand-authored enrichment layer — relations the substrate cannot derive
    (association edges: confusable / cognate). Absent file → no-op, like words.json.
    Schema: docs/authored-edges.md; glossary: docs/glossary.md."""
    p = DATA / "authored.json"
    if not p.exists():
        return {"edges": [], "nodes": []}
    d = read_json(p)
    return {"edges": d.get("edges", []), "nodes": d.get("nodes", [])}


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
    nodes, bindings, edges, clusters = {}, [], [], []
    seen_edge = set()
    symbols = load_symbols()
    real = set(symbols)

    # variant folding: a twin form (覀→西, ナ→𠂇), declared as `variants` on its
    # canonical symbol, composes AS its canonical — so a whole shows ONE part chip.
    # The twin survives as a `variant` edge + a `variants` badge on the canonical
    # node, never as a duplicate part. A twin with no symbol of its own (覀) simply
    # stops minting a frontier stub once its only edge folds onto the canonical.
    variant_of = {}           # twin glyph → canonical glyph
    canon_variants = {}       # canonical glyph → [twin glyphs]
    for sym in symbols.values():
        for v in sym.get("variants") or []:
            variant_of[v] = sym["glyph"]
            canon_variants.setdefault(sym["glyph"], []).append(v)

    def canon(gl):
        return variant_of.get(gl, gl)

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
                "tier": TIER[c["tag"]], "source": src,
                "media": {"animated": c.get("animated", False), "image": c.get("image", "")},
                # content-keyed bank keys for the graph detail panel (renderCard →
                # cnSrc/jpSrc). NOT part of the round-tripped card — stamped on the
                # node only. Same definition build-pages uses, so they can't drift.
                **card_audio_keys(c["cn"], c["jp"]),
            }
            if "script" in c:                 # simplified↔traditional (round-tripped)
                nodes[f"g:{g}"]["script"] = c["script"]
            bindings.append(make_binding(g, "cn", c["cn"], c))
            bindings.append(make_binding(g, "jp", c["jp"], c))

            # denotes → bare referent stub, keyed by the ASCII meaning-slug so the
            # concept spine carries no CN/JP bias; the full gloss rides as label.
            gloss = c["cn"].get("gloss") or c["jp"].get("gloss", "")
            rid = f"r:{referent_slug(gloss)}"
            nodes.setdefault(rid, {"id": rid, "kind": "referent", "label": gloss})
            edges.append({"from": f"g:{g}", "to": rid, "kind": "denotes"})

            # composes ← example chars (union CN+JP, dedup); seed frontier stubs.
            # The part (this glyph) folds onto its canonical twin, if any.
            gsrc = canon(g)
            for v in (c["cn"], c["jp"]):
                ai = v.get("appearsIn")
                if not ai:
                    continue
                tgt = ai["char"]
                if (gsrc, tgt) not in seen_edge:
                    seen_edge.add((gsrc, tgt))
                    edges.append(cedge(f"g:{gsrc}", f"g:{tgt}", role_of(tgt, gsrc)))
                if tgt not in real:
                    nodes.setdefault(f"g:{tgt}", {
                        "id": f"g:{tgt}", "kind": "glyph", "glyph": tgt,
                        "tier": None, "frontier": True})

    # structural composition edges (component → char) from each symbol's authored
    # `composes` — the glyph-level source of truth (男 ← 田 力, 合 ← 𠆢 一 口). A part
    # with no symbol of its own becomes a frontier node. (MMAH is now only an
    # authoring aid for filling `composes`; see data/fetch-decomp.py.)
    for char, sym in symbols.items():
        for comp in sym.get("composes") or []:
            csrc = canon(comp)   # fold twin part onto its canonical (覀 → 西)
            if (csrc, char) not in seen_edge:
                seen_edge.add((csrc, char))
                edges.append(cedge(f"g:{csrc}", f"g:{char}", role_of(char, csrc)))
            if csrc not in real:
                nodes.setdefault(f"g:{csrc}", {
                    "id": f"g:{csrc}", "kind": "glyph", "glyph": csrc,
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
            # audience is part of the id (like a binding's b:<glyph>@<lang>) so a
            # JP and CN word sharing a surface — 大人 おとな vs dàrén — are the two
            # distinct nodes the fork intends, not one silently overwriting the other.
            wid = f"w:{w['surface']}@{w['audience']}"
            node = {"id": wid, "kind": "word", "tier": "word",
                    "audience": w["audience"], "glyph": w["surface"],
                    "reading": w.get("reading", ""),
                    "gloss": w.get("gloss", "")}
            if w.get("okurigana"):
                node["okurigana"] = w["okurigana"]
            if w.get("program"):
                node["program"] = w["program"]
            # A word carries its own audio key so the dossier can play the shared
            # whole-word clip: JP romaji → /audio/jp/<key>.mp3, CN pinyin base →
            # /audio/cn/<key>.mp3 (a single-hanzi CN word reuses its glyph's syllable
            # clip). Both banks are projected from words.json in gen-audio.
            if w["audience"] == "jp" and (k := kana_key(w.get("reading"))):
                node["jpAudioKey"] = k
            elif w["audience"] == "cn" and (k := word_key(w["surface"], w.get("reading"))):
                node["cnAudioKey"] = k
            nodes[wid] = node
            for part in w.get("parts", []):
                psrc = canon(part)   # fold twin part onto its canonical
                if (psrc, wid) not in seen_edge:  # per-word (audience-scoped), not per-surface
                    seen_edge.add((psrc, wid))
                    edges.append(cedge(f"g:{psrc}", wid))
                if psrc not in real:
                    nodes.setdefault(f"g:{psrc}", {
                        "id": f"g:{psrc}", "kind": "glyph", "glyph": psrc,
                        "tier": None, "frontier": True})
            if w.get("denotes"):
                # A single-glyph word rejoins its head glyph's referent (already
                # minted by the glyph card). A compound word (二人) denotes a
                # referent no glyph card owns, so the word mints it here.
                rid = f"r:{w['denotes']}"
                nodes.setdefault(rid, {"id": rid, "kind": "referent",
                                       "label": w.get("gloss", "")})
                edges.append({"from": wid, "to": rid, "kind": "denotes"})

    # variant relation: the canonical node advertises its twin forms (UI collapses
    # them to a badge); a twin that is itself a real symbol (ナ, carrying WK Narwhal)
    # also gets a variant→canonical edge so the two program lenses stay linked.
    for canonical, twins in canon_variants.items():
        node = nodes.get(f"g:{canonical}")
        if node is not None:
            node["variants"] = twins
        for v in twins:
            if v in real:
                edges.append({"from": f"g:{v}", "to": f"g:{canonical}", "kind": "variant"})

    # ── authored enrichment layer (docs/authored-edges.md) ──────────────────────
    # Human-asserted relations the substrate cannot derive. Purely ADDITIVE to
    # edges.json — no card projects them, so the round-trip proof is untouched.
    # ENDPOINT-AGNOSTIC: a ref may name a glyph, a word or an authored entity, so the
    # kind never forks by endpoint type — 人/入 (glyph), 可不/不可 (word) and an authored
    # entity pair are all one `association` kind (the `type` says which relation). Runs
    # last: every node it can point at (glyph, frontier, referent, word) is minted by now.
    authored = load_authored()
    for n in authored["nodes"]:
        nodes.setdefault(n["id"], {"id": n["id"], "kind": "entity",
                                   "label": n.get("label", "")})

    def resolve(ref, audience, where):
        """bare glyph → g:人 · word surface + entry audience → w:可不@cn · explicit id → itself."""
        if ":" in ref:
            rid = ref
        elif len(ref) == 1:                      # one codepoint → a glyph
            rid = f"g:{ref}"
        elif audience:
            rid = f"w:{ref}@{audience}"
        else:
            print(f"⚠ authored[{where}]: {ref!r} is multi-char but the entry declares no "
                  f"`audience` to resolve it as a word (or give an explicit id)", file=sys.stderr)
            return None
        if rid not in nodes:
            print(f"⚠ authored[{where}]: {ref!r} → {rid} matches no node (typo?)", file=sys.stderr)
            return None
        return rid

    for i, a in enumerate(authored["edges"]):
        where = "/".join(a.get("between", [])) or f"#{i}"
        aud = a.get("audience")
        atype = a.get("type")
        if atype not in ASSOCIATION_TYPES:
            print(f"⚠ authored[{where}]: unknown association type {atype!r} "
                  f"(expected {sorted(ASSOCIATION_TYPES)})", file=sys.stderr)
            continue
        basis = a.get("basis")
        if basis and basis not in ASSOCIATION_TYPES[atype]["basis"]:
            print(f"⚠ authored[{where}]: basis {basis!r} not valid for type {atype} "
                  f"(expected {sorted(ASSOCIATION_TYPES[atype]['basis'])})", file=sys.stderr)
            basis = None
        refs = [resolve(r, aud, where) for r in a.get("between", [])]
        if len(refs) < 2 or any(r is None for r in refs):
            print(f"⚠ authored[{where}]: skipped (needs ≥2 resolvable refs)", file=sys.stderr)
            continue
        # Grounding examples. `audioKey` is DERIVED, never authored — content-keyed off
        # (lang, text) by the same function gen-audio names the clip with, exactly as
        # cnAudioKey/jpAudioKey are stamped onto a card. An example with no resolvable
        # lang still renders its text; it just carries no key, and a null key already
        # means "hide the play button" (09774a9), so silence degrades cleanly.
        examples = []
        for ex in a.get("examples", []):
            tgt = resolve(ex["for"], aud, where)
            if tgt is None:
                continue
            lang = ex.get("lang") or a.get("lang") or aud
            if lang not in AUDIO_LANGS:
                print(f"⚠ authored[{where}]: example «{ex['text']}» has no lang "
                      f"({'|'.join(sorted(AUDIO_LANGS))}) — text shows, but it stays silent",
                      file=sys.stderr)
                lang = None
            examples.append({"for": tgt, "text": ex["text"], "gloss": ex.get("gloss", ""),
                             "lang": lang,
                             "audioKey": sentence_key(lang, ex["text"]) if lang else None})

        # Every association type is SYMMETRIC (unlike composes/variant) and N-ARY (己/已/巳 is a
        # three-way set, not three pairs that happen to coincide). So the shared payload
        # — basis/note/examples — is NORMALIZED onto a cluster record, and the graph gets
        # the pairwise clique of slim links pointing back at it by id.
        #
        # Clique (not a star through a reified cluster node) because the query a card asks
        # is "what does 已 confuse with?" — that stays a one-hop edge filter, and no
        # non-linguistic node leaks into nodes.json. Endpoints sorted so an edge is
        # order-independent: stable diffs, natural dedup.
        members = sorted(set(refs))
        cluster = f"{ASSOCIATION_TYPES[atype]['prefix']}:{i + 1}"
        clusters.append({"id": cluster, "kind": ASSOCIATION_KIND, "type": atype,
                         "members": members,
                         **({"basis": basis} if basis else {}),
                         **({"note": a["note"]} if a.get("note") else {}),
                         **({"examples": examples} if examples else {})})
        for x, y in combinations(members, 2):
            edges.append({"from": x, "to": y, "kind": ASSOCIATION_KIND, "type": atype,
                          "symmetric": True, "cluster": cluster, "source": "authored"})

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

    return list(nodes.values()), bindings, edges, clusters


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
            "glyph": g, "tag": TAG[n["tier"]],
            "image": n["media"]["image"], "animated": n["media"]["animated"],
            "cn": view(cn),
            "jp": view(jp),
        }
        if "script" in n:                     # inverse of to_card's passthrough
            card["script"] = n["script"]
        # recover the flat card tiers from each binding's `program` (inverse of the
        # bind_programs projection above) — one registry, both directions.
        card.update(unbind_programs(cn.get("program"), "cn"))
        card.update(unbind_programs(jp.get("program"), "jp"))
        cards.append(card)
    return cards


def main():
    nodes, bindings, edges, clusters = build()
    DATA.mkdir(exist_ok=True)
    # `clusters` rides as a sibling key in edges.json: the n-ary payload of an authored
    # relation, stored ONCE and referenced by each clique link's `cluster` id. Existing
    # consumers read `.edges` (an array) and are unaffected by the new key.
    for name, payload in [("nodes", {"nodes": nodes}),
                          ("bindings", {"bindings": bindings}),
                          ("edges", {"edges": edges, "clusters": clusters})]:
        write_json(DATA / f"{name}.json", payload)

    glyphs = [n for n in nodes if n["kind"] == "glyph"]
    entities = sum(1 for n in nodes if n["kind"] == "entity")
    print(f"nodes:    {len(nodes)}  "
          f"({sum(1 for n in glyphs if not n.get('frontier'))} real glyph, "
          f"{sum(1 for n in glyphs if n.get('frontier'))} frontier, "
          f"{sum(1 for n in nodes if n['kind']=='referent')} referent, "
          f"{sum(1 for n in nodes if n['kind']=='word')} word"
          + (f", {entities} entity" if entities else "") + ")")
    print(f"bindings: {len(bindings)}")
    composes = [e for e in edges if e["kind"] == "composes"]
    print(f"edges:    {len(edges)}  "
          f"({len(composes)} composes [{sum(1 for e in composes if e.get('role'))} typed], "
          f"{sum(1 for e in edges if e['kind']=='denotes')} denotes, "
          f"{sum(1 for e in edges if e['kind']=='variant')} variant, "
          f"{sum(1 for e in edges if e.get('type')=='confusable')} confusable, "
          f"{sum(1 for e in edges if e.get('type')=='cognate')} cognate "
          f"association in {len(clusters)} cluster{'' if len(clusters)==1 else 's'})")

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
