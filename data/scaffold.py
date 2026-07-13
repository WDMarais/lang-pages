#!/usr/bin/env python3
"""Turn a bare glyph into a symbol stub, so an ingest starts from a filled-in
skeleton instead of a blank file.

Scaffolds ONLY what is mechanically derivable — codepoint, Kangxi number, page
class, whether stroke data exists, the structural decomposition. Every field
that is a judgment call (readings, glosses, a program's meaning-vs-mnemonic
`kind`) is written as a literal "TODO" for a human to resolve. The point is to
kill the per-glyph lookup toil, NOT to guess content: a stub that quietly
invents a reading is worse than no stub.

  python3 data/scaffold.py 出 右          # write data/symbols/{出,右}.json
  python3 data/scaffold.py 出 --fetch     # also pull HanziWriter stroke data
  python3 data/scaffold.py 出 --force     # overwrite an existing symbol

Nothing downstream is run. After editing the TODOs, take the normal path:
fetch-decomp → build-graph → build-pages → gen-audio (docs/authoring.md).
"""
import subprocess
import sys

from paths import DATA, ROOT, SYM, read_json, write_json

HANZI = ROOT / "shared" / "hanzi-data"
TODO = "TODO"


def kangxi_number(glyph):
    """The glyph's Kangxi radical number, or None. Read from the 214-spine, which
    is the same reference build-pages joins /kangxi/ against."""
    for r in read_json(DATA / "kangxi.json")["radicals"]:
        if r["glyph"] == glyph:
            return r["num"]
    return None


def decomposition(glyph):
    """MMAH's immediate components, if fetch-decomp has already seen this glyph.
    A hint only — decomposition.json (not the symbol's `composes`) is what feeds
    the graph, and it is regenerated from the symbol set after this runs."""
    path = DATA / "decomposition.json"
    return read_json(path).get(glyph, []) if path.exists() else []


def has_strokes(glyph):
    return (HANZI / f"{glyph}.json").exists()


def fetch_strokes(glyph):
    """Best-effort pull of HanziWriter data. A component absent from the dataset
    (a katakana-shaped part) will fail here — that is expected, and the caller
    falls back to hw:false, which is a valid stub until someone lifts the strokes
    out of a character that contains it (see fetch.py --lift)."""
    r = subprocess.run([sys.executable, str(HANZI / "fetch.py"), glyph],
                       capture_output=True, text=True)
    return r.returncode == 0 and has_strokes(glyph)


def reading_stub(name):
    return {"name": name, "reading": TODO, "gloss": TODO, "extra": TODO}


def scaffold(glyph, fetch=False):
    kangxi = kangxi_number(glyph)
    if fetch and not has_strokes(glyph):
        fetch_strokes(glyph)
    sym = {
        "glyph": glyph,
        "cp": f"U+{ord(glyph):04X}",
        # `char` is the safe default: it is the only class that lands on
        # /characters/, so a mis-scaffolded comp is visible immediately rather
        # than silently missing. Carrying a Kangxi number does not settle this
        # either way (口 is a char, 亠 is a comp) — hence the review line.
        "class": "char",
        **({"kangxi": kangxi} if kangxi else {}),
        "form": {"hw": has_strokes(glyph), "image": ""},
        "readings": {"cn": reading_stub(glyph), "jp": reading_stub(glyph)},
        "programs": [],
    }
    write_json(SYM / f"{glyph}.json", sym)
    return sym


def main(argv):
    force = "--force" in argv
    fetch = "--fetch" in argv
    glyphs = [a for a in argv if not a.startswith("-")]
    if not glyphs:
        sys.exit(__doc__)

    for g in glyphs:
        path = SYM / f"{g}.json"
        if path.exists() and not force:
            print(f"skip  {g}  (already carded — --force to overwrite)")
            continue
        sym = scaffold(g, fetch=fetch)
        parts = decomposition(g)
        bits = [f"cp {sym['cp']}"]
        if sym.get("kangxi"):
            bits.append(f"kangxi {sym['kangxi']}")
        bits.append("hw " + ("✓" if sym["form"]["hw"] else "✗ (fetch or --lift)"))
        if parts:
            bits.append("parts " + " ".join(parts))
        print(f"wrote {g}  ({' · '.join(bits)})")

    print("\nreview in each stub:")
    print("  class     — 'char' assumed; set 'comp' for a building-block shape")
    print("  readings  — every TODO (name/reading/gloss/extra, cn + jp)")
    print("  programs  — add tiers; `kind` is meaning-vs-mnemonic, per the name")
    print("  _spine.json — add the glyph in editorial position (else appended sorted)")


if __name__ == "__main__":
    main(sys.argv[1:])
