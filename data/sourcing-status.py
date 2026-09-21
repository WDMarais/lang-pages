#!/usr/bin/env python3
"""The editor's marks on the imagery worklist: which referents the /author/ linker
should stop asking contributors for. Site-level editorial state, deliberately
independent of how many images a referent already holds — `done` (enough, thanks)
or `later` (deprioritized). Both dim the tile, like a non-image referent does; the
tile still shows its image count.

  python3 data/sourcing-status.py                        # list the marks
  python3 data/sourcing-status.py done fire water        # enough images
  python3 data/sourcing-status.py later claw --note "after the scene pass"
  python3 data/sourcing-status.py clear fire             # back to open

Writes data/sourcing-status.json ({slug: {status, note?}}), which check-source
gates. Commit + deploy it for contributors to see the change.
"""
import argparse
import sys

from paths import DATA, read_json, write_json

PATH = DATA / "sourcing-status.json"
STATUSES = ("done", "later")


def known_slugs():
    """Every referent the linker can be pointed at: the 214 spine + the collection.

    Keyed on the spine's `referent`, NOT its `meaning`: `meaning` is display prose
    ("open enclosure", "page; head") and slugifying it here would disagree with the
    key build-pages resolves images under. See check_kangxi for the gate that keeps
    the two sides honest."""
    slugs = {r["referent"] for r in read_json(DATA / "kangxi.json")["radicals"]}
    if (DATA / "referents.json").exists():
        slugs |= set(read_json(DATA / "referents.json"))
    return slugs


def main():
    ap = argparse.ArgumentParser(description="Mark worklist referents done / later.")
    ap.add_argument("action", nargs="?", default="list", choices=(*STATUSES, "clear", "list"))
    ap.add_argument("slugs", nargs="*", help="referent slugs (kangxi meanings, e.g. fire)")
    ap.add_argument("--note", default="", help="shown to contributors on the tile + referent")
    a = ap.parse_args()
    marks = read_json(PATH) if PATH.exists() else {}

    if a.action == "list":
        for s, m in marks.items():
            print(f"{m['status']:6} {s}" + (f"  — {m['note']}" if m.get("note") else ""))
        print(f"{len(marks)} marked")
        return 0
    if not a.slugs:
        ap.error("name at least one referent slug")
    unknown = sorted(set(a.slugs) - known_slugs())
    if unknown and a.action != "clear":
        print(f"❌ not a referent: {' '.join(unknown)} (see data/kangxi.json referents)")
        return 1

    for s in a.slugs:
        if a.action == "clear":
            marks.pop(s, None)
        else:
            marks[s] = {"status": a.action, **({"note": a.note} if a.note else {})}
    write_json(PATH, dict(sorted(marks.items())))
    print(f"{a.action}: {' '.join(a.slugs)} → {PATH.relative_to(DATA.parent)} ({len(marks)} marked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
