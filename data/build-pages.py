#!/usr/bin/env python3
"""Project the symbol substrate onto the lang-pages card files.

    data/symbols/*.json  ──(membership rules in symbols_io)──▶
        radicals/radicals.json     on_radicals
        strokes/strokes.json       on_strokes
        characters/characters.json on_characters

The card files are GENERATED (kept committed so deploy stays build-free). Which
page a glyph lands on is now a projection rule, not a stored 'source' — 泉/線/三
leave /radicals/ because nothing teaches them as a radical and they aren't Kangxi
radicals; they surface on /characters/ (the full standalone-character inventory).

Emits the hand-authored house format so diffs stay reviewable.
Run: python3 data/build-pages.py
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from symbols_io import (load_symbols, to_card, ROOT,
                        on_strokes, on_radicals, on_characters)


def s(v):
    return json.dumps(v, ensure_ascii=False)


def inline_obj(d, order):
    return "{ " + ", ".join(f"{s(k)}: {s(d[k])}" for k in order if k in d) + " }"


def lang_block(v):
    seg = [f'{s("name")}: {s(v["name"])}, {s("reading")}: {s(v.get("reading",""))}, '
           f'{s("gloss")}: {s(v.get("gloss",""))}']
    if "extra" in v:
        seg.append(f'{s("extra")}: {s(v["extra"])}')
    if "appearsIn" in v:
        seg.append(f'{s("appearsIn")}: ' + inline_obj(v["appearsIn"], ["char", "reading", "gloss"]))
    return "{\n            " + ",\n            ".join(seg) + "\n          }"


def emit_card(c):
    L = ["        {"]
    for k in ("glyph", "slug", "tag", "image", "hw"):
        L.append(f'          {s(k)}: {s(c[k])},')
    L.append(f'          "cn": {lang_block(c["cn"])},')
    L.append(f'          "jp": {lang_block(c["jp"])},')
    tail = []
    if "kanji" in c:
        tail.append(("kanji", inline_obj(c["kanji"], ["name", "readings", "on", "kun", "level"])))
    if "pd" in c:
        tail.append(("pd", inline_obj(c["pd"], ["name", "level", "kind", "icon"])))
    wk = "null" if c["wk"] is None else inline_obj(c["wk"], ["name", "level", "kind", "glyph", "icon"])
    L.append(f'          "wk": {wk}' + ("," if tail else ""))
    for i, (k, v) in enumerate(tail):
        L.append(f'          {s(k)}: {v}' + ("," if i < len(tail) - 1 else ""))
    L.append("        }")
    return "\n".join(L)


def dump_cardfile(cards):
    body = ",\n".join(emit_card(c) for c in cards)
    return ('{\n  "groups": [\n    {\n      "title": "",\n      "sub": "",\n'
            '      "cards": [\n' + body + "\n      ]\n    }\n  ]\n}\n")


def main():
    syms = load_symbols()
    pages = [
        ("strokes",    ROOT / "strokes/strokes.json",       on_strokes),
        ("radicals",   ROOT / "radicals/radicals.json",     on_radicals),
        ("characters", ROOT / "characters/characters.json", on_characters),
    ]
    for name, path, rule in pages:
        cards = [to_card(sym) for sym in syms.values() if rule(sym)]
        path.parent.mkdir(exist_ok=True)
        text = dump_cardfile(cards)
        # validity + content check: reparse must equal the projected cards
        reparsed = [c for grp in json.loads(text)["groups"] for c in grp["cards"]]
        assert reparsed == cards, f"{name}: emit/parse mismatch"
        path.write_text(text)
        print(f"{name+'.json':24} {len(cards):3} cards")

    off_radicals = [g for g, sym in syms.items()
                    if sym["class"] == "char" and not on_radicals(sym)]
    print("chars NOT on /radicals/ (character-only):", " ".join(off_radicals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
