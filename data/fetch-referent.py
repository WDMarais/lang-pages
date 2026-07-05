#!/usr/bin/env python3
"""Fetch open-licensed referent images from Wikimedia Commons into the repo.

Referent images are homed on the REFERENT (a meaning), not the glyph, so one
curated asset serves every glyph that denotes it and doubles as the cross-program
label anchor (person/man). This pulls a 480px thumbnail from Commons, keeps only
free licenses (PD / CC0 / CC-BY / CC-BY-SA), records attribution + license +
source, and registers it in data/referents.json under the referent slug.

Multipass by design: cheap-to-fetch-and-check now, curate/replace later.

Usage:
    python3 data/fetch-referent.py <slug> "<search query>" [--label "<label>"] [-n N]
    e.g. python3 data/fetch-referent.py tree "tree isolated white background" -n 2
"""
import json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF_JSON = ROOT / "data" / "referents.json"
IMG_DIR = ROOT / "shared" / "referents"
API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia UA policy wants a descriptive agent + real contact. Read the contact
# from the env so a personal email is never committed to the repo:
#     export WIKIMEDIA_CONTACT="you@example.com"
CONTACT = os.environ.get("WIKIMEDIA_CONTACT", "").strip()
UA = {"User-Agent": f"lang-pages-referents/0.1 (educational flashcards; {CONTACT})"}
EXT = {"image/jpeg": "jpg", "image/png": "png"}
DELAY = 0.6  # be polite: serial, spaced requests (volume is tiny anyway)


def require_contact():
    if not CONTACT:
        sys.exit("Set WIKIMEDIA_CONTACT (email or URL) — Wikimedia's UA policy "
                 "requires a real contact.  export WIKIMEDIA_CONTACT='you@example.com'")


def api(**params):
    params.setdefault("format", "json")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    time.sleep(DELAY)
    return out


def is_free(lic):
    """Free-culture only: PD / CC0 / CC-BY / CC-BY-SA. Explicitly reject the
    non-free CC modifiers NonCommercial (-nc) and NoDerivatives (-nd), plus
    fair-use / all-rights-reserved. GFDL-only is skipped (attribution too onerous
    for our use)."""
    l = (lic or "").strip().lower()
    if not l or "-nc" in l or "-nd" in l or "fair use" in l or "all rights" in l:
        return False
    return (l.startswith("pd") or "pdm" in l or "cc0" in l
            or "public domain" in l or "cc by" in l or "cc-by" in l)


def search(query, limit=12):
    d = api(action="query", list="search", srsearch=query,
            srnamespace=6, srlimit=limit)
    return [h["title"] for h in d.get("query", {}).get("search", [])]


def info(title):
    d = api(action="query", titles=title, prop="imageinfo",
            iiprop="url|extmetadata|mime", iiurlwidth=480)
    pages = d.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    ii = (page.get("imageinfo") or [None])[0]
    return ii


def plain(html):
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()


def fetch(slug, query, label, n):
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    store = json.loads(REF_JSON.read_text()) if REF_JSON.exists() else {}
    ent = store.setdefault(slug, {"label": label or slug, "images": []})
    if label:
        ent["label"] = label
    have = {im["file"] for im in ent["images"]}
    added = 0
    for title in search(query):
        if added >= n:
            break
        ii = info(title)
        if not ii or ii.get("mime") not in EXT:
            continue
        meta = ii.get("extmetadata", {})
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if not is_free(lic):
            print(f"  skip (license {lic!r}): {title}")
            continue
        url = ii.get("thumburl") or ii.get("url")
        fname = f"{slug}-{len(ent['images']) + 1:02d}.{EXT[ii['mime']]}"
        if fname in have:
            continue
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                (IMG_DIR / fname).write_bytes(r.read())
        except Exception as e:
            print(f"  download failed: {title} ({e})")
            continue
        ent["images"].append({
            "file": fname,
            "credit": plain((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons",
            "license": lic,
            "source": ii.get("descriptionurl", ""),
        })
        added += 1
        print(f"  + {fname}  «{plain(title)}»  [{lic}]")
    REF_JSON.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n")
    print(f"{slug}: added {added} (total {len(ent['images'])})")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 1
    require_contact()
    slug, query = argv[0], argv[1]
    label, n = None, 1
    i = 2
    while i < len(argv):
        if argv[i] == "--label":
            label = argv[i + 1]; i += 2
        elif argv[i] == "-n":
            n = int(argv[i + 1]); i += 2
        else:
            i += 1
    fetch(slug, query, label, n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
