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


# ── page-membership rules — one axis per rule ────────────────────────────────
# The old on_radicals unioned three distinct axes (Kangxi ∪ component ∪ "a program
# teaches it as a radical") into one muddle. Untangled: each axis is its own rule,
# and program-radical NO LONGER drives membership — that a course happens to teach
# 七/上/メ as a "radical" is an accident of the course, not a fact about the glyph,
# so it stays only as a per-card annotation (to_card still surfaces the WK item).
def on_strokes(sym):
    return sym["class"] == "stroke"


def on_kangxi(sym):
    """The canonical 214 Kangxi radicals — the principled 'radical' axis. A glyph
    is here iff it carries a Kangxi number (亠 is #8, so it stays; 七/上/千/才 fall
    off — WK-radical ≠ Kangxi-radical). The /kangxi/ page joins these to the 214
    reference spine by number; see data/kangxi.json + build-pages."""
    return bool(sym.get("kangxi"))


def on_components(sym):
    """Non-Kangxi structural components — the small residue of building-block
    shapes that are neither Kangxi radicals, standalone chars, nor single strokes
    (ナ ト メ 𠂉). Surfaced as the annex on /kangxi/."""
    return sym["class"] == "comp" and not sym.get("kangxi")


def on_characters(sym):
    """The full standalone-character inventory. Overlaps /kangxi/ for chars that
    are also Kangxi radicals (大, 木, 口) — one symbol, two projected views.
    Excludes `form_only` stubs — the CN-first Kangxi promotion (glyph + reading +
    stroke data, no JP/programs/examples yet) shows only on /kangxi/ until a
    content pass fleshes it out, so /characters/ stays a curated real-card deck."""
    return sym["class"] == "char" and not sym.get("form_only")


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
