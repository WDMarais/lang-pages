#!/usr/bin/env python3
"""Generate TTS audio clips for the lang-pages modules.

Audio is a *projection* of the canonical card data — same stance as the content
graph (build-graph.py) and the decomposition edges (fetch-decomp.py). The text
to synthesize is derived from the same card JSON the pages render, so there is a
single source of truth; no hand-maintained word lists live in shell.

Every glyph clip is content-keyed by SOUND, in a shared site-level bank, so a
reading is voiced once and every glyph that uses it shares the clip:
  - cn-bank: /audio/cn/<pinyin+tone>.mp3 (千→qian1), plus the few multi-syllable
    stroke names (竖钩→shugou); projected from phonetics.bank so it matches /zhuyin/.
  - jp-bank: /audio/jp/<romaji>.mp3 (セン→sen), voiced from the kana reading itself.
  - sent-bank: /audio/sent/<lang>-<digest>.mp3 — the authored example SENTENCES that
    ground a confusable cluster. A sentence has no short canonical spelling, so it is
    keyed by a digest of its text (phonetics.sentence_key); same content-keyed rule.
  - kana:    /audio/kana/<romaji>.mp3, the fixed mora board (/kana/).
  - xi-zhuang / cha-cai: bespoke lessons whose cards.json lists each clip per voice; we
    synthesize the four synthetic voices and leave any 录音 human recording alone.
cards3.js resolves each card to these banks by the keys build-pages stamps (cnSrc/
jpSrc), so there are no per-page, slug-keyed audio buckets to 404 or orphan.

Each bucket carries a manifest.json recording the text+voice synthesized into every
clip. A content key still can't tell whether the representative hanzi changed (禾→合
both voice he2), so the manifest catches that: such a clip is regenerated ("stale"),
not skipped. Clips predating the manifest are adopted.

Run:  python3 data/gen-audio.py [cn-bank|jp-bank|sent-bank|kana|xi-zhuang|all] [--dry-run] [--prune]
      --prune deletes clips in a bank that no card references, keeping the committed
      bank in sync with the projected set. Bespoke lessons (xi-zhuang, cha-cai) are
      never pruned — their dirs may hold a human 录音 recording that is not a job.
Requires: uv tool install edge-tts
"""
import subprocess
import sys
from collections import namedtuple

from paths import ROOT, DATA, read_json, write_json
from symbols_io import load_symbols, resolve_senses
from phonetics import bank as cn_bank, audio_key, multi_key, sentence_key, word_key
from phonetics_jp import kana_key

CN_VOICE = "zh-CN-XiaoxiaoNeural"
JP_VOICE = "ja-JP-NanamiNeural"

# Site-level, content-keyed audio banks (the shared store the audio-slug memory calls
# for): /audio/cn/<pinyin+tone>.mp3 and /audio/kana/<romaji>.mp3. Referenced by the
# phonetics pages now and (after the reconcile) by the CN cards, so a syllable is
# voiced once and shared by every character and page that uses it.
AUDIO = ROOT / "audio"

# xi-zhuang voice label → edge-tts voice. 录音 is a human recording, never synthesized.
XZ_VOICES = {
    "晓晓": "zh-CN-XiaoxiaoNeural",
    "晓伊": "zh-CN-XiaoyiNeural",
    "云扬": "zh-CN-YunyangNeural",
    "云希": "zh-CN-YunxiNeural",
}

Job = namedtuple("Job", "voice text outfile")


def lesson_jobs(path):
    """Bespoke lesson (xi-zhuang, cha-cai): one clip per (example sentence × synthetic
    voice), read from the lesson's cards.json. 录音, if present, is human — never a job."""
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


# Tone-demo syllables for /tones/: a representative hanzi per tone so ma1–5 always
# exist even when no card reads them. Merged into the CN syllable jobs, keyed the same.
TONE_DEMO = {"ma1": "妈", "ma2": "麻", "ma3": "马", "ma4": "骂", "ma5": "吗"}


