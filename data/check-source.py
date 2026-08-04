#!/usr/bin/env python3
"""Source-integrity gate for the authored layer: data/symbols/*.json + words.json.

These are the hand-authored tier — the one the build faithfully *projects* rather
than validates, so a mistake here rides straight into the graph as a node that is
internally consistent but silently wrong (the round-trip proof still passes, the
deploy check still passes). This asserts the invariants the build ASSUMES, so an
authoring slip fails HERE with a clear locus instead of surfacing downstream as a
puzzling frontier node or a missing referent.

Structural only. It says nothing about whether generated files are current (that is
re-running the build) or what the box serves (that is check-deploy) — see those for
the other two seams in symbols -> build -> generated -> deployed.

  python3 data/check-source.py        ·  exit 0 clean · 1 hard error(s) · 2 load failure

Hard errors block; warnings are smells that the build tolerates (an unresolved part
becomes a frontier node by design, a spine omission is appended sorted) but that are
usually mistakes worth seeing.
"""
import json
import sys

from paths import DATA, ROOT, SYM
from phonetics import cn_key
from phonetics_jp import kana_key
from symbols_io import PROGRAM_TIERS, referent_slug

TIER_BY_KEY = {(t["source"], t["role"]): t for t in PROGRAM_TIERS}
CLASSES = {"char", "comp", "stroke"}
AUDIENCES = {"cn", "jp"}
KINDS = {"meaning", "mnemonic"}
KANGXI_MAX = 214


class Report:
    """Two buckets: errors fail the gate, warnings only print."""

    def __init__(self):
        self.errors = []
        self.warns = []

    def err(self, where, msg):
        self.errors.append((where, msg))

    def warn(self, where, msg):
        self.warns.append((where, msg))


def _str(v):
    return isinstance(v, str) and v.strip() != ""


def check_reading_view(rep, where, view):
    """One CN or JP reading view: name + gloss required; appearsIn if present must
    itself carry char/reading/gloss. `reading` (the phonetic) is OPTIONAL — form-only
    Kangxi promotions carry a gloss but no reading yet, and the build tolerates it
    (card_audio_keys simply mints no clip)."""
    for k in ("name", "gloss"):
        if not _str(view.get(k)):
            rep.err(where, f"reading.{k} missing or empty")
    ai = view.get("appearsIn")
    if ai is not None:
        if not isinstance(ai, dict):
            rep.err(where, "appearsIn is not an object")
        else:
            for k in ("char", "reading", "gloss"):
                if not _str(ai.get(k)):
                    rep.err(where, f"appearsIn.{k} missing or empty")


def check_script(rep, where, script):
    """Validate a `script` block's shape (docs/traditional-script.md). `traditional`
    is either "same" (verified no divergence) or a non-empty list of {glyph, when?}
    entries; `role` if present tags a non-simplified primary axis (円)."""
    if not isinstance(script, dict):
        rep.err(where, "script must be an object")
        return
    role = script.get("role")
    if role is not None and role not in ("simplified", "shinjitai"):
        rep.err(where, f"script.role {role!r} not in ('simplified', 'shinjitai')")
    trad = script.get("traditional")
    if trad == "same":
        return
    if not isinstance(trad, list) or not trad:
        rep.err(where, 'script.traditional must be "same" or a non-empty list of entries')
        return
    for e in trad:
        if not isinstance(e, dict) or not _str(e.get("glyph")) or len(e["glyph"]) != 1:
            rep.err(where, "script.traditional entry needs a single-char 'glyph'")
        elif "when" in e and not _str(e["when"]):
            rep.err(where, "script.traditional 'when' must be a non-empty string")


