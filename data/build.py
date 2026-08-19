#!/usr/bin/env python3
"""One-command build: regenerate every derived artifact from the authored source
(data/symbols/*.json + data/words.json) in dependency order, then gate.

    python3 data/build.py [--no-audio] [--no-check]

    symbols → graph → pages → audio → check-source

Run this after ANY edit under data/symbols/ or to data/words.json. The steps have a
strict linear order with no back-edge (each reads the source of truth, not a peer's
output), and each is idempotent — a clean tree stays clean, so re-running is always
safe. A glyph's parts are its authored `composes` field, read straight from the
symbol by build-graph.py — there is no separate decomposition step to forget (MMAH
is now only an authoring aid: data/fetch-decomp.py suggests parts to paste in).

Flags:
  --no-audio   skip gen-audio.py (needs edge-tts; the data build is complete without it)
  --no-check   skip the closing check-source.py gate

Halts at the first non-zero step and returns its exit code (so a pre-commit hook or CI
can gate on it). The full runbook with the per-step rationale is docs/authoring.md.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (name, script) in dependency order. `audio` and `check` are individually skippable.
STEPS = [
    ("graph", "build-graph.py"),
    ("pages", "build-pages.py"),
    ("audio", "gen-audio.py"),
    ("check", "check-source.py"),
]


def main(argv):
    skip = set()
    if "--no-audio" in argv:
        skip.add("audio")
    if "--no-check" in argv:
        skip.add("check")

    for name, script in STEPS:
        if name in skip:
            print(f"\n── skip {name}")
            continue
        print(f"\n═══ {name}  ({script})")
        code = subprocess.run([sys.executable, str(HERE / script)]).returncode
        if code != 0:
            print(f"\n✗ build halted at '{name}' (exit {code})")
            return code

    print("\n✓ build complete")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