def cn_bank_jobs():
    """One clip per CN sound → audio/cn/<key>.mp3, voiced by a representative hanzi
    (edge-tts can't pronounce bare pinyin). Single syllables come from phonetics.bank
    (the shared inventory the /zhuyin/ page also uses), deduped so every hanzi reading
    qiān shares audio/cn/qian1.mp3; tone-demo syllables are folded in. The handful of
    multi-syllable stroke names (竖钩 shùgōu → shugou) audio_key skips are added too,
    keyed by multi_key and voiced by the stroke's hanzi name — so /audio/cn/ is the one
    CN store and no clip is slug-keyed."""
    syms = load_symbols()

    def voiceable(entry):
        """Pick the hanzi that will VOICE this sound. A stroke codepoint (㇐ héng) is not
        pronounceable by edge-tts — it yields an empty clip — so a sound carried only by
        strokes falls back to the stroke's hanzi NAME (㇐ → 横), which says the very same
        syllable. Exactly the fallback the multi-syllable branch below already relies on;
        without it heng2/na4/ti2 silently never generated and those play buttons were mute."""
        for g in entry["glyphs"]:
            if (syms.get(g["glyph"], {}).get("class")) != "stroke":
                return g["glyph"]
        first = entry["glyphs"][0]["glyph"]
        cn = ((syms.get(first, {}).get("readings") or {}).get("cn") or {})
        return cn.get("name") or first

    text = {k: voiceable(e) for k, e in cn_bank(syms).items()}
    for k, hz in TONE_DEMO.items():
        text.setdefault(k, hz)
    for s in syms.values():
        cn = (s.get("readings") or {}).get("cn") or {}
        r = cn.get("reading")
        if r and audio_key(r) is None and (k := multi_key(r)):
            text.setdefault(k, cn.get("name") or s["glyph"])
        # a non-primary sense with its OWN cn reading (only ever a distinct sound —
        # inherited readings resolve to the primary, already keyed) is a real clip,
        # voiced by the glyph surface (docs/sense-model.md). setdefault keeps a shared
        # syllable clip voiced by its existing representative.
        for sense in resolve_senses(s):
            for reading in sense["cn"]:
                if k := audio_key(reading):
                    text.setdefault(k, s["glyph"])
    # CN words (真相・工作) are real hanzi — directly speakable, so the whole-word clip
    # is voiced by the SURFACE, not a representative syllable. setdefault so a single-
    # hanzi word (犬 → quan3) shares the glyph's syllable clip rather than re-cutting it;
    # the JP analog lives in jp_bank_jobs. Mirrors phonetics-architecture's word-audio wire.
    for w in read_json(DATA / "words.json").get("words", []):
        if w.get("audience") == "cn" and (k := word_key(w["surface"], w.get("reading"))):
            text.setdefault(k, w["surface"])
    return [Job(CN_VOICE, t, AUDIO / "cn" / f"{k}.mp3") for k, t in sorted(text.items())]


def jp_bank_jobs():
    """One clip per JP reading → audio/jp/<romaji>.mp3, voiced from the kana reading
    itself — unlike CN, kana is directly speakable, so no representative glyph is
    needed. Deduped by romaji key: 天 and 丶 both read テン → one audio/jp/ten.mp3.
    Scans a glyph's reading and its example (appearsIn), the JP analog of the CN bank;
    readingless components contribute nothing (kana_key → None)."""
    text = {}
    for s in load_symbols().values():
        jp = (s.get("readings") or {}).get("jp") or {}
        for reading in (jp.get("reading"), (jp.get("appearsIn") or {}).get("reading")):
            if k := kana_key(reading):
                text.setdefault(k, reading)
        # a non-primary sense's JP reading is its own voice clip (生 なま → nama.mp3);
        # kana is directly speakable, so no representative glyph (docs/sense-model.md).
        # setdefault dedups an inherited reading already voiced by sense 0.
        for sense in resolve_senses(s):
            for reading in sense["jp"]:
                if k := kana_key(reading):
                    text.setdefault(k, reading)
    # JP words (これ・人々・リンゴ) are audience-tagged lexemes; their full kana reading
    # is directly speakable, exactly like a glyph reading. setdefault so a reading a
    # glyph already voiced (之→これ) is shared, not regenerated as a duplicate clip.
    for w in read_json(DATA / "words.json").get("words", []):
        if w.get("audience") == "jp" and (k := kana_key(w.get("reading"))):
            text.setdefault(k, w["reading"])
    return [Job(JP_VOICE, t, AUDIO / "jp" / f"{k}.mp3") for k, t in sorted(text.items())]


