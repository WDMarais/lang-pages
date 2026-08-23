#!/usr/bin/env python3
"""Batch-fetch referent images from a contributor submission into shared/referents/.

The imagery linker (/author/) exports a submission JSON — {slug: {label, images:[…]}}
— but never the image *bytes*: a contributor curates licensing metadata, the
maintainer fetches the files. This is that fetch, automated. Point it at one or
more submission JSONs (or referents.json itself, to backfill missing files):

    python3 data/fetch-referent-images.py mountain.json bird.json
    python3 data/fetch-referent-images.py --dry-run mountain.json     # plan only
    python3 data/fetch-referent-images.py --force referents.json      # re-download
    python3 data/fetch-referent-images.py --short-edge 0 mountain.json # originals, no resize

For each image it resolves a fetchable URL, in order:
  1. `_download` — an explicit direct image URL, if the submission carries one
     (the export-only preview field; only needed for non-Wikimedia sources).
  2. `source` is a Wikimedia `File:` page  → the official Special:FilePath endpoint,
     fetched at a computed width so the SHORT edge lands at --short-edge (default
     800px, the general-spec minimum). ?width= alone would undershoot the short
     edge on landscape images, so the width is derived from the real aspect ratio
     via one imageinfo API call. An image already at/below the target isn't upscaled.
  3. `source` is itself a direct image URL (ends .jpg/.png/…) → used as-is (no
     server-side resize possible off-wiki).
  4. otherwise → reported as needing a manual download (no auto-fetchable URL).

Bytes land at shared/referents/<file> (the name the referent entry already
declares). Idempotent: an existing file is left alone unless --force. Local
originals (empty source, e.g. a CC0 lang-pages SVG) are skipped, not an error.

Guardrails, since this pulls arbitrary URLs onto the box: a 20 MB per-file cap, a
content-type must be image/*, a descriptive UA, a 30 s timeout, and `file` must be
a bare name (no '/' or '..') so a typo/bad submission can't write outside the dir.

Fetch only — it does not touch referents.json. After it runs, merge the
submission's image entries into referents.json (dropping any `_contributor` /
`_download`) and run `python3 data/build.py`.

Exit: 0 all resolved · 1 something failed or needs a manual download.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import paths

REFDIR = paths.ROOT / "shared" / "referents"
UA = "lang-pages fetch-referent-images (+https://github.com/WDMarais/lang-pages)"
CAP = 20 * 1024 * 1024  # per-file byte cap
PACE = 0.25  # courtesy delay before each request — Wikimedia 429s a rapid bulk sweep
IMG_EXT = re.compile(r"\.(jpe?g|png|gif|webp|svg)(?:$|[?#])", re.I)


def _open(url, timeout=30):
    """GET with the UA, a courtesy pace, and a bounded retry on 429 (honours
    Retry-After). Wikimedia rate-limits a fast bulk fetch; this keeps it polite."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        time.sleep(PACE)
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(min(int(e.headers.get("Retry-After") or 0) or 2 * (attempt + 1), 30))
                continue
            raise


def wiki_file(source):
    """(host, unquoted filename) for a Wikimedia `File:` page URL, else (None, None).
    Works for any wiki host (Commons, Wikipedia)."""
    parts = urllib.parse.urlsplit(source)
    if not parts.netloc.endswith((".wikimedia.org", ".wikipedia.org")):
        return None, None
    m = re.match(r"/wiki/File:(.+)$", parts.path)
    if not m:
        return None, None
    return parts.netloc, urllib.parse.unquote(m.group(1))


def resolve(im):
    """Classify one image entry → (kind, payload, note), no network. kind is one of
    'wiki' (payload=(host,name)), 'direct' (payload=url), 'local'/'manual' (payload=None)."""
    dl = (im.get("_download") or "").strip()
    src = (im.get("source") or "").strip()
    if dl:
        return "direct", dl, "direct (_download)"
    if not src:
        return "local", None, "local original (empty source) — nothing to fetch"
    host, name = wiki_file(src)
    if name:
        return "wiki", (host, name), "Wikimedia Special:FilePath"
    if IMG_EXT.search(src):
        return "direct", src, "direct source URL"
    return "manual", None, f"no auto-fetchable URL — download by hand from {src}"


