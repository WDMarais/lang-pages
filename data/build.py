#!/usr/bin/env python3
"""One-command build: regenerate every derived artifact from the authored source
(data/symbols/*.json + data/words.json) in dependency order, then gate.

    python3 data/build.py [--no-audio] [--no-check]

    symbols → graph → pages → phonetics → audio (+prune) → check-source

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

# (name, script, args) in dependency order. `audio` and `check` are individually skippable.
# `phonetics` projects the /zhuyin/ syllable bank from the same symbols build-pages reads.
# `audio` runs with --prune so a clip whose key moved (么 me → me5) doesn't linger;
# gen-audio prunes only the banks it fully owns, never a lesson dir that may hold a 录音.
STEPS = [
    ("graph", "build-graph.py", []),
    ("pages", "build-pages.py", []),
    ("phonetics", "build-phonetics.py", []),
    ("audio", "gen-audio.py", ["--prune"]),
    ("check", "check-source.py", []),
]


def main(argv):
    skip = set()
    if "--no-audio" in argv:
        skip.add("audio")
    if "--no-check" in argv:
        skip.add("check")

    for name, script, args in STEPS:
        if name in skip:
            print(f"\n── skip {name}")
            continue
        print(f"\n═══ {name}  ({' '.join([script, *args])})")
        code = subprocess.run([sys.executable, str(HERE / script), *args]).returncode
        if code != 0:
            print(f"\n✗ build halted at '{name}' (exit {code})")
            return code

    print("\n✓ build complete")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
