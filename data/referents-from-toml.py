#!/usr/bin/env python3
"""Merge a friendly TOML inbox of hand-found referent images into referents.json.

Non-technical contributors author `data/referents-inbox.toml` as flat `[[image]]`
blocks — plain `key = "value"` lines, no JSON, no nesting. This folds them into
`data/referents.json` deterministically: NO LLM in the loop, so the
credit / license / source strings can't be silently altered on the way in (the one
place a transcription slip is expensive). Run `check-source.py` afterwards as usual.

Usage:
    python3 data/referents-from-toml.py                 # merge data/referents-inbox.toml
    python3 data/referents-from-toml.py <inbox.toml>    # merge a named inbox
    python3 data/referents-from-toml.py --check         # validate only, write nothing

Exit: 0 clean · 1 hard error(s) (nothing written) · 2 load failure.
"""
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        sys.exit("Need Python 3.11+ (tomllib) or `pip install tomli`.")

from paths import ROOT, read_json, write_json

REF_JSON = ROOT / "data" / "referents.json"
DEFAULT_INBOX = ROOT / "data" / "referents-inbox.toml"
REQUIRED = ("slug", "label", "file", "credit", "license", "source")

# Free-to-redistribute licenses only. Anything NC / ND / "all rights reserved" is
# a hard reject; anything unrecognised is a warning to eyeball, not a silent pass.
FREE_MARKERS = ("CC0", "PUBLIC DOMAIN", "CC-BY", "CC BY")
BLOCKED_MARKERS = ("-NC", " NC", "-ND", " ND", "ALL RIGHTS", "COPYRIGHT")


def license_verdict(lic: str) -> str:
    """'ok' | 'blocked' | 'unknown' for a license string."""
    up = f" {lic.upper()} "
    if any(b in up for b in BLOCKED_MARKERS):
        return "blocked"
    if any(m in up for m in FREE_MARKERS):
        return "ok"
    return "unknown"


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--check"]
    check_only = "--check" in sys.argv
    inbox = (ROOT / args[0]) if args else DEFAULT_INBOX
    if not inbox.exists():
        print(f"no inbox at {inbox} — nothing to do")
        return 0

    try:
        blocks = tomllib.loads(inbox.read_text(encoding="utf-8")).get("image", [])
    except tomllib.TOMLDecodeError as e:
        print(f"could not parse {inbox.name}: {e}")
        return 2

    errors, warns, staged = [], [], []
    for i, b in enumerate(blocks, 1):
        where = f"[[image]] #{i}"
        missing = [k for k in REQUIRED if not str(b.get(k, "")).strip()]
        if missing:
            errors.append(f"{where}: missing/empty {', '.join(missing)}")
            continue
        verdict = license_verdict(b["license"])
        if verdict == "blocked":
            errors.append(f"{where} ({b['file']}): non-free license {b['license']!r} — reject")
            continue
        if verdict == "unknown":
            warns.append(f"{where} ({b['file']}): unrecognised license {b['license']!r} — check by hand")
        staged.append(b)

    for w in warns:
        print(f"  warn: {w}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"\n{len(errors)} hard error(s) — nothing written. Fix the inbox and re-run.")
        return 1

    refs = read_json(REF_JSON) if REF_JSON.exists() else {}
    added, skipped = 0, 0
    for b in staged:
        entry = refs.setdefault(b["slug"], {"label": b["label"], "images": []})
        entry.setdefault("label", b["label"])
        entry.setdefault("images", [])
        if any(img.get("file") == b["file"] for img in entry["images"]):
            skipped += 1
            continue
        entry["images"].append(
            {k: b[k].strip() for k in ("file", "credit", "license", "source")}
        )
        added += 1

    if check_only:
        print(f"check ok: {added} to add, {skipped} already present, {len(warns)} warning(s)")
        return 0

    write_json(REF_JSON, refs)
    print(f"merged {added} image(s) into {REF_JSON.name} "
          f"({skipped} already present, {len(warns)} warning(s)). "
          f"Now run: python3 data/check-source.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
