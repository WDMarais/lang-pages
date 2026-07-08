#!/usr/bin/env python3
"""Generate TTS audio clips for the lang-pages modules.

Audio is a *projection* of the canonical card data — same stance as the content
graph (build-graph.py) and the decomposition edges (fetch-decomp.py). The text
to synthesize is derived from the same card JSON the pages render, so there is a
single source of truth; no hand-maintained word lists live in shell.

Each job mirrors exactly what the page renders, so we neither 404 nor orphan:
  - glyph modules (radicals, strokes): projected straight from the symbol source of
    truth (load_symbols → to_card), NOT a page file — cards3.js renders the name play
    button unconditionally and the example button only when the binding has an
    `appearsIn`. Non-stroke glyph audio is homed in the shared radicals/audio/ bucket
    that /characters/ and /kangxi/ both point at via audioBase; strokes has its own.
  - xi-zhuang: cards.json already lists each clip's file per voice; we synthesize
    the four synthetic voices and leave the 录音 human recording alone.

Run:  python3 data/gen-audio.py [radicals|strokes|xi-zhuang|all] [--dry-run]
Requires: uv tool install edge-tts
"""
import subprocess
import sys
from collections import namedtuple

from paths import ROOT, read_json
from symbols_io import load_symbols, to_card, on_strokes

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


def glyph_cards(keep):
    """Glyph cards from the symbol source of truth (load_symbols → to_card), filtered
    by a page-membership rule. Same projection build-pages renders, so the audio set
    matches the page exactly without reading a (possibly retired) page file."""
    return [to_card(s) for s in load_symbols().values() if keep(s)]


def glyph_jobs(cards, audio):
    """Name button ({cn,jp}-{slug}.mp3) + example button (-ex) when the binding has an
    appearsIn. `audio` is the bucket the page actually fetches from (per its audioBase)."""
    jobs = []
    for c in cards:
        slug, cn, jp = c["slug"], c["cn"], c["jp"]
        cn_name = cn["name"]
        jp_name = jp.get("reading") or jp["name"]
        jobs.append(Job(CN_VOICE, cn_name, audio / f"cn-{slug}.mp3"))
        jobs.append(Job(JP_VOICE, jp_name, audio / f"jp-{slug}.mp3"))
        if cn.get("appearsIn"):
            jobs.append(Job(CN_VOICE, cn["appearsIn"]["char"], audio / f"cn-{slug}-ex.mp3"))
        if jp.get("appearsIn"):
            jp_ai = jp["appearsIn"]
            jobs.append(Job(JP_VOICE, jp_ai.get("reading") or jp_ai["char"],
                            audio / f"jp-{slug}-ex.mp3"))
    return jobs


def xizhuang_jobs(path):
    """xi-zhuang: one clip per (example sentence × synthetic voice), from the manifest."""
    base = path.parent
    d = read_json(path)
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
    # radicals/audio/ is the shared non-stroke glyph audio bucket — its dir name is
    # historical (the /radicals/ page retired into /characters/ + /kangxi/, which both
    # point here via audioBase "../radicals/"). Sourced from the symbols, so it never
    # reads a retired projection.
    "radicals": lambda: glyph_jobs(glyph_cards(lambda s: not on_strokes(s)),
                                   ROOT / "radicals/audio"),
    "strokes": lambda: glyph_jobs(glyph_cards(on_strokes), ROOT / "strokes/audio"),
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
