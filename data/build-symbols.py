#!/usr/bin/env python3
"""Carve the per-glyph SUBSTRATE + INSTANTIATIONS files out of the hand-authored
cards — the decoupling described in docs/content-graph-schema.md.

    radicals/radicals.json  ┐
    strokes/strokes.json    ┼─▶  data/symbols/<glyph>.json   (one per glyph)
    data/decomposition.json ┘

Each symbol file is bare form + composition (the substrate — adopted wholesale
from Unicode + Make-Me-a-Hanzi, custom only at the edges) plus a UNIFORM list of
program instantiations (WK/PD radical + kanji items) and the two native-language
readings. NO mnemonic / name / reading lives on the substrate; it all rides on
the instantiations, keyed by (source, lang, role) FIELDS — never nesting keys —
so projections stay a single linear pass.

Then ROUND-TRIPS: rebuilds each source card-file from the symbol files and checks
structural equality, proving the carve is lossless (same discipline as
build-graph.py). Additive + reversible: does not touch the card files or pages.

Run: python3 data/build-symbols.py
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "symbols"
SOURCES = [("radicals", ROOT / "radicals/radicals.json"),
           ("strokes",  ROOT / "strokes/strokes.json")]


def load_cards(path):
    d = json.loads(path.read_text())
    return [c for grp in d["groups"] for c in grp["cards"]]


def cp(glyph):
    """Canonical Unicode codepoint label. Every atom we use is a single
    codepoint (incl. astral 𠂉)."""
    return "U+%04X" % ord(glyph)


# ── forward: card → symbol file ─────────────────────────────────────────────
def to_symbol(c, source, decomp):
    g = c["glyph"]
    sym = {
        "glyph": g,
        "cp": cp(g),
        "slug": c["slug"],
        "class": c["tag"],                 # stroke | comp | char  (structural)
        "source": source,                  # authoring collection / page hint
        "form": {"hw": c.get("hw", False), "image": c.get("image", "")},
    }
    if g in decomp:
        sym["composes"] = decomp[g]        # structural parts (MMAH IDS + overrides)

    # native-language readings — the fixed two-key binding, not part of the
    # (source × lang × role) program cross-product, so kept as a symmetric map.
    sym["readings"] = {"cn": dict(c["cn"]), "jp": dict(c["jp"])}

    # programs — the uniform instantiation list. role/source/lang are FIELDS.
    progs = []
    wk = c.get("wk")
    if wk:
        p = {"source": "wanikani", "lang": "jp", "role": "radical",
             "name": wk["name"], "kind": wk["kind"], "level": wk["level"]}
        if wk.get("glyph"):
            p["altglyph"] = wk["glyph"]
        if wk.get("icon"):
            p["icon"] = wk["icon"]
        progs.append(p)
    k = c.get("kanji")
    if k:
        p = {"source": "wanikani", "lang": "jp", "role": "kanji",
             "name": k["name"], "readings": k.get("readings", []),
             "on": k.get("on", False), "level": k.get("level", 1)}
        if k.get("kun"):
            p["kun"] = k["kun"]
        progs.append(p)
    pd = c.get("pd")
    if pd:
        p = {"source": "pandanese", "lang": "cn", "role": "radical",
             "name": pd["name"], "kind": pd["kind"], "level": pd["level"]}
        if pd.get("icon"):
            p["icon"] = pd["icon"]
        progs.append(p)
    sym["programs"] = progs
    return sym


# ── reverse: symbol file → card (the round-trip proof) ──────────────────────
def to_card(sym):
    prog = {(p["source"], p["role"]): p for p in sym.get("programs", [])}
    card = {
        "glyph": sym["glyph"],
        "slug": sym["slug"],
        "tag": sym["class"],
        "image": sym["form"]["image"],
        "hw": sym["form"]["hw"],
        "cn": sym["readings"]["cn"],
        "jp": sym["readings"]["jp"],
    }
    wkp = prog.get(("wanikani", "radical"))
    if wkp:
        wk = {"name": wkp["name"], "level": wkp["level"], "kind": wkp["kind"]}
        if "altglyph" in wkp:
            wk["glyph"] = wkp["altglyph"]
        if "icon" in wkp:
            wk["icon"] = wkp["icon"]
        card["wk"] = wk
    else:
        card["wk"] = None
    kp = prog.get(("wanikani", "kanji"))
    if kp:
        k = {"name": kp["name"], "readings": kp["readings"],
             "on": kp["on"], "level": kp["level"]}
        if "kun" in kp:
            k["kun"] = kp["kun"]
        card["kanji"] = k
    pdp = prog.get(("pandanese", "radical"))
    if pdp:
        pd = {"name": pdp["name"], "level": pdp["level"], "kind": pdp["kind"]}
        if "icon" in pdp:
            pd["icon"] = pdp["icon"]
        card["pd"] = pd
    return card


def main():
    decomp = {}
    dp = DATA / "decomposition.json"
    if dp.exists():
        decomp = json.loads(dp.read_text())

    OUT.mkdir(exist_ok=True)
    symbols = {}          # glyph -> symbol dict
    order = {}            # source -> [glyph...] in card order (for round-trip)
    for source, path in SOURCES:
        order[source] = []
        for c in load_cards(path):
            g = c["glyph"]
            if g in symbols:
                print(f"! duplicate glyph across sources: {g}")
                return 1
            symbols[g] = to_symbol(c, source, decomp)
            order[source].append(g)

    for g, sym in symbols.items():
        (OUT / f"{g}.json").write_text(
            json.dumps(sym, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {len(symbols)} symbol files → {OUT.relative_to(ROOT)}/")
    withcomp = sum(1 for s in symbols.values() if s.get("composes"))
    nprog = sum(len(s["programs"]) for s in symbols.values())
    print(f"  {withcomp} with composition · {nprog} program instantiations")

    # round-trip proof: rebuild each card file from the symbol files
    ok = True
    for source, path in SOURCES:
        original = load_cards(path)
        rebuilt = [to_card(symbols[g]) for g in order[source]]
        if original == rebuilt:
            print(f"round-trip {source+'.json':16} ✓  ({len(rebuilt)} cards identical)")
        else:
            ok = False
            print(f"round-trip {source+'.json':16} ✗  MISMATCH")
            for o, r in zip(original, rebuilt):
                if o != r:
                    diff = sorted(set(o) | set(r))
                    diff = [k for k in diff if o.get(k) != r.get(k)]
                    print(f"    {o['glyph']}: differs in {diff}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