def wiki_dims(host, name):
    """(width, height) of a Wikimedia file via the imageinfo API, or None."""
    api = f"https://{host}/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo",
        "iiprop": "size", "redirects": "1", "titles": f"File:{name}"})
    with _open(api) as r:
        doc = json.load(r)
    for page in doc.get("query", {}).get("pages", {}).values():
        ii = page.get("imageinfo")
        if ii:
            return ii[0]["width"], ii[0]["height"]
    return None


def scaled_width(w, h, target):
    """Width that puts the SHORT edge at `target` px. Never upscales; target<=0 or
    an already-small image returns the original width (fetch as-is)."""
    short = min(w, h)
    if target <= 0 or short <= target:
        return w
    return max(1, round(w * target / short))


def wiki_url(host, name, width):
    """Special:FilePath URL for `name`, at `width` px (302s to the scaled render)."""
    base = f"https://{host}/wiki/Special:FilePath/{urllib.parse.quote(name, safe='')}"
    return f"{base}?width={width}"


def fetch(url):
    """Return the image bytes, or raise. Enforces the size cap and image/* type."""
    with _open(url) as r:  # follows redirects
        ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
        data = r.read(CAP + 1)
    if len(data) > CAP:
        raise ValueError(f"exceeds {CAP // 1024 // 1024} MB cap")
    if ctype and not ctype.startswith("image/"):
        raise ValueError(f"not an image (Content-Type: {ctype}) — probably an error page")
    return data


def safe_name(name):
    """A referent `file` must be a bare filename — reject traversal / absolute paths."""
    return name and "/" not in name and "\\" not in name and ".." not in name


def images_of(submission):
    """Yield (slug, image_dict) across the submission's referents, skipping
    `_contributor` and any other top-level underscore key."""
    for slug, ref in submission.items():
        if slug.startswith("_") or not isinstance(ref, dict):
            continue
        for im in ref.get("images", []):
            yield slug, im


def fetch_url_for(kind, payload, target):
    """The concrete URL to GET for a resolved (kind, payload). Does the imageinfo
    call for wiki files so the short edge hits `target`; direct URLs pass through."""
    if kind == "direct":
        return payload
    host, name = payload
    dims = wiki_dims(host, name)
    width = scaled_width(*dims, target) if dims else 0
    return wiki_url(host, name, width) if width else wiki_url(host, name, 0).split("?")[0]


def main(argv):
    ap = argparse.ArgumentParser(description="Fetch referent images from submission JSON(s).")
    ap.add_argument("files", nargs="+", help="submission JSON file(s) (or referents.json)")
    ap.add_argument("--short-edge", type=int, default=800, metavar="PX",
                    help="target short-edge px for Wikimedia files (default 800; 0 = original)")
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, fetch nothing")
    args = ap.parse_args(argv)

    REFDIR.mkdir(parents=True, exist_ok=True)
    fetched = skipped = local = 0
    failures = []  # (file, reason) — anything a human must chase

    for f in args.files:
        submission = paths.read_json(f)
        for slug, im in images_of(submission):
            name = (im.get("file") or "").strip()
            tag = f"{slug}/{name or '<no file>'}"
            if not safe_name(name):
                failures.append((tag, "missing or unsafe `file` name"))
                continue
            dest = REFDIR / name
            if dest.exists() and not args.force:
                skipped += 1
                continue
            kind, payload, note = resolve(im)
            if kind == "local":
                local += 1
                continue
            if kind == "manual":
                failures.append((tag, note))
                continue
            if args.dry_run:
                where = payload if kind == "direct" else f"Special:FilePath/{payload[1]} (≥{args.short_edge}px)"
                print(f"WOULD FETCH  {tag:<28} ← {where}  [{note}]")
                fetched += 1
                continue
            try:
                data = fetch(fetch_url_for(kind, payload, args.short_edge))
                dest.write_bytes(data)
                print(f"fetched      {tag:<28} {len(data)//1024} KB  [{note}]")
                fetched += 1
            except (urllib.error.URLError, ValueError, OSError, KeyError) as e:
                failures.append((tag, f"{type(e).__name__}: {e}"))

    verb = "would fetch" if args.dry_run else "fetched"
    print(f"\n==> {verb} {fetched}, skipped {skipped} present, {local} local original(s)")
    if failures:
        print(f"==> {len(failures)} need attention:")
        for tag, reason in failures:
            print(f"    {tag}: {reason}")
        return 1
    if not args.dry_run and fetched:
        print("==> next: merge the image entries into data/referents.json "
              "(drop _contributor/_download), then python3 data/build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
