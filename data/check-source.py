#!/usr/bin/env python3
"""Source-integrity gate for the authored layer: data/symbols/*.json + words.json.

These are the hand-authored tier — the one the build faithfully *projects* rather
than validates, so a mistake here rides straight into the graph as a node that is
internally consistent but silently wrong (the round-trip proof still passes, the
deploy check still passes). This asserts the invariants the build ASSUMES, so an
authoring slip fails HERE with a clear locus instead of surfacing downstream as a
puzzling frontier node or a missing referent.

Structural only. A glyph's parts are its authored `composes` field, which build-graph
reads directly — so the old under-integration failure (a symbol landing with no parts
because a regenerated decomposition.json went stale) can no longer happen, and its gate
is gone. `composes` is validated in-place instead (a list of single glyphs, no
self-loop). Says nothing about whether generated files are current (that is re-running
the build) or what the box serves (that is check-deploy) — see those for the other two
seams in symbols -> build -> generated -> deployed.

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
from symbols_io import PROGRAM_TIERS, referent_slug, _as_list

TIER_BY_KEY = {(t["source"], t["role"]): t for t in PROGRAM_TIERS}
CLASSES = {"char", "comp", "stroke"}
AUDIENCES = {"cn", "jp"}
KINDS = {"meaning", "mnemonic"}
KANGXI_MAX = 214
REPRESENTATIONS = {"image", "sound", "motion", "scene", "sentence", "diagram"}


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


def _check_script_form(rep, where, key, form):
    """A `simplified`/`traditional` slot: a non-empty list of {glyph, when?}."""
    if not isinstance(form, list) or not form:
        rep.err(where, f"script.{key} must be a non-empty list of entries")
        return
    for e in form:
        if not isinstance(e, dict) or not _str(e.get("glyph")) or len(e["glyph"]) != 1:
            rep.err(where, f"script.{key} entry needs a single-char 'glyph'")
        elif "when" in e and not _str(e["when"]):
            rep.err(where, f"script.{key} 'when' must be a non-empty string")


def check_script(rep, where, script):
    """Validate a symmetric `script` block (docs/traditional-script.md). `keyed`
    names the axis the card `glyph` sits on (simplified|traditional|shinjitai,
    default simplified); the *other* Han form(s) are named under `simplified` /
    `traditional`, or `same: true` declares the two Han forms coincide."""
    if not isinstance(script, dict):
        rep.err(where, "script must be an object")
        return
    keyed = script.get("keyed", "simplified")
    if keyed not in ("simplified", "traditional", "shinjitai"):
        rep.err(where, f"script.keyed {keyed!r} not in ('simplified', 'traditional', 'shinjitai')")
    same = script.get("same")
    if same is not None and same is not True:
        rep.err(where, "script.same must be true when present")
    # the keyed Han axis IS the glyph — don't restate it as a named slot
    if keyed in ("simplified", "traditional") and keyed in script:
        rep.err(where, f"script.{keyed} restates the keyed glyph — omit it")
    named = [k for k in ("simplified", "traditional") if k in script]
    if same:
        if named:
            rep.err(where, "script.same is exclusive with a named simplified/traditional form")
        if keyed == "shinjitai":
            rep.err(where, "script.same needs a Han-keyed glyph, not shinjitai")
    elif not named:
        rep.err(where, "script needs `same: true` or a named simplified/traditional form")
    for k in named:
        _check_script_form(rep, where, k, script[k])


def check_senses(rep, where, s):
    """Validate the optional `senses[]` (docs/sense-model.md): the glyph's NON-PRIMARY
    senses, each a bundle of (gloss, denotes, per-language reading). Sense 0 IS the
    `readings.{cn,jp}` block and is not repeated here — so `senses[]` starts at sense 1.

    Two invariants:
      · SHAPE — each sense carries a non-empty gloss + denotes; a declared cn/jp block
        is an object whose `reading` is a non-empty string or a non-empty list of
        non-empty strings (a list = polyphony within the one sense).
      · COUPLING (gated inheritance) — a sense may OMIT language L only when the glyph
        is monophonic in L. If L carries >1 distinct reading across sense 0 + the
        explicit sense readings, every non-primary sense MUST declare its own L reading:
        omitting it would silently inherit sense 0's sound onto a sense that sounds
        different — the exact 多音字 slip the sense model exists to catch."""
    senses = s.get("senses")
    if senses is None:
        return
    if not isinstance(senses, list) or not senses:
        rep.err(where, "senses must be a non-empty list when present")
        return

    base = s.get("readings") or {}
    distinct = {"cn": set(), "jp": set()}   # every reading seen for L, sense 0 + explicit
    omitted = {"cn": False, "jp": False}    # did SOME sense inherit L (omit it)?
    for lang in ("cn", "jp"):
        for x in _as_list((base.get(lang) or {}).get("reading")):
            if _str(x):
                distinct[lang].add(x)

    for j, sense in enumerate(senses):
        sw = f"{where} sense[{j + 1}]"
        if not isinstance(sense, dict):
            rep.err(sw, "sense must be an object")
            continue
        if not _str(sense.get("gloss")):
            rep.err(sw, "gloss missing or empty")
        if not _str(sense.get("denotes")):
            rep.err(sw, "denotes missing or empty")
        for lang in ("cn", "jp"):
            block = sense.get(lang)
            if block is None:
                omitted[lang] = True
                continue
            if not isinstance(block, dict):
                rep.err(sw, f"{lang} must be an object")
                continue
            vals = _as_list(block.get("reading"))
            if not vals or not all(_str(x) for x in vals):
                rep.err(sw, f"{lang}.reading must be a non-empty string or list of strings")
                continue
            distinct[lang].update(vals)

    for lang in ("cn", "jp"):
        if omitted[lang] and len(distinct[lang]) > 1:
            rep.err(where, f"a sense omits {lang} but the glyph is polyphonic in {lang} "
                           f"({len(distinct[lang])} readings: "
                           f"{' '.join(sorted(distinct[lang]))}) — every non-primary "
                           f"sense must declare its own {lang} reading")


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
        if not isinstance(form.get("animated"), bool):
            rep.err(where, "form.animated must be a bool")
        elif form["animated"] and not (ROOT / "shared" / "hanzi-data" / f"{g}.json").exists():
            # animated promises a local stroke-data file — cards3/cardsJP fetch it to
            # animate the tile, so animated=True with no file is a 404 (a silent,
            # blank animation). The file may be native (fetch.py <glyph>) or lifted
            # from a parent (fetch.py --lift) — either way it must exist here.
            rep.err(where, "form.animated is true but shared/hanzi-data/<glyph>.json is missing")
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

    # composes: the glyph-level source of truth for composition edges (build-graph
    # reads it directly — no decomposition.json anymore). A part with no symbol of
    # its own is fine (it becomes a frontier node); a malformed list or a self-loop
    # is not. This is the seam the old decomposition-freshness gate protected, now
    # enforced at the source instead of on a regenerated side-file.
    composes = s.get("composes")
    if composes is not None:
        if not isinstance(composes, list) or not all(_str(c) and len(c) == 1 for c in composes):
            rep.err(where, "composes must be a list of single-glyph strings")
        elif g in composes:
            rep.err(where, "composes lists the glyph itself (a self-loop)")

    # simplified↔traditional block (docs/traditional-script.md). Shape is validated
    # WHEN PRESENT; there is deliberately no repo-wide "unclassified" gate yet, so a
    # symbol without `script` is silent (backfill is incremental).
    if s.get("script") is not None:
        check_script(rep, where, s["script"])

    # non-primary senses (docs/sense-model.md) — shape + the polyphony coupling rule
    check_senses(rep, where, s)

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
            # A polysemous head denotes ANY of its senses (docs/sense-model.md): the
            # bare-glyph word may rejoin the primary gloss OR a non-primary sense's
            # referent (生 → r:life or r:raw), so hold it to the union, not just sense 0.
            want = {referent_slug(gloss)}
            want |= {sense["denotes"] for sense in head.get("senses") or []
                     if _str(sense.get("denotes"))}
            if _str(w.get("denotes")) and w["denotes"] not in want:
                rep.warn(where, f"denotes {w['denotes']!r} != head {parts[0]} "
                                f"referent(s) {' '.join(sorted(want))}")


def check_grounding(syms):
    """Referent sense-data coverage — the 'answer = sense-data, not a gloss' KPI.

    NOT a gate: a low number is a worklist (image sourcing), never an error, so it
    returns a stat rather than pushing 393 warnings. Counts the distinct referents
    the graph will denote — one per glyph (its gloss, matching build-graph) plus each
    word's `denotes` — and how many carry >=1 image in the curated data/referents.json
    overlay. The pages render the grounded ones (the 所指 panel); this is the COMPLEMENT
    — the aggregate and the gap the pages can't show you."""
    universe = set()
    for s in syms.values():
        v = s["readings"]
        r = referent_slug(v["cn"].get("gloss") or v["jp"].get("gloss", ""))
        if r:
            universe.add(r)
    wpath = DATA / "words.json"
    if wpath.exists():
        for w in json.loads(wpath.read_text(encoding="utf-8")).get("words", []):
            if _str(w.get("denotes")):
                universe.add(w["denotes"])

    refs = {}
    rpath = DATA / "referents.json"
    if rpath.exists():
        refs = json.loads(rpath.read_text(encoding="utf-8"))
    grounded = sum(1 for r in universe if refs.get(r, {}).get("images"))
    return grounded, len(universe)


