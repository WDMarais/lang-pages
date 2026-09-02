#!/usr/bin/env python3
"""Fold a QC viewer export (qc-decisions.json) into the referent image store.

The maintainer curates a bulk image pack in `data/qc-viewer.py` (Keep/Reject per
candidate) and exports `qc-decisions.json`. This folds the KEPT, free-licensed
images into `data/referents.json` and copies their bytes into `shared/referents/`
— the same store the human sourcing pipeline (referents-inbox.toml) writes to.

    python3 data/referents-from-qc.py ~/Downloads/qc-decisions.json            # dry-run: plan only
    python3 data/referents-from-qc.py ~/Downloads/qc-decisions.json --apply    # write it

Resolution: each kept image is attached to the referent its radical GLYPH denotes
(edges.json `g:<glyph> → r:<slug>`, sense 0), falling back to a referent whose slug
equals the pack slug. Unresolved radicals (glyph not authored yet, no matching
referent) are reported and skipped — author the glyph, re-run.

Guardrails mirror referents-from-toml.py: only PD / CC0 / CC BY / CC BY-SA licenses
are accepted (anything else is refused, not silently dropped), and the fold is
idempotent — an image whose `source` is already recorded for that referent is
skipped. Bytes come from the local pack (no network). After it runs, `data/build.py`
regenerates the graph + pages and `check-source.py` validates.

Exit: 0 clean · 1 something needed attention (unresolved / rejected license).
"""
import argparse
import json
import os
import shutil
import sys

import paths

DATA = paths.DATA
REFDIR = paths.ROOT / "shared" / "referents"
DEFAULT_PACK = DATA / ".cache" / "qc" / "kangxi_radical_imagery"
def license_ok(lic):
    """Free-to-redistribute only: public domain (any phrasing — 'Public Domain Mark',
    'Public Domain Dedication (CC0)', 'Public domain'), CC0, and CC BY / CC BY-SA at
    any version. Space-guarded so CC BY-NC / CC BY-ND stay refused."""
    up = (lic or "").strip().upper()
    if up.startswith("PUBLIC DOMAIN") or up == "PD" or up.startswith("PD ") or up.startswith("CC0"):
        return True
    return any(up == o or up.startswith(o + " ") for o in ("CC BY", "CC BY-SA"))


def denotes_by_glyph():
    """glyph → r:<slug> for the FIRST (sense-0) denotes edge, the referent bridge."""
    edges = json.load(open(DATA / "edges.json", encoding="utf-8"))
    edges = edges if isinstance(edges, list) else edges.get("edges", [])
    out = {}
    for e in edges:
        if e.get("kind") == "denotes" and str(e.get("from", "")).startswith("g:"):
            g = e["from"][2:]
            out.setdefault(g, e["to"])  # first edge = sense 0
    return out


def next_index(slug, entries):
    """Next `<slug>-NN` number, past both recorded entries and files on disk."""
    used = set()
    for im in entries:
        m = im.get("file", "")
        stem = os.path.splitext(m)[0]
        if stem.startswith(f"{slug}-") and stem[len(slug) + 1:].isdigit():
            used.add(int(stem[len(slug) + 1:]))
    for f in (os.listdir(REFDIR) if REFDIR.exists() else []):
        stem = os.path.splitext(f)[0]
        if stem.startswith(f"{slug}-") and stem[len(slug) + 1:].isdigit():
            used.add(int(stem[len(slug) + 1:]))
    return (max(used) + 1) if used else 1


