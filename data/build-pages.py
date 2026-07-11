#!/usr/bin/env python3
"""Project the symbol substrate onto the lang-pages card files.

    data/symbols/*.json  ──(membership rules in symbols_io)──▶
        strokes/strokes.json       on_strokes
        characters/characters.json on_characters
        kangxi/kangxi.json         on_kangxi ⋈ data/kangxi.json (the 214 spine)

The card files are GENERATED (kept committed so deploy stays build-free). Which
page a glyph lands on is a projection rule, not a stored 'source'. The radical
axis is now the canonical 214 Kangxi radicals: /kangxi/ joins our kangxi-tagged
symbols to the reference spine BY NUMBER — a real card where we have the symbol,
a greyed stub where we don't — so the page is an honest, completable deck. The
old /radicals/ page (Kangxi ∪ component ∪ program-radical) is retired; its chars
were already on /characters/, its Kangxi entries move here, and the handful of
non-Kangxi components (ナ ト メ 𠂉) ride along as an annex.

strokes/characters emit the hand-authored house format so diffs stay reviewable;
the big generated kangxi page uses plain indented JSON.
Run: python3 data/build-pages.py
"""
import json, sys
from collections import defaultdict

from paths import ROOT, DATA, read_json
from phonetics import audio_key
from symbols_io import (
    load_symbols,
    to_card,
    referent_slug,
    on_strokes,
    on_kangxi,
    on_components,
    on_characters,
    PROGRAM_TIERS,
    TIER_BY_CARD,
)


def stamp_cn_audio(card):
    """Stamp the CN syllable-bank key(s) so cards3.js can resolve audio to the shared
    /audio/cn/ bank without any normalization of its own. A single bank-eligible
    reading gets cnAudioKey (千→qian1); its example reading gets cnExAudioKey. Multi-
    syllable readings (stroke names) get neither and fall back to the per-slug clip."""
    cn = card.get("cn") or {}
    if k := audio_key(cn.get("reading")):
        card["cnAudioKey"] = k
    if k := audio_key((cn.get("appearsIn") or {}).get("reading")):
        card["cnExAudioKey"] = k


def load_referents():
    """Referent-keyed image store (data/referents.json) → {slug: [{src, credit}]}.
    Homed on the referent, not the glyph, so one curated asset serves every glyph
    that denotes it (木/林/森 → tree) and doubles as the cross-program label anchor."""
    path = DATA / "referents.json"
    if not path.exists():
        return {}
    raw = read_json(path)
    return {slug: [{"src": f"../shared/referents/{im['file']}",
                    "credit": im.get("credit", ""), "license": im.get("license", "")}
                   for im in ent.get("images", [])]
            for slug, ent in raw.items()}


def attach_referents(card, refmap):
    """Attach the referent's images to a card via its meaning-slug (CN gloss)."""
    gloss = card.get("cn", {}).get("gloss", "")
    imgs = refmap.get(referent_slug(gloss)) if gloss else None
    if imgs:
        card["referents"] = [{"label": gloss, "images": imgs}]


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
    for k in ("cnAudioKey", "cnExAudioKey"):  # optional — present only for bank-eligible readings
        if k in c:
            L.append(f'          {s(k)}: {s(c[k])},')
    L.append(f'          "cn": {lang_block(c["cn"])},')
    L.append(f'          "jp": {lang_block(c["jp"])},')
    # program tiers — order + per-tier field lists come from the PROGRAM_TIERS
    # registry (symbols_io). The always-present tier (WK radical) leads and may be
    # null; the rest form a trailing block only when the card carries them.
    tail = [(t["card"], inline_obj(c[t["card"]], t["fields"]))
            for t in PROGRAM_TIERS if not t.get("always") and t["card"] in c]
    lead = next(t for t in PROGRAM_TIERS if t.get("always"))
    lv = "null" if c[lead["card"]] is None else inline_obj(c[lead["card"]], lead["fields"])
    L.append(f'          {s(lead["card"])}: {lv}' + ("," if tail else ""))
    for i, (k, v) in enumerate(tail):
        L.append(f'          {s(k)}: {v}' + ("," if i < len(tail) - 1 else ""))
    L.append("        }")
    return "\n".join(L)