def check_symbol(rep, g, s):
    where = f"symbols/{g}.json"

    if s.get("glyph") != g:
        rep.err(where, f"glyph field {s.get('glyph')!r} != filename {g!r}")
    want_cp = f"U+{ord(g):04X}"
    if s.get("cp") != want_cp:
        rep.err(where, f"cp {s.get('cp')!r} != codepoint {want_cp}")
    if s.get("class") not in CLASSES:
        rep.err(where, f"class {s.get('class')!r} not in {sorted(CLASSES)}")

    form = s.get("form")
    if not isinstance(form, dict):
        rep.err(where, "form missing or not an object")
    else:
        if not isinstance(form.get("hw"), bool):
            rep.err(where, "form.hw must be a bool")
        elif form["hw"] and not (ROOT / "shared" / "hanzi-data" / f"{g}.json").exists():
            # hw promises a local stroke-data file — cards3/cardsJP fetch it to animate
            # the tile, so hw=True with no file is a 404 (a silent, blank animation).
            rep.err(where, "form.hw is true but shared/hanzi-data/<glyph>.json is missing")
        if not isinstance(form.get("image"), str):
            rep.err(where, "form.image must be a string")

    readings = s.get("readings")
    if not isinstance(readings, dict):
        rep.err(where, "readings missing or not an object")
    else:
        for lang in ("cn", "jp"):
            view = readings.get(lang)
            if not isinstance(view, dict):
                rep.err(where, f"readings.{lang} missing or not an object")
            else:
                check_reading_view(rep, where, view)

    progs = s.get("programs")
    if not isinstance(progs, list):
        rep.err(where, "programs missing or not a list")
    else:
        for p in progs:
            key = (p.get("source"), p.get("role"))
            if key not in TIER_BY_KEY:
                rep.err(where, f"program {key} not a known (source, role) tier")
                continue
            if not _str(p.get("name")):
                rep.err(where, f"program {key} has no name")
            want_lang = TIER_BY_KEY[key]["lang"]
            if p.get("lang") != want_lang:
                rep.err(where, f"program {key} lang {p.get('lang')!r} != tier lang {want_lang!r}")
            if "kind" in p and p["kind"] not in KINDS:
                rep.err(where, f"program {key} kind {p['kind']!r} not in {sorted(KINDS)}")

    kx = s.get("kangxi")
    if kx is not None and not (isinstance(kx, int) and 1 <= kx <= KANGXI_MAX):
        rep.err(where, f"kangxi {kx!r} not an int in 1..{KANGXI_MAX}")

    variants = s.get("variants")
    if variants is not None and (not isinstance(variants, list)
                                 or not all(_str(v) for v in variants)):
        rep.err(where, "variants must be a list of non-empty glyph strings")

    # simplified↔traditional block (docs/traditional-script.md). Shape is validated
    # WHEN PRESENT; there is deliberately no repo-wide "unclassified" gate yet, so a
    # symbol without `script` is silent (backfill is incremental).
    if s.get("script") is not None:
        check_script(rep, where, s["script"])

    # audio: a reading the phonetics normaliser cannot key gets no voice clip.
    cn = (readings or {}).get("cn") or {}
    jp = (readings or {}).get("jp") or {}
    if _str(cn.get("reading")) and cn_key(cn["reading"]) is None:
        rep.warn(where, f"cn reading {cn['reading']!r} yields no audio key")
    if _str(jp.get("reading")) and kana_key(jp["reading"]) is None:
        rep.warn(where, f"jp reading {jp['reading']!r} yields no audio key")


