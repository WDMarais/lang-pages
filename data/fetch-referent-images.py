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
     (the linker sets it on search-picked non-Wikimedia images, e.g. Flickr).
     Fetched as-is: no resize, same as any direct URL.
  2. `source` is a Wikimedia `File:` page  → the official Special:FilePath endpoint,
     fetched at a computed width so the SHORT edge lands at --short-edge (default
     800px, the general-spec minimum). ?width= alone would undershoot the short
     edge on landscape images, so the width is derived from the real aspect ratio
     via one imageinfo API call. An image already at/below the target isn't upscaled.
     The `File:` name is read from the path OR the fragment, since Commons' own
     media viewer links look like `/wiki/Main_Page#/media/File:Foo.jpg`.
  3. `source` is itself a direct image URL (ends .jpg/.png/…) → used as-is (no
     server-side resize possible off-wiki).
  4. `source` is an HTML landing page (Flickr photo page &c.) → its `og:image`
     meta tag, which every such page carries and which points straight at the
     bytes. Flickr's own size suffix is upgraded to `_b` (1024px long edge) when
     the page advertises something smaller, with a fallback to the advertised URL.
  5. otherwise → reported as needing a manual download (no auto-fetchable URL).

Bytes land at --dest (default shared/referents/) under the name the referent entry
declares — point --dest at a QC pack's `images/` dir to stage a batch for review
instead of folding it straight into the store. Idempotent: an existing file is left
alone unless --force. Local originals (empty source, e.g. a CC0 lang-pages SVG) are
skipped, not an error.