def check_kangxi(rep):
    """The 214-radical spine (data/kangxi.json). build-pages projects it into the
    /kangxi/ deck; the /author/ imagery worklist reads it live to shade coverage.
    Validate the authored `representations` set — a typed modality declaration
    (image·sound·motion·scene·sentence·diagram) the tool trusts to route non-image
    referents away from the photo form. A missing, empty, or off-vocab list would
    mis-shade the worklist (a radical silently un-clickable, or a photo solicited for
    something that can't have one), so it fails HERE rather than at the tool."""
    path = DATA / "kangxi.json"
    if not path.exists():
        return
    for r in json.loads(path.read_text(encoding="utf-8")).get("radicals", []):
        where = f"kangxi.json #{r.get('num')} {r.get('glyph', '?')}"
        reps = r.get("representations")
        if not isinstance(reps, list) or not reps:
            rep.err(where, "representations must be a non-empty list")
            continue
        bad = [t for t in reps if t not in REPRESENTATIONS]
        if bad:
            rep.err(where, f"representations {bad} not in {sorted(REPRESENTATIONS)}")
        if len(set(reps)) != len(reps):
            rep.err(where, f"representations has duplicate tags: {reps}")


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
    check_kangxi(rep)

    for where, msg in rep.warns:
        print(f"⚠  {where}: {msg}")
    for where, msg in rep.errors:
        print(f"❌ {where}: {msg}")

    n_sym, n_err, n_warn = len(syms), len(rep.errors), len(rep.warns)
    print(f"\nchecked {n_sym} symbols · {n_err} error(s) · {n_warn} warning(s)")

    grounded, total = check_grounding(syms)
    pct = 100 * grounded // (total or 1)
    print(f"grounded referents: {grounded}/{total} ({pct}%) carry sense-data · "
          f"{total - grounded} still prose-only")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
