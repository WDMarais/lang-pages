#!/usr/bin/env python3
"""Build and maintain a referent-imagery QC pack from contributor submissions.

The `/author/` linker exports a FLAT submission — `{_contributor, slug: {label,
images:[…]}}` — but `data/qc-viewer.py` reads a PACK: one numbered folder per
Kangxi radical, each holding a submission JSON and an `images/` dir of bytes.
This is the adapter between the two, plus the small maintenance ops the pack
needs once more than one contributor is in it.

    python3 data/qc-pack.py add ~/coding-review/imagery-lmar-2026-09-19.json
    python3 data/qc-pack.py add SUBMISSION.json --fetch      # …and pull the bytes
    python3 data/qc-pack.py tag avis                         # stamp untagged folders
    python3 data/qc-pack.py ls                               # what's in the pack

`add` MERGES: a contributor's images for a radical land in that radical's existing
folder as a SIBLING file (`<slug>-<contributor>.json`), never by rewriting another
contributor's submission. Two batches for the same radical then render side by side
in the viewer, each image carrying its provenance.

Two renames happen on the way in, both load-bearing:
  · the folder's own slug wins over the submission's (lmar's `earth` is the pack's
    `32 soil`), so one radical is one folder however contributors labelled it;
  · every file becomes `<slug>-<contributor>-NN.<ext>`, so a second batch cannot
    collide with the first (both ship `cloth-01.jpg`) — and, because the viewer keys
    its Keep/Reject state on the image path, the existing decisions survive untouched.

Radicals are matched to folders by KANGXI NUMBER, in this order: a `kangxi` field on
the referent entry (authoritative — carry it whenever you have it), then the pack's
own folder names, then data/kangxi.json's meanings. An unresolvable slug is reported,
not guessed — pass `--map slug=num` to place it by hand.

Why the `kangxi` field matters: a slug alone does NOT identify a radical. Of the 184
folders in the first pack, 14 don't match any kangxi.json meaning and two match the
WRONG one (`14 cover` looks like 146, `144 walk` like 162). Meaning-matching is a
convenience for submissions that predate the field, never the source of truth.

`export` runs the adapter backwards — pack folders → one flat submission JSON per
contributor, in exactly the `/author/` export shape, with `kangxi` stamped from the
folder name. That makes the flat submission the single canonical input format and
the pack tree a rebuildable staging area, rather than the first batch being a
special case that only exists as folders:

    python3 data/qc-pack.py export --out data/.cache/qc/submissions/
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

import paths

DATA = paths.DATA
DEFAULT_PACK = DATA / ".cache" / "qc" / "kangxi_radical_imagery"
FETCH = DATA / "fetch-referent-images.py"


def slugify(s):
    """The pack's folder-slug spelling: lowercase, spaces → hyphens (`short thread`
    is the folder `52 short-thread`)."""
    return re.sub(r"[^a-z0-9-]+", "-", s.strip().lower()).strip("-")


def pack_folders(root):
    """num → (folder path, folder slug) for every numbered folder in the pack."""
    out = {}
    for d in sorted(glob.glob(os.path.join(root, "*", ""))):
        name = os.path.basename(d.rstrip(os.sep))
        if not name or not name[0].isdigit():
            continue
        num, _, rest = name.partition(" ")
        out[int(num)] = (d.rstrip(os.sep), rest.strip())
    return out


def kangxi_by_meaning():
    """meaning → num from our own kangxi.json, the canonical numbering."""
    try:
        rads = json.load(open(DATA / "kangxi.json", encoding="utf-8"))["radicals"]
    except (OSError, ValueError, KeyError):
        return {}
    return {r["meaning"]: r["num"] for r in rads if r.get("meaning")}


def submission_jsons(folder):
    """The submission JSONs in one pack folder — everything but the marking webapp's
    `*-meta.json` sidecars."""
    return sorted(p for p in glob.glob(os.path.join(folder, "*.json"))
                  if not os.path.basename(p).endswith("-meta.json"))


def entry_key(data):
    """The referent key in a submission JSON, skipping `_contributor` &c."""
    return next((k for k in data if not k.startswith("_")), None)


def resolve_num(slug, ref, folders_by_slug, by_meaning, overrides):
    """(num, how) for a submission entry. An explicit --map wins, then the entry's own
    `kangxi` field, then a pack folder of that name, then kangxi.json's meaning. The
    last of those is a guess — a slug does not identify a radical — so it's reported
    as such. (None, reason) when we genuinely don't know."""
    for key in (slug, slugify(slug)):
        if key in overrides:
            return overrides[key], "--map"
    num = ref.get("kangxi")
    if isinstance(num, int):
        return num, "kangxi field"
    for key in (slug, slugify(slug)):
        if key in folders_by_slug:
            return folders_by_slug[key], "pack folder"
    if slug in by_meaning:
        return by_meaning[slug], "meaning guess"
    return None, "unresolved"