Guardrails, since this pulls arbitrary URLs onto the box: a 20 MB per-file cap, a
content-type must be image/*, a descriptive UA, a 30 s timeout, and `file` must be
a bare name (no '/' or '..') so a typo/bad submission can't write outside the dir.

Fetch only — it does not touch referents.json. After it runs, merge the
submission's image entries into referents.json (dropping any `_contributor` /
`_download`) and run `python3 data/build.py`.

Exit: 0 all resolved · 1 something failed or needs a manual download.
"""
import argparse
import html
import json
import pathlib
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
PAGE_CAP = 512 * 1024  # only the <head> is wanted off a landing page
OG_IMAGE = re.compile(
    r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']"""
    r"""|<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']""", re.I)
# Flickr static names end `_<suffix>.jpg`: _m 240 · _n 320 · _z 640 · _c 800 · _b 1024.
# The spec wants a short edge of 800, so anything under `_b` is worth upgrading.
FLICKR_SMALL = re.compile(r"(_[mnzc])(\.[a-z]+)$", re.I)


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
    Works for any wiki host (Commons, Wikipedia). The name lives in the path on a
    plain file page (`/wiki/File:Foo.jpg`) but in the FRAGMENT when the link came
    from Commons' media viewer (`/wiki/Main_Page#/media/File:Foo.jpg`)."""
    parts = urllib.parse.urlsplit(source)
    if not parts.netloc.endswith((".wikimedia.org", ".wikipedia.org")):
        return None, None
    for candidate, pattern in ((parts.path, r"/wiki/File:(.+)$"),
                               (parts.fragment, r"/media/File:(.+)$")):
        m = re.match(pattern, candidate)
        if m:
            return parts.netloc, urllib.parse.unquote(m.group(1))
    return None, None


def is_landing_page(source):
    """True for an HTML page we know carries an `og:image` pointing at the real file.
    Kept to hosts actually seen in submissions rather than 'anything with no image
    extension', so a typo'd source still surfaces as a manual download."""
    host = urllib.parse.urlsplit(source).netloc.lower()
    return host == "flickr.com" or host.endswith((".flickr.com", ".flic.kr"))


def resolve(im):
    """Classify one image entry → (kind, payload, note), no network. kind is one of
    'wiki' (payload=(host,name)), 'direct' (payload=url), 'page' (payload=url, the
    landing page to read og:image off), 'local'/'manual' (payload=None)."""
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
    if is_landing_page(src):
        return "page", src, "landing page → og:image"
    return "manual", None, f"no auto-fetchable URL — download by hand from {src}"


def og_image(page_url):
    """The `og:image` URL a landing page advertises, or raise. Reads only the head of
    the document — the tag lives in <head>, and the body can be megabytes."""
    with _open(page_url) as r:
        head = r.read(PAGE_CAP).decode("utf-8", "replace")
    m = OG_IMAGE.search(head)
    if not m:
        raise ValueError("no og:image meta tag on the landing page")
    return urllib.parse.urljoin(page_url, html.unescape(m.group(1) or m.group(2)))


def flickr_variants(url):
    """Candidate URLs for a Flickr static image, best first. A page advertising a
    small size (`_z` 640px) still has the `_b` 1024px render, which is what the
    800px short-edge spec wants; the advertised URL stays as the fallback."""
    m = FLICKR_SMALL.search(url)
    if not m or "staticflickr.com" not in urllib.parse.urlsplit(url).netloc:
        return [url]
    return [FLICKR_SMALL.sub(r"_b\2", url), url]


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


def fetch_urls_for(kind, payload, target):
    """Candidate URLs to GET for a resolved (kind, payload), best first — the caller
    takes the first that yields bytes. Direct URLs pass through; wiki files get one
    imageinfo call so the short edge hits `target`; a landing page is read for its
    og:image (and, on Flickr, offered at the larger `_b` render first)."""
    if kind == "direct":
        return [payload]
    if kind == "page":
        return flickr_variants(og_image(payload))
    host, name = payload
    dims = wiki_dims(host, name)
    width = scaled_width(*dims, target) if dims else 0
    return [wiki_url(host, name, width) if width else wiki_url(host, name, 0).split("?")[0]]


def fetch_first(urls):
    """Bytes from the first candidate that works, else re-raise the last error."""
    for i, url in enumerate(urls):
        try:
            return fetch(url)
        except (urllib.error.URLError, ValueError, OSError):
            if i == len(urls) - 1:
                raise
    raise ValueError("no candidate URLs")


def main(argv):
    ap = argparse.ArgumentParser(description="Fetch referent images from submission JSON(s).")
    ap.add_argument("files", nargs="+", help="submission JSON file(s) (or referents.json)")
    ap.add_argument("--short-edge", type=int, default=800, metavar="PX",
                    help="target short-edge px for Wikimedia files (default 800; 0 = original)")
    ap.add_argument("--dest", default=str(REFDIR), metavar="DIR",
                    help="where the bytes land (default shared/referents/; point at a QC "
                         "pack's images/ dir to stage a batch for review instead)")
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, fetch nothing")
    args = ap.parse_args(argv)

    dest_dir = pathlib.Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)
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
            dest = dest_dir / name
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
                where = (f"Special:FilePath/{payload[1]} (≥{args.short_edge}px)" if kind == "wiki"
                         else f"og:image of {payload}" if kind == "page" else payload)
                print(f"WOULD FETCH  {tag:<28} ← {where}  [{note}]")
                fetched += 1
                continue
            try:
                data = fetch_first(fetch_urls_for(kind, payload, args.short_edge))
                dest.write_bytes(data)
                print(f"fetched      {tag:<28} {len(data)//1024} KB  [{note}]")
                fetched += 1
            except (urllib.error.URLError, ValueError, OSError, KeyError) as e:
                failures.append((tag, f"{type(e).__name__}: {e}"))

    verb = "would fetch" if args.dry_run else "fetched"
    print(f"\n==> {verb} {fetched}, skipped {skipped} present, {local} local original(s)"
          f"  → {dest_dir}")
    if failures:
        print(f"==> {len(failures)} need attention:")
        for tag, reason in failures:
            print(f"    {tag}: {reason}")
        return 1
    if not args.dry_run and fetched and dest_dir.resolve() == REFDIR.resolve():
        print("==> next: merge the image entries into data/referents.json "
              "(drop _contributor/_download), then python3 data/build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