def dump_cardfile(cards):
    body = ",\n".join(emit_card(c) for c in cards)
    return ('{\n  "groups": [\n    {\n      "title": "",\n      "sub": "",\n'
            '      "cards": [\n' + body + "\n      ]\n    }\n  ]\n}\n")


def build_kangxi_page(syms):
    """Join our kangxi-tagged symbols to the 214-radical reference spine by NUMBER;
    emit one card per radical (real projection where we have the symbol, else a
    greyed stub), grouped by stroke count, then a non-Kangxi component annex."""
    ref = read_json(DATA / "kangxi.json")["radicals"]
    by_num = {sym["kangxi"]: sym for sym in syms.values() if sym.get("kangxi")}
    refmap = load_referents()

    by_strokes = defaultdict(list)
    real = 0
    for e in ref:
        if e["num"] in by_num:
            c = to_card(by_num[e["num"]])
            c["kx"] = e["num"]
            c["audioBase"] = "../radicals/"   # JP (+ non-bank CN) per-slug clip bucket
            stamp_cn_audio(c)                 # CN single-syllable audio → /audio/cn/ bank
            attach_referents(c, refmap)
            real += 1
        else:
            c = {"stub": True, "glyph": e["glyph"], "kx": e["num"],
                 "pinyin": e["pinyin"], "meaning": e["meaning"], "strokes": e["strokes"]}
        by_strokes[e["strokes"]].append(c)

    groups = []
    for st in sorted(by_strokes):
        # reals (full cards) first, then stub tiles — both in canonical number order
        cards = sorted(by_strokes[st], key=lambda c: (c.get("stub", False), c["kx"]))
        groups.append({"title": f"{st} 画", "sub": f"{st} stroke" + ("s" if st > 1 else ""),
                       "cards": cards})

    annex = [to_card(s) for s in syms.values() if on_components(s)]
    for c in annex:
        c["audioBase"] = "../radicals/"
        stamp_cn_audio(c)
        attach_referents(c, refmap)
    if annex:
        groups.append({"title": "非部首部件", "sub": "non-Kangxi components", "cards": annex})

    path = ROOT / "kangxi/kangxi.json"
    path.parent.mkdir(exist_ok=True)
    text = json.dumps({"groups": groups}, ensure_ascii=False, indent=2) + "\n"
    reparsed = [c for g in json.loads(text)["groups"] for c in g["cards"]]
    assert reparsed == [c for g in groups for c in g["cards"]], "kangxi: emit/parse mismatch"
    path.write_text(text)
    total = sum(len(g["cards"]) for g in groups)
    print(f"{'kangxi.json':24} {total:3} cards ({real}/214 real, {214 - real} stub, "
          f"{len(annex)} annex)")


def main():
    syms = load_symbols()
    pages = [
        ("strokes",    ROOT / "strokes/strokes.json",       on_strokes),
        ("characters", ROOT / "characters/characters.json", on_characters),
    ]
    for name, path, rule in pages:
        cards = [to_card(sym) for sym in syms.values() if rule(sym)]
        for c in cards:
            stamp_cn_audio(c)
        path.parent.mkdir(exist_ok=True)
        text = dump_cardfile(cards)
        # validity + content check: reparse must equal the projected cards
        reparsed = [c for grp in json.loads(text)["groups"] for c in grp["cards"]]
        assert reparsed == cards, f"{name}: emit/parse mismatch"
        path.write_text(text)
        print(f"{name+'.json':24} {len(cards):3} cards")

    build_kangxi_page(syms)

    char_only = [g for g, sym in syms.items()
                 if sym["class"] == "char" and not on_kangxi(sym)]
    print("character-only (not Kangxi radicals):", " ".join(char_only))
    return 0


if __name__ == "__main__":
    sys.exit(main())