def cmd_add(args):
    root = os.path.abspath(args.pack)
    if not os.path.isdir(root):
        raise SystemExit(f"pack dir not found: {root}")
    sub = paths.read_json(args.submission)
    contributor = args.contributor or sub.get("_contributor", "")
    if not contributor:
        raise SystemExit("submission carries no `_contributor` — pass --contributor NAME")
    contributor = slugify(contributor)

    folders = pack_folders(root)
    by_slug = {slug: num for num, (_, slug) in folders.items()}
    by_meaning = kangxi_by_meaning()
    overrides = {}
    for m in args.map or []:
        k, _, v = m.partition("=")
        overrides[k.strip()] = int(v)

    planned, unresolved = [], []
    for slug, ref in sub.items():
        if slug.startswith("_") or not isinstance(ref, dict):
            continue
        num, how = resolve_num(slug, ref, by_slug, by_meaning, overrides)
        if num is None:
            unresolved.append(slug)
            continue
        if num in folders:
            folder, fslug = folders[num]
            fresh = False
        else:
            fslug = slugify(slug)
            folder, fresh = os.path.join(root, f"{num} {fslug}"), True
        images = []
        for i, im in enumerate(ref.get("images", []), 1):
            ext = os.path.splitext(im.get("file", ""))[1] or ".jpg"
            name = im.get("file", "") if args.keep_names else f"{fslug}-{contributor}-{i:02d}{ext}"
            images.append({**im, "file": name})
        planned.append({"num": num, "slug": slug, "fslug": fslug, "folder": folder,
                        "fresh": fresh, "how": how, "label": ref.get("label", slug),
                        "images": images})

    planned.sort(key=lambda p: p["num"])
    print(f"contributor {contributor!r} → {root}")
    for p in planned:
        mark = "NEW folder" if p["fresh"] else f"merge into {os.path.basename(p['folder'])}"
        rename = "" if p["slug"] == p["fslug"] else f"  ({p['slug']} → {p['fslug']})"
        print(f"  {p['num']:>3} {p['fslug']:<16} {len(p['images']):>2} images  "
              f"[{mark}]{rename}  ·{p['how']}")
    print(f"==> {len(planned)} radicals, {sum(len(p['images']) for p in planned)} images")
    guessed = [p for p in planned if p["how"] == "meaning guess"]
    if guessed:
        print(f"⚠ {len(guessed)} placed by MEANING GUESS (no `kangxi` field, no matching "
              f"folder) — check these, a slug doesn't identify a radical:")
        for p in guessed:
            print(f"    {p['slug']!r} → {p['num']}")
    if unresolved:
        print(f"\n⚠ UNRESOLVED ({len(unresolved)}) — no Kangxi number; pass --map slug=num:",
              file=sys.stderr)
        for s in unresolved:
            print(f"    {s}", file=sys.stderr)
    if args.dry_run:
        print("\n(dry-run — re-run without --dry-run to write the pack)")
        return 1 if unresolved else 0

    for p in planned:
        os.makedirs(os.path.join(p["folder"], "images"), exist_ok=True)
        dest = os.path.join(p["folder"], f"{p['fslug']}-{contributor}.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump({"_contributor": contributor,
                       p["fslug"]: {"label": p["label"], "kangxi": p["num"],
                                    "images": p["images"]}},
                      f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"\nwrote {len(planned)} submission JSON(s) into the pack")

    if args.fetch:
        failed = 0
        for p in planned:
            jf = os.path.join(p["folder"], f"{p['fslug']}-{contributor}.json")
            cmd = [sys.executable, str(FETCH), "--dest", os.path.join(p["folder"], "images"), jf]
            if args.short_edge is not None:
                cmd[3:3] = ["--short-edge", str(args.short_edge)]
            print(f"\n── {p['num']} {p['fslug']} ──")
            failed += subprocess.call(cmd) != 0
        if failed:
            print(f"\n⚠ {failed} radical(s) had a fetch that needs attention (see above)")
        print("\nnext: python3 data/qc-viewer.py")
        return 1 if (failed or unresolved) else 0
    print("next: python3 data/qc-pack.py add … --fetch   (or fetch-referent-images.py per folder)")
    return 1 if unresolved else 0


def cmd_tag(args):
    """Stamp `_contributor` onto submission JSONs that predate the field. The first
    pack was sourced before provenance was recorded per file; this names it so the
    viewer can tell one contributor's candidates from another's."""
    root = os.path.abspath(args.pack)
    name = slugify(args.name)
    touched, already = 0, 0
    for _num, (folder, _slug) in sorted(pack_folders(root).items()):
        for jf in submission_jsons(folder):
            data = json.load(open(jf, encoding="utf-8"))
            if data.get("_contributor"):
                already += 1
                continue
            if args.dry_run:
                print(f"WOULD TAG  {os.path.relpath(jf, root)}")
                touched += 1
                continue
            with open(jf, "w", encoding="utf-8") as f:
                json.dump({"_contributor": name, **data}, f, ensure_ascii=False, indent=2)
                f.write("\n")
            touched += 1
    verb = "would tag" if args.dry_run else "tagged"
    print(f"==> {verb} {touched} submission JSON(s) as {name!r}, {already} already attributed")
    return 0