def main():
    ap = argparse.ArgumentParser(description="Fold qc-decisions.json into referents.json + shared/referents/.")
    ap.add_argument("decisions", nargs="+",
                    help="qc-decisions.json export(s). Later files OVERRIDE earlier ones per "
                         "image (matched on `path`), so after reviewing the export you can flip "
                         "specific calls with a small hand-edited file of {path, decision} rows "
                         "— the raw export stays untouched.")
    ap.add_argument("--pack", default=str(DEFAULT_PACK), help="pack dir the decisions came from (byte source)")
    ap.add_argument("--apply", action="store_true", help="write files + referents.json (default: dry-run)")
    args = ap.parse_args()

    pack = os.path.abspath(args.pack)
    # Merge the decision files in order; a later file's row is layered onto the earlier
    # record for the same image (keyed by path), so an override file need only carry the
    # fields it changes (e.g. just {"path": "...", "decision": "reject"}).
    merged = {}
    for dpath in args.decisions:
        exp = json.load(open(dpath, encoding="utf-8"))
        rows = exp.get("decisions", exp) if isinstance(exp, dict) else exp
        for d in rows:
            key = d.get("path") or f"{d.get('num')}|{d.get('file')}"
            merged[key] = {**merged.get(key, {}), **d}
    decisions = list(merged.values())

    refpath = DATA / "referents.json"
    referents = json.load(open(refpath, encoding="utf-8")) if refpath.exists() else {}
    d2g = denotes_by_glyph()
    known_ref_ids = set(d2g.values()) | {f"r:{k}" for k in referents}

    kept = [d for d in decisions if d.get("decision") == "keep"]
    planned, unresolved, rejected, skipped = [], [], [], []
    existing_sources = {slug: {im.get("source", "") for im in e.get("images", [])}
                        for slug, e in referents.items()}
    # index reserved per (slug) as we plan, so two kept images for one referent
    # don't both grab the same -NN.
    reserved = {}

    for d in kept:
        glyph, slug = d.get("glyph", ""), d.get("slug", "")
        if d.get("missing"):
            skipped.append((d, "file missing in pack"))
            continue
        if not license_ok(d.get("license")):
            rejected.append(d)
            continue
        rid = d2g.get(glyph) or (f"r:{slug}" if f"r:{slug}" in known_ref_ids else None)
        if not rid:
            unresolved.append(d)
            continue
        refslug = rid[2:]
        src = d.get("source", "")
        if src and src in existing_sources.get(refslug, set()):
            skipped.append((d, f"already folded into r:{refslug}"))
            continue
        # locate bytes: prefer the exported path, else the "<num> <slug>/images/<file>" folder.
        rel = d.get("path") or f"{d.get('num')} {slug}/images/{d.get('file')}"
        srcfile = os.path.join(pack, rel)
        if not os.path.exists(srcfile):
            skipped.append((d, f"byte source not found: {rel}"))
            continue
        ext = os.path.splitext(d.get("file", ""))[1] or os.path.splitext(srcfile)[1]
        entries = referents.get(refslug, {}).get("images", [])
        idx = reserved.get(refslug, next_index(refslug, entries))
        reserved[refslug] = idx + 1
        dest = f"{refslug}-{idx:02d}{ext}"
        planned.append({
            "refslug": refslug, "srcfile": srcfile, "dest": dest,
            "credit": d.get("credit", ""), "license": d.get("license", ""), "source": src,
        })
        existing_sources.setdefault(refslug, set()).add(src)

    # ── report ──
    byref = {}
    for p in planned:
        byref.setdefault(p["refslug"], []).append(p)
    print(f"kept in export: {len(kept)}  ·  to fold: {len(planned)} images into {len(byref)} referents")
    for refslug in sorted(byref):
        print(f"  r:{refslug}: +{len(byref[refslug])}  ({', '.join(p['dest'] for p in byref[refslug])})")
    if rejected:
        print(f"\n✗ REJECTED — non-free license ({len(rejected)}):", file=sys.stderr)
        for d in rejected:
            print(f"    {d.get('num')} {d.get('slug')} / {d.get('file')}: {d.get('license')!r}", file=sys.stderr)
    if unresolved:
        print(f"\n⚠ UNRESOLVED — no referent for glyph/slug ({len(unresolved)}):", file=sys.stderr)
        for d in unresolved:
            print(f"    {d.get('num')} {d.get('slug')} (glyph {d.get('glyph') or '—'}) / {d.get('file')}",
                  file=sys.stderr)
    if skipped:
        print(f"\n· skipped ({len(skipped)}): "
              + "; ".join(f"{d.get('slug')}/{d.get('file')} [{why}]" for d, why in skipped[:8])
              + (" …" if len(skipped) > 8 else ""))

    if not args.apply:
        print("\n(dry-run — re-run with --apply to copy bytes + write referents.json)")
        return 0 if not (rejected or unresolved) else 1

    # ── apply ──
    REFDIR.mkdir(parents=True, exist_ok=True)
    for p in planned:
        shutil.copyfile(p["srcfile"], REFDIR / p["dest"])
        entry = referents.setdefault(p["refslug"], {"label": p["refslug"], "images": []})
        entry.setdefault("images", []).append({
            "file": p["dest"], "credit": p["credit"], "license": p["license"], "source": p["source"],
        })
    referents = {k: referents[k] for k in sorted(referents)}
    with open(refpath, "w", encoding="utf-8") as f:
        json.dump(referents, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\napplied: copied {len(planned)} files → {REFDIR}, updated {refpath}")
    print("next: python3 data/build.py")
    return 0 if not (rejected or unresolved) else 1


if __name__ == "__main__":
    sys.exit(main())
