#!/usr/bin/env python3
"""Verify the live site serves exactly what the given git ref contains.

nginx serves /var/www/lang-pages — a plain git clone — so a deploy is just a
pull. When that pull is skipped, drift is not always loud: a file added since
the last pull 404s, but a file *modified* since then still returns 200 with
stale bytes. The silent case is the one this catches.

Compares content hashes, not sizes: the CN clips collide on size often enough
that a size check is no check at all (heng2/na4 are both 10656 bytes). The hash
we compare against is the ref's blob objectname, and git's blob hash of the
downloaded bytes must equal it — recomputed locally (no git call per file), which
is exact here because the repo has no .gitattributes filters.

Gentle on the box: keep-alive connections are reused (one per worker thread), so
a full sweep opens ~JOBS connections rather than a fresh TCP+TLS handshake per
file — the actual cost of a 1000-file check against a small instance.

  python3 scripts/check-deploy.py                        # audio banks + page data
  python3 scripts/check-deploy.py 'audio/cn/*.mp3'       # any glob (matched vs the ref's paths)
  HOST=localhost:8765 python3 scripts/check-deploy.py    # point at the dev server

Env: HOST (default cn.wdmarais.dev), REF (default origin/main), JOBS (default 24).
Exit: 0 all match · 1 drift found · 2 no tracked file matched the patterns.

Ported from the original bash version, whose two bugs were both shell footguns:
ls-tree does not accept glob pathspecs (so patterns are matched in-process), and
it C-quotes non-ASCII paths by default (dropping every CJK-named file) — handled
here by fnmatch and core.quotePath=false respectively.
"""
import fnmatch
import hashlib
import http.client
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# scripts/ -> repo root. Mirrors data/paths.py's idiom; not imported from it,
# since deploy tooling deliberately does not reach into the data pipeline.
ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PATTERNS = ["audio/*.mp3", "*.json"]
UA = "lang-pages-check-deploy (+https://github.com/WDMarais/lang-pages)"

# One keep-alive connection per worker thread, reused across the files that
# thread handles. Thread-local because http.client connections are not safe to
# share across threads.
_local = threading.local()


def git_blob_sha1(data):
    """The objectname `git hash-object` gives these bytes: sha1 of the blob
    header + content. Equals ls-tree's %(objectname) for an unfiltered blob."""
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def expected(ref, patterns):
    """(objectname, path) for every tracked path in `ref` matching a pattern.
    core.quotePath=false so non-ASCII paths arrive as literal UTF-8, not C-quoted
    octal — otherwise every CJK-named file silently misses the globs. `*` in a
    pattern spans '/' (fnmatch, like the original bash [[ == ]])."""
    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", "ls-tree", "-r",
         "--format=%(objectname) %(path)", ref],
        cwd=ROOT, capture_output=True, text=True, check=True)
    items = []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        obj, path = line.split(" ", 1)
        if any(fnmatch.fnmatchcase(path, p) for p in patterns):
            items.append((obj, path))
    return items


def _connection(scheme, host):
    """This thread's live connection, opened on first use and kept for reuse."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn
    hostname, _, port = host.partition(":")
    if scheme == "https":
        conn = http.client.HTTPSConnection(hostname, int(port) if port else 443, timeout=30)
    else:
        conn = http.client.HTTPConnection(hostname, int(port) if port else 80, timeout=30)
    _local.conn = conn
    return conn


def _drop():
    """Discard this thread's connection (closed/broken); the next call reopens."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def probe(scheme, host, ref, item):
    """Fetch one path over the thread's keep-alive connection; return a drift
    line (MISSING / STALE) or None if it matches. One retry, on connection errors
    only: a server may close an idle keep-alive connection mid-sweep, which must
    not read as drift — but a genuinely-down box is not re-hit per file."""
    obj, path = item
    target = "/" + urllib.parse.quote(path, safe="/")
    code = body = None
    for attempt in (0, 1):
        try:
            conn = _connection(scheme, host)
            conn.request("GET", target, headers={"User-Agent": UA})
            resp = conn.getresponse()
            body = resp.read()  # drain fully so the connection stays reusable
            code = resp.status
            break
        except (OSError, http.client.HTTPException):
            _drop()
            if attempt == 0:
                time.sleep(0.25)
                continue
            return f"MISSING  {path}  (HTTP 000)"
    if code != 200:
        return f"MISSING  {path}  (HTTP {code})"
    if git_blob_sha1(body) != obj:
        return f"STALE    {path}  (200, but content differs from {ref})"
    return None


def main(argv):
    host = os.environ.get("HOST", "cn.wdmarais.dev")
    ref = os.environ.get("REF", "origin/main")
    jobs = int(os.environ.get("JOBS", "24"))
    patterns = argv or DEFAULT_PATTERNS
    scheme = "http" if host.startswith(("localhost", "127.0.0.1")) else "https"

    items = expected(ref, patterns)
    if not items:
        print(f"no tracked files match: {' '.join(patterns)}", file=sys.stderr)
        return 2

    print(f"==> checking {len(items)} files on {host} against {ref}")
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        drift = [d for d in pool.map(lambda it: probe(scheme, host, ref, it), items) if d]

    if not drift:
        print(f"==> ok: all {len(items)} files match {ref}")
        return 0

    for line in sorted(drift):
        print(line)
    print()
    print(f"==> {len(drift)} of {len(items)} files drifted -- the box needs:")
    print("    cd /var/www/lang-pages && git pull --ff-only")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