def cmd_export(args):
    """Pack folders → one flat submission JSON per contributor, in the `/author/`
    export shape. This is `add` run backwards, and it's what lets the flat submission
    be the single canonical input: the first pack was delivered as folders and exists
    nowhere else, so without this it stays a permanent special case.

    The folder NUMBER is stamped onto each entry as `kangxi`, because that is the one
    piece of information the folder layout carries and the flat shape otherwise loses.
    Image bytes are not touched — they stay cached in the pack."""
    root = os.path.abspath(args.pack)
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    batches, collisions = {}, []
    for num, (folder, _slug) in sorted(pack_folders(root).items()):
        for jf in submission_jsons(folder):
            data = json.load(open(jf, encoding="utf-8"))
            key = entry_key(data)
            if key is None:
                continue
            who = data.get("_contributor") or args.unattributed
            entry = dict(data[key])
            entry["kangxi"] = num
            batch = batches.setdefault(who, {})
            # The flat shape is keyed by slug, but a slug does not identify a radical:
            # kangxi.json gives 144 行 and 162 辵 the same meaning ('walk'), as it does
            # 14 冖 and 146 襾 ('cover'). Suffix the number so one never silently
            # overwrites the other — `kangxi` still carries the truth either way.
            if key in batch:
                collisions.append((key, batch[key].get("kangxi"), num))
                batch[f"{key}-{num}"] = entry
            else:
                batch[key] = entry

    for who, refs in sorted(batches.items()):
        payload = {"_contributor": who, **{k: refs[k] for k in sorted(refs)}}
        dest = os.path.join(out_dir, f"imagery-{who}.json")
        n = sum(len(r.get("images", [])) for r in refs.values())
        if args.dry_run:
            print(f"WOULD WRITE  {dest}  ({len(refs)} referents, {n} images)")
            continue
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"wrote {dest}  ({len(refs)} referents, {n} images)")
    print(f"==> {len(batches)} contributor batch(es) → {out_dir}")
    if collisions:
        print(f"note: {len(collisions)} slug collision(s) disambiguated by number "
              "(same meaning, different radical):")
        for slug, first, second in collisions:
            print(f"    {slug!r}: kept {first}, wrote {second} as {slug}-{second}")
    return 0


def cmd_ls(args):
    root = os.path.abspath(args.pack)
    folders = pack_folders(root)
    by_contrib = {}
    for num, (folder, slug) in sorted(folders.items()):
        rows = []
        for jf in submission_jsons(folder):
            data = json.load(open(jf, encoding="utf-8"))
            key = entry_key(data)
            if key is None:
                continue
            who = data.get("_contributor", "—")
            n = len(data[key].get("images", []))
            by_contrib[who] = by_contrib.get(who, 0) + n
            rows.append(f"{who}:{n}")
        if rows:
            print(f"  {num:>3} {slug:<18} {'  '.join(rows)}")
    print(f"==> {len(folders)} folders · " + " · ".join(
        f"{who} {n} images" for who, n in sorted(by_contrib.items())))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pack", default=str(DEFAULT_PACK), help="pack dir (folder-per-radical)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="merge a flat submission JSON into the pack")
    a.add_argument("submission")
    a.add_argument("--contributor", default="", help="override the submission's _contributor")
    a.add_argument("--map", action="append", metavar="SLUG=NUM",
                   help="place a slug the pack can't resolve (repeatable)")
    a.add_argument("--keep-names", action="store_true",
                   help="keep the submission's own filenames instead of "
                        "<slug>-<contributor>-NN. Only for REBUILDING a batch that is "
                        "already in a pack (its image paths are what the viewer keys "
                        "Keep/Reject on) — a fresh batch must be renamed, or it collides.")
    a.add_argument("--fetch", action="store_true", help="also fetch the image bytes")
    a.add_argument("--short-edge", type=int, default=None, metavar="PX",
                   help="passed through to fetch-referent-images.py")
    a.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    a.set_defaults(fn=cmd_add)

    t = sub.add_parser("tag", help="stamp _contributor on untagged submission JSONs")
    t.add_argument("name")
    t.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    t.set_defaults(fn=cmd_tag)

    e = sub.add_parser("export", help="pack → flat /author/-shape submission per contributor")
    e.add_argument("--out", default=str(DEFAULT_PACK.parent / "submissions"),
                   help="directory to write imagery-<contributor>.json into")
    e.add_argument("--unattributed", default="unknown",
                   help="contributor name for submissions with no _contributor (run `tag` first)")
    e.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    e.set_defaults(fn=cmd_export)

    ls = sub.add_parser("ls", help="what's in the pack, by contributor")
    ls.set_defaults(fn=cmd_ls)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
