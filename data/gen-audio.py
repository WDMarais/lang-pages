#!/usr/bin/env python3
"""Generate TTS audio clips for the lang-pages modules.

Audio is a *projection* of the canonical card data — same stance as the content
graph (build-graph.py) and the decomposition edges (fetch-decomp.py). The text
to synthesize is derived from the same card JSON the pages render, so there is a
single source of truth; no hand-maintained word lists live in shell.

Each job mirrors exactly what the page requests, so we neither 404 nor orphan:
  - glyph modules (radicals, strokes): cards3.js renders the name play button
    unconditionally and the example button only when the binding has an `ex`.
  - xi-zhuang: cards.json already lists each clip's file per voice; we synthesize
    the four synthetic voices and leave the 录音 human recording alone.

Run:  python3 data/gen-audio.py [radicals|strokes|xi-zhuang|all] [--dry-run]
Requires: uv tool install edge-tts
"""
import json
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CN_VOICE = "zh-CN-XiaoxiaoNeural"
JP_VOICE = "ja-JP-NanamiNeural"

# xi-zhuang voice label → edge-tts voice. 录音 is a human recording, never synthesized.
XZ_VOICES = {
    "晓晓": "zh-CN-XiaoxiaoNeural",
    "晓伊": "zh-CN-XiaoyiNeural",
    "云扬": "zh-CN-YunyangNeural",
    "云希": "zh-CN-YunxiNeural",
}

Job = namedtuple("Job", "voice text outfile")


def _cards(path):
    d = json.loads(path.read_text())
    return [c for grp in d["groups"] for c in grp["cards"]]


def glyph_jobs(path):
    """radicals / strokes: {cn,jp}-{slug}.mp3 (name) + -ex.mp3 when an example exists."""
    audio = path.parent / "audio"
    jobs = []
    for c in _cards(path):
        slug, cn, jp = c["slug"], c["cn"], c["jp"]
        cn_name = cn["name"]
        jp_name = jp.get("reading") or jp["name"]
        jobs.append(Job(CN_VOICE, cn_name, audio / f"cn-{slug}.mp3"))
        jobs.append(Job(JP_VOICE, jp_name, audio / f"jp-{slug}.mp3"))
        if cn.get("ex"):
            jobs.append(Job(CN_VOICE, cn["ex"]["char"], audio / f"cn-{slug}-ex.mp3"))
        if jp.get("ex"):
            jp_ex = jp["ex"]
            jobs.append(Job(JP_VOICE, jp_ex.get("reading") or jp_ex["char"],
                            audio / f"jp-{slug}-ex.mp3"))
    return jobs


def xizhuang_jobs(path):
    """xi-zhuang: one clip per (example sentence × synthetic voice), from the manifest."""
    base = path.parent
    d = json.loads(path.read_text())
    jobs = []
    for category in d.values():
        for entry in category:
            for ex in entry.get("examples", []):
                for label, rel in (ex.get("audio") or {}).items():
                    voice = XZ_VOICES.get(label)
                    if voice:  # skip 录音 and anything unrecognized
                        jobs.append(Job(voice, ex["zh"], base / rel))
    return jobs


MODULES = {
    "radicals": lambda: glyph_jobs(ROOT / "radicals/radicals.json"),
    "strokes": lambda: glyph_jobs(ROOT / "strokes/strokes.json"),
    "xi-zhuang": lambda: xizhuang_jobs(ROOT / "xi-zhuang/cards.json"),
}


def run(jobs, dry_run):
    made = skipped = 0
    for j in jobs:
        rel = j.outfile.relative_to(ROOT)
        if j.outfile.exists():
            skipped += 1
            if dry_run:
                print(f"skip  {rel}  «{j.text}»  [{j.voice}]")
            continue
        made += 1
        if dry_run:
            print(f"gen   {rel}  «{j.text}»  [{j.voice}]")
            continue
        print(f"gen   {rel}")
        j.outfile.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["edge-tts", "--voice", j.voice, "--text", j.text,
                        "--write-media", str(j.outfile)], check=True)
    print(f"done  ({made} generated, {skipped} skipped, {len(jobs)} total)")


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    dry_run = "--dry-run" in argv
    which = args[0] if args else "all"
    names = list(MODULES) if which == "all" else [which]
    if any(n not in MODULES for n in names):
        sys.exit(f"unknown module: {which}  (choose: {', '.join(MODULES)}, all)")
    jobs = [j for n in names for j in MODULES[n]()]
    run(jobs, dry_run)


if __name__ == "__main__":
    main(sys.argv[1:])