def sent_bank_jobs():
    """One clip per authored example SENTENCE → audio/sent/<lang>-<digest>.mp3.

    The grounding half of a confusable cluster: each member gets a sentence that anchors
    it to its own context, and the contexts have to be HEARD for a phonetic pair (可不 vs
    不可) to come apart. Content-keyed by (lang, text) like every other bank, so the same
    sentence authored in two clusters is voiced once.

    Projects data/authored.json — the SOURCE, not edges.json — so gen-audio stays free of
    build order; sentence_key() is the shared contract that keeps the clip build-graph
    stamped and the clip synthesized here under one name."""
    p = DATA / "authored.json"
    if not p.exists():
        return []
    voices = {"cn": CN_VOICE, "jp": JP_VOICE}
    text = {}
    for e in read_json(p).get("edges", []):
        for ex in e.get("examples", []):
            lang = ex.get("lang") or e.get("lang") or e.get("audience")
            if lang not in voices or not ex.get("text"):
                continue
            text.setdefault(sentence_key(lang, ex["text"]), (lang, ex["text"]))
    return [Job(voices[lang], t, AUDIO / "sent" / f"{k}.mp3")
            for k, (lang, t) in sorted(text.items())]


def kana_jobs():
    """One clip per mora → audio/kana/<romaji>.mp3, voiced from the kana glyph. Deduped
    by romaji so ぢ/づ don't re-cut じ/ず's ji/zu. Projects kana/data.json, so the clip
    set matches the /kana/ board exactly."""
    data = read_json(ROOT / "kana/data.json")
    seen = {}
    for section in data.values():
        for row in section:
            for c in row:
                if c:
                    seen.setdefault(c["romaji"], c["hira"])
    return [Job(JP_VOICE, hira, AUDIO / "kana" / f"{r}.mp3") for r, hira in sorted(seen.items())]


# All glyph audio is content-keyed now: CN (single + multi-syllable) → /audio/cn/,
# JP → /audio/jp/, kana mora → /audio/kana/. The old per-page, slug-keyed buckets
# (radicals/audio, strokes/audio) and their glyph_jobs are retired — cards3.js resolves
# every card to a bank by sound, so a page no longer owns an audio dir.
MODULES = {
    "cn-bank": cn_bank_jobs,
    "jp-bank": jp_bank_jobs,
    "sent-bank": sent_bank_jobs,
    "kana": kana_jobs,
    "xi-zhuang": lambda: lesson_jobs(ROOT / "xi-zhuang/cards.json"),
    "cha-cai": lambda: lesson_jobs(ROOT / "cha-cai/cards.json"),
    "chao-fan": lambda: lesson_jobs(ROOT / "chao-fan/cards.json"),
}


# A clip's filename is the sound key, not the text spoken, so "the file exists"
# cannot answer "is it voiced by the right hanzi?" (禾 and 合 both key he2). Each
# bucket keeps a manifest of what was synthesized into it, and a job whose text or
# voice has moved since is regenerated — otherwise a changed representative would
# leave the old clip sitting there under the same key.
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
# Bespoke lessons (xi-zhuang, cha-cai) are excluded as a class: lesson_jobs skips 录音,
# so a human recording in the dir is never a referenced job — a prune would delete it.
# A lesson may hold (or later gain) such a recording, so its dir is never fully owned.
PRUNABLE = {"cn-bank", "jp-bank", "sent-bank", "kana"}


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
