#!/usr/bin/env python3
"""Filesystem leaf for the data-layer scripts: repo paths + the one canonical
JSON read/write idiom (UTF-8, 2-space indent, trailing newline).

This module imports nothing local, so the pipeline is a *tree* rooted here:
symbols_io and every build/fetch script sit on top of it, and no script reaches
sideways into another script's output. Run the scripts as `python3 data/foo.py`
— Python puts data/ on sys.path[0] automatically, so a bare `import paths` (or
`import symbols_io`) resolves with no sys.path juggling.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SYM = DATA / "symbols"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    """Write `payload` as the repo's house JSON: UTF-8, indent 2, trailing newline.
    Centralised so the trailing-newline / ensure_ascii convention can't drift."""
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
