#!/usr/bin/env python3
"""Shared substrate access + projection helpers.

data/symbols/<glyph>.json is now the SOURCE OF TRUTH (bare form + composition +
a uniform program-instantiation list). Everything else — the page card files and
the content graph — is projected from it. This module holds the loader, the
symbol→card projection, and the page-membership rules so build-pages.py and
build-graph.py agree on one definition.
"""
import re

from paths import ROOT, DATA, SYM, read_json  # noqa: F401  (ROOT/DATA re-exported)
from phonetics import cn_key
from phonetics_jp import kana_key


def referent_slug(gloss):
    """Canonical ASCII key for a meaning — the language-neutral referent id shared
    by every glyph that denotes it (so a curated referent image is looked up once,
    not per-glyph). First sense, parentheticals dropped, leading 'to ' dropped."""
    s = re.sub(r"\(.*?\)", "", gloss.split(";")[0]).strip().lower()
    s = re.sub(r"^to\s+", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def load_symbols():
    """Ordered {glyph: symbol} following data/symbols/_spine.json (the editorial
    order); any file missing from the spine is appended sorted, so nothing is
    silently dropped."""
    spine = read_json(SYM / "_spine.json")["order"]
    files = {f.stem: f for f in SYM.glob("*.json") if not f.name.startswith("_")}
    order = [g for g in spine if g in files] + sorted(set(files) - set(spine))
    return {g: read_json(files[g]) for g in order}


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


# ── source-program tiers: single source of truth ────────────────────────────
# A glyph's programs[] entries (keyed by source+role) project onto flat card
# fields and, in the graph, nest back onto a per-language `program` object. Each
# tier is described ONCE here; to_card + bind_programs/unbind_programs (below) and
# build-pages.emit_card all derive from it, so adding a tier (e.g. a WK/PD vocab
# item) is a single row rather than a parallel edit at four hand-rolled sites.
#   card    flat card-field name (wk/kanji/pd/pdc)
#   lang    which language binding the tier rides on (WK=jp, Pandanese=cn)
#   nest    None → the tier's fields flatten onto `program`; else nested under
#           program[nest] (WK ships radical+kanji, Pandanese radical+character —
#           the primary/radical tier flattens, the single-glyph tier nests)
#   fields  card-side field names, in canonical emit order; absent ones are skipped
#   rename  card-field → symbol/graph-field, for the lone altglyph↔glyph mismatch
#   always  card always carries this key (None when absent) — only the WK radical
PROGRAM_TIERS = [
    {"source": "wanikani", "role": "radical", "lang": "jp", "card": "wk",
     "nest": None, "fields": ["name", "level", "kind", "glyph", "icon"],
     "rename": {"glyph": "altglyph"}, "always": True},
    {"source": "wanikani", "role": "kanji", "lang": "jp", "card": "kanji",
     "nest": "kanji", "fields": ["name", "readings", "on", "kun", "level"]},
    {"source": "pandanese", "role": "radical", "lang": "cn", "card": "pd",
     "nest": None, "fields": ["name", "level", "kind", "icon"]},
    {"source": "pandanese", "role": "character", "lang": "cn", "card": "pdc",
     "nest": "character", "fields": ["name", "kind", "level"]},
]
TIER_BY_CARD = {t["card"]: t for t in PROGRAM_TIERS}


def _pick(entry, src):
    """Copy `entry`'s fields out of dict `src`, applying the card↔store rename and
    skipping absent (optional) fields. Same mapping both directions — the store key
    for card-field f is rename[f], whether `src` is a symbol program or a graph one."""
    rn = entry.get("rename", {})
    return {f: src[rn.get(f, f)] for f in entry["fields"] if rn.get(f, f) in src}


# ── symbol → card (the lang-pages presentation shape) ───────────────────────
def to_card(sym):
    prog = {(p["source"], p["role"]): p for p in sym.get("programs", [])}
    card = {
        "glyph": sym["glyph"],
        "tag": sym["class"],
        "image": sym["form"]["image"],
        "hw": sym["form"]["hw"],
        "cn": sym["readings"]["cn"],
        "jp": sym["readings"]["jp"],
    }
    # script correspondence (simplified↔traditional); orthographic, not a tier —
    # see docs/traditional-script.md. Passed through so both projections carry it.
    if "script" in sym:
        card["script"] = sym["script"]
    for t in PROGRAM_TIERS:
        p = prog.get((t["source"], t["role"]))
        if p:
            card[t["card"]] = _pick(t, p)
        elif t.get("always"):
            card[t["card"]] = None
    return card


def card_audio_keys(cn, jp):
    """A card/node's content-keyed audio bank keys, from its CN/JP reading views:
    cnAudioKey/cnExAudioKey → /audio/cn/, jpAudioKey/jpExAudioKey → /audio/jp/. Keyed
    by *sound* (千→qian1, セン→sen), never the glyph — which is why the per-symbol slug
    is gone. The ONE definition, so build-pages (cards) and build-graph (graph-panel
    nodes) never drift. Returns only the keys that exist — a readingless view
    contributes nothing (cards3.js gates the play button on a reading)."""
    cn, jp = cn or {}, jp or {}
    out = {}
    if k := cn_key(cn.get("reading")):
        out["cnAudioKey"] = k
    if k := cn_key((cn.get("appearsIn") or {}).get("reading")):
        out["cnExAudioKey"] = k
    if k := kana_key(jp.get("reading")):
        out["jpAudioKey"] = k
    if k := kana_key((jp.get("appearsIn") or {}).get("reading")):
        out["jpExAudioKey"] = k
    return out


# ── card ⇄ graph `program` object (the two inverse graph projections) ────────
def bind_programs(lang, card):
    """Assemble the per-language `program` object for a binding from card fields:
    the radical tier flattens onto it, the single-glyph tier nests under its key."""
    prog, source = {}, None
    for t in PROGRAM_TIERS:
        if t["lang"] != lang:
            continue
        val = card.get(t["card"])
        if not val:
            continue
        source = t["source"]
        if t["nest"] is None:
            rn = t.get("rename", {})
            for f in t["fields"]:
                if f in val:
                    prog[rn.get(f, f)] = val[f]
        else:
            prog[t["nest"]] = {f: val[f] for f in t["fields"] if f in val}
    return {"source": source, **prog} if source else None


def unbind_programs(program, lang):
    """Inverse of bind_programs: recover the flat card fields from a binding's
    `program`. Presence of a top-level `name` marks the radical tier as present
    (a program carrying only the nested tier has none)."""
    out = {}
    for t in PROGRAM_TIERS:
        if t["lang"] != lang:
            continue
        val = None
        if program and program.get("source") == t["source"]:
            if t["nest"] is None:
                if "name" in program:
                    val = _pick(t, program)
            elif program.get(t["nest"]):
                val = {f: program[t["nest"]][f] for f in t["fields"]
                       if f in program[t["nest"]]}
        if val is not None:
            out[t["card"]] = val
        elif t.get("always"):
            out[t["card"]] = None
    return out