def check_words(rep, syms):
    path = DATA / "words.json"
    if not path.exists():
        return
    words = json.loads(path.read_text(encoding="utf-8")).get("words", [])
    seen = {}
    for i, w in enumerate(words):
        surface = w.get("surface", f"#{i}")
        where = f"words.json[{i}] {surface}"
        for k in ("surface", "audience", "denotes", "reading", "gloss"):
            if not _str(w.get(k)):
                rep.err(where, f"{k} missing or empty")
        if w.get("audience") not in AUDIENCES:
            rep.err(where, f"audience {w.get('audience')!r} not in {sorted(AUDIENCES)}")
        parts = w.get("parts")
        # May be empty: a pure-kana word (おはよう, ホテル) has no glyph parts, it
        # only denotes a referent. Entries, when present, must be non-empty glyphs.
        if not isinstance(parts, list) or not all(_str(p) for p in parts):
            rep.err(where, "parts must be a list of glyph strings")
            parts = []

        key = (w.get("surface"), w.get("audience"))
        if key in seen:
            rep.err(where, f"duplicate (surface, audience) — also words.json[{seen[key]}]")
        else:
            seen[key] = i

        for p in parts:
            if p not in syms:
                rep.warn(where, f"part {p!r} has no symbol (becomes a frontier node)")
        # A word that IS the bare glyph (surface == its one part: 中, 手) should
        # rejoin that glyph's referent. Derived lexemes (上げる, 〜円) legitimately
        # denote something new, so they are not held to this.
        if len(parts) == 1 and w.get("surface") == parts[0] and parts[0] in syms:
            head = syms[parts[0]]
            gloss = (head["readings"]["cn"].get("gloss")
                     or head["readings"]["jp"].get("gloss", ""))
            want = referent_slug(gloss)
            if _str(w.get("denotes")) and w["denotes"] != want:
                rep.warn(where, f"denotes {w['denotes']!r} != head {parts[0]} referent {want!r}")


def check_cross(rep, syms):
    """Invariants across the whole set, not any single file."""
    by_kangxi = {}
    for g, s in syms.items():
        kx = s.get("kangxi")
        if isinstance(kx, int):
            by_kangxi.setdefault(kx, []).append(g)
    for kx, gs in sorted(by_kangxi.items()):
        if len(gs) > 1:
            # Warn, not fail: a Kangxi number can front a canonical + its variant
            # form (80 = 毋/母). The /kangxi/ page joins by number, so worth seeing —
            # but it may be intentional and modelled via `variants` instead.
            rep.warn("cross", f"kangxi #{kx} claimed by multiple glyphs: {' '.join(gs)}")

    # A variant twin folds onto its canonical as the SAME node, so it usually means
    # the same thing (厶/ム both 'private'). A divergent referent is a smell worth
    # seeing: either a deliberate shape-only fold (twin glossed by its own sense, e.g.
    # 襾 'cover' under 西 'west') or a look-alike that is really a CONFUSABLE, not a
    # variant (the カ/力 mistake). Flagged, not failed — the call is editorial.
    def ref_of(g):
        v = syms[g]["readings"]
        return referent_slug(v["cn"].get("gloss") or v["jp"].get("gloss", ""))

    for g, s in syms.items():
        for tw in s.get("variants") or []:
            if tw in syms and ref_of(tw) != ref_of(g):
                rep.warn(f"symbols/{g}.json",
                         f"variant {tw} denotes r:{ref_of(tw)} but canonical {g} is "
                         f"r:{ref_of(g)} — shape-only fold, or should it be a confusable?")

    # A spine entry with no symbol file is a dangling reference. The reverse (a file
    # not in the spine) is NOT flagged — load_symbols appends those sorted by design,
    # which is exactly how the promoted-but-unsequenced Kangxi radicals ride along.
    spine = set(json.loads((SYM / "_spine.json").read_text(encoding="utf-8"))["order"])
    for g in spine - set(syms):
        rep.warn("_spine.json", f"{g} listed but has no symbol file")


def main():
    syms, bad = {}, []
    for f in sorted(SYM.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            syms[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            bad.append((f.name, str(e)))
    if bad:
        for name, msg in bad:
            print(f"❌ symbols/{name}: invalid JSON — {msg}")
        return 2

    rep = Report()
    for g, s in syms.items():
        check_symbol(rep, g, s)
    check_words(rep, syms)
    check_cross(rep, syms)

    for where, msg in rep.warns:
        print(f"⚠  {where}: {msg}")
    for where, msg in rep.errors:
        print(f"❌ {where}: {msg}")

    n_sym, n_err, n_warn = len(syms), len(rep.errors), len(rep.warns)
    print(f"\nchecked {n_sym} symbols · {n_err} error(s) · {n_warn} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
