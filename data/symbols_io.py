#!/usr/bin/env python3
"""Shared substrate access + projection helpers.

data/symbols/<glyph>.json is now the SOURCE OF TRUTH (bare form + composition +
a uniform program-instantiation list). Everything else — the page card files and
the content graph — is projected from it. This module holds the loader, the
symbol→card projection, and the page-membership rules so build-pages.py and
build-graph.py agree on one definition.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYM = ROOT / "data" / "symbols"


def load_symbols():
    """Ordered {glyph: symbol} following data/symbols/_spine.json (the editorial
    order); any file missing from the spine is appended sorted, so nothing is
    silently dropped."""
    spine = json.loads((SYM / "_spine.json").read_text())["order"]
    files = {f.stem: f for f in SYM.glob("*.json") if not f.name.startswith("_")}
    order = [g for g in spine if g in files] + sorted(set(files) - set(spine))
    return {g: json.loads(files[g].read_text()) for g in order}


# ── page-membership rules (replace the old per-file 'source') ────────────────
def has_radical_program(sym):
    return any(p["role"] == "radical" for p in sym.get("programs", []))


def on_strokes(sym):
    return sym["class"] == "stroke"


def on_radicals(sym):
    """Components, Kangxi radicals, and anything a program teaches AS a radical.
    A standalone character that is none of these (泉, 線, 三) is not a radical."""
    if sym["class"] == "stroke":
        return False
    if sym["class"] == "comp":
        return True
    return bool(sym.get("kangxi")) or has_radical_program(sym)


def on_characters(sym):
    """The full standalone-character inventory. Overlaps /radicals/ for chars
    that are also radicals (才, 一) — one symbol, two projected views."""
    return sym["class"] == "char"


# ── symbol → card (the lang-pages presentation shape) ───────────────────────
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
