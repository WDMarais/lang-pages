#!/usr/bin/env python3
"""Generate TTS audio clips for the lang-pages modules.

Audio is a *projection* of the canonical card data — same stance as the content
graph (build-graph.py) and the decomposition edges (fetch-decomp.py). The text
to synthesize is derived from the same card JSON the pages render, so there is a
single source of truth; no hand-maintained word lists live in shell.

Each job mirrors exactly what the page renders, so we neither 404 nor orphan:
  - glyph modules (radicals, strokes): projected straight from the symbol source of
    truth (load_symbols → to_card), NOT a page file — cards3.js renders the name play
    button when the binding has a reading and the example button only when it has an
    `appearsIn`. Non-stroke glyph audio is homed in the shared radicals/audio/ bucket
    that /characters/ and /kangxi/ both point at via audioBase; strokes has its own.
  - xi-zhuang: cards.json already lists each clip's file per voice; we synthesize
    the four synthetic voices and leave the 录音 human recording alone.

Each bucket carries a manifest.json recording the text+voice synthesized into every
clip. Filenames are keyed by slug, not by what they say, so the manifest is the only
thing that can notice a reading edited in place under an unchanged slug; such a clip
is regenerated ("stale"), not skipped. Clips predating the manifest are adopted.

Run:  python3 data/gen-audio.py [radicals|strokes|xi-zhuang|all] [--dry-run] [--prune]
      --prune deletes clips in a glyph bucket (radicals/strokes) that no card
      references, keeping the committed bucket in sync with the projected set.
      xi-zhuang is never pruned — its dir holds the human 录音 recording.
Requires: uv tool install edge-tts
"""
import subprocess
import sys
from collections import namedtuple

from paths import ROOT, read_json, write_json
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
    """Name button ({cn,jp}-{slug}.mp3) when the binding has a reading + example button
    (-ex) when it has an appearsIn — matching cards3.js, which gates each play button on
    those same fields. Gating the name job on a reading is also what keeps us from
    feeding a readingless shape component (匸, no JP reading) to a voice that can't say
    it. `audio` is the bucket the page fetches from (per its audioBase)."""
    jobs = []
    for c in cards:
        slug, cn, jp = c["slug"], c["cn"], c["jp"]
        if cn.get("reading"):
            jobs.append(Job(CN_VOICE, cn["name"], audio / f"cn-{slug}.mp3"))
        if jp.get("reading"):
            jobs.append(Job(JP_VOICE, jp["reading"], audio / f"jp-{slug}.mp3"))
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


# A clip's filename is keyed by slug, not by the text it speaks, so "the file
# exists" cannot answer "does it still say the right thing?". Each bucket keeps a
# manifest of what was synthesized into it, and a job whose text or voice has
# moved since is regenerated. Without this, editing a reading in place leaves the
# old clip sitting there under the same slug, silently wrong.
MANIFEST = "manifest.json"


def load_manifest(bucket):
    path = bucket / MANIFEST
    return read_json(path) if path.exists() else {}


def run(jobs, dry_run):
    made = adopted = skipped = failed = 0
    unspeakable = []
    manifests = {b: load_manifest(b) for b in {j.outfile.parent for j in jobs}}
    for j in jobs:
        rel = j.outfile.relative_to(ROOT)
        man = manifests[j.outfile.parent]
        said = {"text": j.text, "voice": j.voice}
        # a 0-byte file is a partial write from an aborted run — regenerate it
        present = j.outfile.exists() and j.outfile.stat().st_size > 0
        recorded = man.get(j.outfile.name)
        if present and recorded is None:
            # Pre-manifest clip. Its text is unknowable after the fact, so adopt it
            # as-is rather than resynthesize every committed bucket on first run.
            adopted += 1
            man[j.outfile.name] = said
            if dry_run:
                print(f"adopt {rel}  «{j.text}»  [{j.voice}]")
            continue
        if present and recorded == said:
            skipped += 1
            if dry_run:
                print(f"skip  {rel}  «{j.text}»  [{j.voice}]")
            continue
        why = "stale" if present else "gen"
        if dry_run:
            made += 1
            was = f"  (was «{recorded['text']}»)" if present else ""
            print(f"{why:5} {rel}  «{j.text}»  [{j.voice}]{was}")
            continue
        print(f"{why:5} {rel}")
        j.outfile.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["edge-tts", "--voice", j.voice, "--text", j.text,
                            "--write-media", str(j.outfile)], check=True,
                           capture_output=True)
            made += 1
            man[j.outfile.name] = said
        except subprocess.CalledProcessError:
            # edge-tts yields no audio for a readingless shape component (丆 has no
            # pronunciation) — skip that one clip rather than abort the whole batch.
            j.outfile.unlink(missing_ok=True)  # don't leave a 0-byte file behind
            man.pop(j.outfile.name, None)
            failed += 1
            unspeakable.append((rel, j.text))
    if not dry_run:
        for bucket, man in manifests.items():
            if bucket.exists():
                write_json(bucket / MANIFEST, dict(sorted(man.items())))
    tail = f", {failed} failed" if failed else ""
    kept = f"{skipped} skipped" + (f", {adopted} adopted" if adopted else "")
    print(f"done  ({made} generated, {kept}{tail}, {len(jobs)} total)")
    for rel, text in unspeakable:
        print(f"  ⚠ no audio for «{text}» → {rel} (readingless; button stays silent)")


# Buckets gen-audio fully owns, so an unreferenced file there is safe to delete.
# xi-zhuang is excluded: its audio dir also holds the human 录音 recording, which
# is never a synthesized job and must never be pruned.
PRUNABLE = {"radicals", "strokes"}


def prune_bucket(name, jobs, dry_run):
    """Delete clips in this module's bucket(s) that no current job references —
    keeps the committed audio in sync with the projected card set (e.g. after a
    reading is added/removed or a glyph is re-slugged)."""
    if name not in PRUNABLE:
        print(f"prune {name}: skipped (bucket not exclusively synthesized)")
        return
    referenced = {j.outfile.name for j in jobs}
    buckets = {j.outfile.parent for j in jobs}  # derived from the jobs, never guessed
    removed = 0
    for bucket in sorted(buckets):
        for f in sorted(bucket.glob("*.mp3")):
            if f.name not in referenced:
                removed += 1
                print(f"prune {'(dry) ' if dry_run else ''}{f.relative_to(ROOT)}")
                if not dry_run:
                    f.unlink()
        # the manifest tracks the clips, so it prunes with them
        man = load_manifest(bucket)
        if not dry_run and (stale := man.keys() - referenced):
            write_json(bucket / MANIFEST,
                       dict(sorted((k, v) for k, v in man.items() if k not in stale)))
    verb = "to remove" if dry_run else "removed"
    print(f"prune {name}: {removed} unreferenced {verb}")


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    dry_run = "--dry-run" in argv
    prune = "--prune" in argv
    which = args[0] if args else "all"
    names = list(MODULES) if which == "all" else [which]
    if any(n not in MODULES for n in names):
        sys.exit(f"unknown module: {which}  (choose: {', '.join(MODULES)}, all)")
    per_module = {n: MODULES[n]() for n in names}
    run([j for js in per_module.values() for j in js], dry_run)
    if prune:
        for n in names:
            prune_bucket(n, per_module[n], dry_run)


if __name__ == "__main__":
    main(sys.argv[1:])
