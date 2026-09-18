#!/usr/bin/env python3
"""Triage a pasted batch of program items before ingesting them.

Read-only: reports where each item already stands in the graph, so a WK/PD batch
can be sorted into tag-only / frontier-fill / new-card / word before any file is
touched. Nothing is written.

    python3 data/triage.py 虫 見 人生 〜台        # items as args
    pbpaste | python3 data/triage.py              # or whitespace-separated on stdin
    python3 data/triage.py --offline 名           # skip the stroke-data CDN probe

A single character is a GLYPH:
  CARD      has data/symbols/<g>.json — shows class/form_only, program tags,
            authored composes, referent and words using it
  FRONTIER  referenced as a part but not carded yet — shows who uses it
  NEW       not in the graph at all
  …plus the MMAH parts suggestion (each part's own status) and stroke data
  (local file, else whether the hanzi-writer CDN has it).
Anything longer is a WORD: existing entries with that surface (either audience),
and each non-kana character's glyph status.

Run after `python3 data/build.py` so nodes.json (frontier, referents) is fresh.
"""
import importlib.util
import sys
import urllib.parse
import urllib.request

from paths import DATA, ROOT, read_json
from symbols_io import load_symbols, referent_slug

CDN = "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2/{}.json"
HANZI = ROOT / "shared" / "hanzi-data"
SHORT = {"wanikani": "WK", "pandanese": "PD"}


def load_decomp():
    """fetch-decomp.py's suggest(), imported by path (its name has a hyphen)."""
    spec = importlib.util.spec_from_file_location("fetch_decomp", DATA / "fetch-decomp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.suggest


def is_kana(ch):
    return "぀" <= ch <= "ヿ" or ch in "〜~ー・"


def cdn_has(glyph):
    req = urllib.request.Request(CDN.format(urllib.parse.quote(glyph)), method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


class Graph:
    def __init__(self):
        self.symbols = load_symbols()
        nodes = read_json(DATA / "nodes.json")["nodes"]
        self.frontier = {n["glyph"] for n in nodes if n["kind"] == "glyph" and n.get("frontier")}
        self.referents = {n["id"] for n in nodes if n["kind"] == "referent"}
        words = read_json(DATA / "words.json")
        self.words = words["words"] if isinstance(words, dict) else words
        self.used_by = {}
        for g, sym in self.symbols.items():
            for part in sym.get("composes") or []:
                self.used_by.setdefault(part, []).append(g)

    def status(self, g):
        if g in self.symbols:
            return "card"
        return "frontier" if g in self.frontier else "new"

    def words_with(self, surface=None, part=None):
        return [w for w in self.words
                if (surface is not None and w["surface"] == surface)
                or (part is not None and part in w.get("parts", []))]


def fmt_program(p):
    bits = [SHORT.get(p["source"], p["source"]), p["role"][:3], f"“{p.get('name', '')}”"]
    if p.get("kind") == "mnemonic":
        bits.append("(mnemonic)")
    return " ".join(bits) + f" L{p.get('level', '?')}"


def fmt_word(w):
    prog = w.get("program") or {}
    tag = f"{SHORT.get(prog.get('source'), '-')} L{prog.get('level', '?')}" if prog else "untagged"
    return f"{w['surface']}@{w['audience']} ({tag})"


def fmt_parts(graph, parts):
    return " ".join(f"{p}[{graph.status(p)}]" for p in parts) or "—"


def triage_glyph(graph, g, mmah, offline):
    st = graph.status(g)
    print(f"{g}  {st.upper()}")
    if st == "card":
        sym = graph.symbols[g]
        flags = [sym.get("class", "?")] + (["form_only"] if sym.get("form_only") else [])
        print(f"   {' · '.join(flags)}")
        progs = sym.get("programs") or []
        print("   programs: " + ("; ".join(fmt_program(p) for p in progs) or "none"))
        print(f"   composes: {fmt_parts(graph, sym.get('composes') or [])}")
        cn = sym["readings"]["cn"]
        slug = referent_slug(cn.get("gloss", ""))
        print(f"   cn: {cn.get('reading') or '—'} “{cn.get('gloss', '')}” → r:{slug}")
        jp = sym["readings"]["jp"]
        print(f"   jp: {jp.get('reading') or '—'} “{jp.get('gloss', '')}”")
    elif st == "frontier":
        users = graph.used_by.get(g, [])
        print(f"   used by: {' '.join(users) or '(word parts / appearsIn only)'}")
    if st != "card" or len(graph.symbols[g].get("composes") or []) <= 1:
        print(f"   MMAH suggests: {fmt_parts(graph, mmah.get(g, []))}")
    if (HANZI / f"{g}.json").exists():
        strokes = "local ✓"
    elif offline:
        strokes = "not local (CDN not checked)"
    else:
        strokes = "CDN ✓ (fetch.py)" if cdn_has(g) else "✗ none — lift/assemble"
    print(f"   strokes: {strokes}")
    same = graph.words_with(surface=g)
    if same:
        print(f"   word entries: {', '.join(fmt_word(w) for w in same)}")
    users = graph.words_with(part=g)
    if users:
        more = f" +{len(users) - 8}" if len(users) > 8 else ""
        print(f"   in {len(users)} word(s): {' '.join(w['surface'] for w in users[:8])}{more}")


def triage_word(graph, surface):
    existing = graph.words_with(surface=surface)
    print(f"{surface}  WORD {'EXISTS' if existing else 'NEW'}")
    if existing:
        for w in existing:
            print(f"   {fmt_word(w)} · {w.get('reading', '')} “{w.get('gloss', '')}” → r:{w.get('denotes')}")
    glyphs = [c for c in surface if not is_kana(c) and not c.isascii()]
    print(f"   glyphs: {fmt_parts(graph, glyphs)}")


def main(argv):
    offline = "--offline" in argv
    items = [a for a in argv if not a.startswith("--")]
    if not items and not sys.stdin.isatty():
        items = sys.stdin.read().split()
    if not items:
        sys.exit(__doc__)

    graph = Graph()
    glyphs = [i for i in items if len(i) == 1]
    mmah = load_decomp()(glyphs) if glyphs else {}
    for item in items:
        if len(item) == 1:
            triage_glyph(graph, item, mmah, offline)
        else:
            triage_word(graph, item)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
