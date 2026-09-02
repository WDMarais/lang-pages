#!/usr/bin/env python3
"""Referent-imagery QC viewer — the curation gate for a bulk image pack.

A contributor batch (e.g. `kangxi_radical_imagery`) ships one folder per referent,
each with a submission JSON (`{slug:{label,images:[…]}}` — the referents.json image
shape) and an `images/` dir of candidates. This tool renders the whole pack as a
single self-contained HTML page so the maintainer can Keep/Reject each candidate,
then export the decisions as `qc-decisions.json` (folded into referents.json by a
separate ingest step). Keep/Reject state persists in the browser's localStorage.

    python3 data/qc-viewer.py                 # default pack in data/.cache/qc/
    python3 data/qc-viewer.py --pack PATH      # a specific pack dir
    python3 data/qc-viewer.py --out viewer.html

Then open the printed viewer.html through the dev server (it sits under the repo,
so image paths resolve relative to it). This is a dev-only curation tool — the pack
lives in the git-ignored data/.cache/, and only the exported decisions + the picked
image bytes ever enter the repo. It is NOT a deployed page.
"""
import argparse
import glob
import html
import json
import os
import re
import zipfile

import paths

DATA = paths.ROOT / "data"
DEFAULT_PACK = DATA / ".cache" / "qc" / "kangxi_radical_imagery"


def our_layer():
    """num → {glyph, kmean, reps, our_ref} from the repo's OWN data, so the viewer can
    show what WE think a radical is against what the pack sourced: kangxi.json gives the
    canonical meaning + representation modality (image / diagram / scene / motion / …),
    and the denotes edge gives the referent the glyph actually points at. The key signal
    is `reps`: a radical with no `image` in it (e.g. 乙 = diagram) is anchored by a
    diagram/scene/sound, so photo candidates are the WRONG modality — flag, don't fold."""
    try:
        kx = {r["num"]: r for r in json.load(open(DATA / "kangxi.json", encoding="utf-8"))["radicals"]}
        ed = json.load(open(DATA / "edges.json", encoding="utf-8"))
        edges = ed if isinstance(ed, list) else ed.get("edges", [])
        nodes = {n["id"]: n for n in json.load(open(DATA / "nodes.json", encoding="utf-8"))["nodes"]}
    except (OSError, ValueError, KeyError):
        return {}
    g2ref = {}
    for e in edges:
        if e.get("kind") == "denotes" and str(e.get("from", "")).startswith("g:"):
            g2ref.setdefault(e["from"][2:], nodes.get(e["to"], {}).get("label", e["to"]))
    return {num: {"glyph": r.get("glyph", ""), "kmean": r.get("meaning", ""),
                  "reps": r.get("representations", []), "our_ref": g2ref.get(r.get("glyph", ""), "")}
            for num, r in kx.items()}


def parse_docx(root):
    """Per-radical semantic-boundary + starting-keyword notes, if the pack ships the
    Gemini docx. Optional — a pack without it just renders no boundary/keyword."""
    matches = glob.glob(os.path.join(root, "*.docx"))
    if not matches:
        return {}
    z = zipfile.ZipFile(matches[0])
    xml = z.read("word/document.xml").decode("utf-8").replace("</w:p>", "\n")
    text = html.unescape(re.sub(r"<[^>]+>", "", xml))
    blocks = {}
    # split on radical headers, capturing number/glyph/label
    parts = re.split(r"Radical (\d+):\s*([^()\n]+?)\s*\(([^)]*)\)", text)
    # parts[0] preamble, then groups of (num, glyph, label, body)
    for i in range(1, len(parts), 4):
        num = int(parts[i])
        glyph = parts[i + 1].split("/")[0].strip()
        label = parts[i + 2].strip()
        body = parts[i + 3]
        boundary = ""
        m = re.search(r"Semantic Meaning & Boundary\s*\n(.+?)\n", body, re.S)
        if m:
            boundary = m.group(1).strip()
        kw = ""
        m = re.search(r"Recommended Starting Keyword:\s*(.+)", body)
        if m:
            kw = m.group(1).strip()
        blocks[num] = {"glyph": glyph, "docx_label": label, "boundary": boundary, "keyword": kw}
    return blocks


def gather(root):
    """One entry per numbered radical folder, images reconciled against disk."""
    docx = parse_docx(root)
    ours = our_layer()
    radicals = []
    dirs = sorted(
        glob.glob(os.path.join(root, "*", "")),
        key=lambda p: int(os.path.basename(p.rstrip("/")).split()[0])
        if os.path.basename(p.rstrip("/"))[0].isdigit() else 999,
    )
    for d in dirs:
        name = os.path.basename(d.rstrip("/"))
        if not name[0].isdigit():
            continue
        num = int(name.split()[0])
        # the submission JSON is `<slug>.json`; a sibling `<slug>-meta.json` (a separate
        # marking webapp's per-image flags/comments) is NOT the image manifest — skip it.
        jf = [p for p in glob.glob(os.path.join(d, "*.json"))
              if not os.path.basename(p).endswith("-meta.json")]
        if not jf:
            continue
        data = json.load(open(jf[0]))
        key = next(iter(data))
        entry = data[key]
        if not isinstance(entry, dict) or "images" not in entry:
            print(f"skip {name}: unexpected JSON shape in {os.path.basename(jf[0])}")
            continue
        reldir = os.path.relpath(d, root).replace(os.sep, "/")
        imgs = []
        for im in entry.get("images", []):
            f = im["file"]
            disk = os.path.join(d, "images", f)
            drift = ""
            missing = False
            if not os.path.exists(disk):
                base = os.path.splitext(f)[0]
                alts = sorted(glob.glob(os.path.join(d, "images", base + ".*")))
                if alts:
                    f = os.path.basename(alts[0])  # reconcile extension drift (json .jpg vs disk .webp/.png)
                    drift = f
                else:
                    missing = True  # declared file absent, no same-basename fallback
            imgs.append({**im, "file": f, "declared": im["file"],
                         "path": f"{reldir}/images/{f}", "drift": drift, "missing": missing})
        note = docx.get(num, {})
        o = ours.get(num, {})
        reps = o.get("reps", [])
        radicals.append({
            "num": num,
            "slug": key,
            "label": entry.get("label", key),
            "glyph": note.get("glyph") or o.get("glyph", ""),
            "boundary": note.get("boundary", ""),
            "keyword": note.get("keyword", ""),
            # our own read (kangxi.json + denotes edge): the referent the glyph points
            # at, the canonical meaning, and the anchor modality. `image_anchor` is the
            # soft signal — false just means our canonical anchor is a diagram/scene/…,
            # so a proxy photo is a supplement, NOT a reason to reject on sight.
            "ourRef": o.get("our_ref", ""),
            "kmean": o.get("kmean", ""),
            "reps": reps,
            "imageAnchor": ("image" in reps) if reps else True,
            "images": imgs,
        })
    return radicals


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Referent Imagery — QC</title>
<style>
:root{--bg:#0f1115;--panel:#171a21;--line:#262b36;--fg:#e6e9ef;--mut:#8b93a3;--good:#2ea043;--bad:#e5534b;--warn:#d29922;--acc:#4c8dff}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg);display:flex;height:100vh;overflow:hidden}
#nav{width:230px;flex:none;border-right:1px solid var(--line);overflow-y:auto;background:var(--panel)}
#nav h1{font-size:13px;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);padding:14px 16px 6px;margin:0}
.navitem{display:flex;align-items:center;gap:10px;padding:9px 16px;cursor:pointer;border-left:3px solid transparent}
.navitem:hover{background:#1e222b}
.navitem.sel{background:#1e242f;border-left-color:var(--acc)}
.navitem .g{font-size:22px;line-height:1;width:26px;text-align:center}
.navitem .meta{display:flex;flex-direction:column;min-width:0}
.navitem .lb{font-weight:600}
.navitem .sub{font-size:12px;color:var(--mut)}
.navitem .cnt{margin-left:auto;font-size:11px;color:var(--mut)}
.dot{width:8px;height:8px;border-radius:50%;margin-left:auto;flex:none}
#main{flex:1;overflow-y:auto;padding:24px 30px 80px}
.head{display:flex;align-items:baseline;gap:16px;margin-bottom:4px}
.head .g{font-size:56px;line-height:1}
.head .t{font-size:26px;font-weight:700}
.head .n{color:var(--mut)}
.kw{display:inline-block;background:#1e2633;border:1px solid var(--line);color:var(--acc);border-radius:20px;padding:2px 12px;font-size:13px;margin-bottom:14px}
.ours{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.pill{background:#181c24;border:1px solid var(--line);border-radius:6px;padding:3px 10px;font-size:12px;color:var(--mut)}
.pill b{color:var(--fg);font-weight:600}
.pill.proxy{border-color:var(--warn);color:var(--warn)}.pill.proxy b{color:var(--warn)}
.proxynote{background:#211d12;border:1px solid var(--warn);border-left:3px solid var(--warn);border-radius:8px;padding:10px 14px;margin-bottom:16px;color:#e7d5a8;font-size:13px;max-width:80ch}
.proxynote b{color:#fff}
.navitem .px{color:var(--warn);font-size:11px;margin-left:6px}
.boundary{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--acc);border-radius:8px;padding:12px 16px;margin-bottom:22px;color:#c7cdd8;max-width:80ch}
.boundary b{color:var(--fg)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;display:flex;flex-direction:column}
.card.rej{opacity:.5;border-color:var(--bad)}
.imgwrap{position:relative;aspect-ratio:4/3;background:#000;cursor:zoom-in}
.imgwrap img{width:100%;height:100%;object-fit:contain}
.badge{position:absolute;top:8px;left:8px;font-size:11px;font-weight:700;padding:3px 8px;border-radius:5px;background:rgba(0,0,0,.7)}
.badge.ok{color:var(--good)}.badge.no{color:var(--bad)}
.miss{display:flex;align-items:center;justify-content:center;height:100%;color:var(--bad);font-weight:700;letter-spacing:.06em}
.imgwrap.broken{background:#3a1414}
.drift{color:var(--warn);font-size:12px}
.body{padding:12px 14px;font-size:13px;display:flex;flex-direction:column;gap:6px}
.title{font-weight:600;font-size:14px}
.row{color:var(--mut)}
.row b{color:var(--fg);font-weight:500}
.lic.ok{color:var(--good)}.lic.no{color:var(--bad);font-weight:700}
.notes{color:#aeb6c2;font-style:italic}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.acts{display:flex;gap:8px;margin-top:6px}
.acts button{flex:1;background:#1e242f;border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:6px;cursor:pointer;font-size:12px}
.acts button.on-keep{background:var(--good);border-color:var(--good);color:#04140a}
.acts button.on-rej{background:var(--bad);border-color:var(--bad);color:#1a0505}
#bar{position:fixed;bottom:0;left:230px;right:0;background:var(--panel);border-top:1px solid var(--line);padding:8px 16px;display:flex;gap:14px;align-items:center;font-size:13px}
#bar b{color:var(--good)}#bar .r{color:var(--bad)}
#bar button{margin-left:auto;background:var(--acc);border:0;color:#fff;border-radius:6px;padding:7px 14px;cursor:pointer}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;z-index:50;cursor:zoom-out}
#lb img{max-width:94vw;max-height:94vh}
</style></head><body>
<div id="nav"><h1>Radicals (__NR__)</h1><div id="navlist"></div></div>
<div id="main"></div>
<div id="bar"><span>Kept <b id="nk">0</b> · Rejected <span class="r" id="nrj">0</span> · Undecided <span id="nu">0</span></span>
<button onclick="exportQC()">Export decisions</button></div>
<div id="lb" onclick="this.style.display='none'"><img></div>
<script>
const DATA=__DATA__;
// Free-to-redistribute: public-domain (any phrasing — "Public Domain Mark",
// "Public Domain Dedication (CC0)", "Public domain"), CC0, and CC BY / CC BY-SA
// at any version. Space-guarded so CC BY-NC / CC BY-ND stay rejected.
function licOk(l){
  const u=(l||'').trim().toUpperCase();
  if(u.startsWith('PUBLIC DOMAIN')||u==='PD'||u.startsWith('PD ')||u.startsWith('CC0')) return true;
  return ['CC BY','CC BY-SA'].some(o=>u===o||u.startsWith(o+' '));
}
const dec=JSON.parse(localStorage.getItem('qc')||'{}');
function save(){localStorage.setItem('qc',JSON.stringify(dec));counts();}
let sel=0;
function counts(){
  let k=0,r=0,u=0;
  DATA.forEach(rad=>rad.images.forEach(im=>{const s=dec[im.path];if(s==='keep')k++;else if(s==='rej')r++;else u++;}));
  nk.textContent=k;nrj.textContent=r;nu.textContent=u;
  document.querySelectorAll('.navitem').forEach((el,i)=>{
    const rad=DATA[i];const bad=rad.images.some(im=>!licOk(im.license)||im.missing);
    const done=rad.images.every(im=>dec[im.path]);
    const d=el.querySelector('.dot');
    d.style.background=bad?'var(--bad)':done?'var(--good)':'var(--line)';
  });
}
function nav(){
  navlist.innerHTML='';
  DATA.forEach((rad,i)=>{
    const el=document.createElement('div');el.className='navitem'+(i===sel?' sel':'');
    const px=rad.imageAnchor===false?`<span class="px" title="canonical anchor is ${(rad.reps||[]).join('/')||'non-image'} — proxy image">◇</span>`:'';
    el.innerHTML=`<div class="g">${rad.glyph||'?'}</div><div class="meta"><span class="lb">${rad.label}${px}</span><span class="sub">№${rad.num} · ${rad.slug}</span></div><div class="dot"></div>`;
    el.onclick=()=>{sel=i;render();};navlist.appendChild(el);
  });
}
function card(im){
  const ok=licOk(im.license);const state=dec[im.path]||'';
  const c=document.createElement('div');c.className='card'+(state==='rej'?' rej':'');
  c.innerHTML=`<div class="imgwrap"><span class="badge ${ok?'ok':'no'}">${ok?'✓ '+im.license:'✗ '+(im.license||'no license')}</span>${im.missing?'<div class="miss">FILE MISSING</div>':`<img loading="lazy" src="${im.path}" onerror="this.closest('.imgwrap').classList.add('broken');this.alt='failed: '+this.src">`}</div>
  <div class="body">
    <div class="title">${im.title||im.file}</div>
    <div class="row"><b>Credit:</b> ${im.credit||'—'}</div>
    <div class="row"><b>License:</b> <span class="lic ${ok?'ok':'no'}">${im.license||'—'}</span></div>
    ${im.missing?`<div class="row"><b>File:</b> <span class="lic no">MISSING — ${im.declared}</span></div>`:im.drift?`<div class="row"><b>File:</b> ${im.file} <span class="drift">(json said ${im.declared})</span></div>`:`<div class="row"><b>File:</b> ${im.file}</div>`}
    ${im.source?`<div class="row"><b>Source:</b> <a href="${im.source}" target="_blank">file page ↗</a></div>`:'<div class="row"><b>Source:</b> <span class="lic no">missing</span></div>'}
    ${im.notes?`<div class="notes">${im.notes}</div>`:''}
    <div class="acts">
      <button class="${state==='keep'?'on-keep':''}" onclick="setD('${im.path}','keep')">Keep</button>
      <button class="${state==='rej'?'on-rej':''}" onclick="setD('${im.path}','rej')">Reject</button>
    </div>
  </div>`;
  c.querySelector('.imgwrap').onclick=e=>{if(e.target.tagName==='IMG'){lb.querySelector('img').src=im.path;lb.style.display='flex';}};
  return c;
}
function setD(p,v){if(dec[p]===v)delete dec[p];else dec[p]=v;save();render();}
function render(){
  const rad=DATA[sel];
  const reps=(rad.reps&&rad.reps.length)?rad.reps.join(' · '):'—';
  const proxy=rad.imageAnchor===false;
  main.innerHTML=`<div class="head"><span class="g">${rad.glyph||'?'}</span><span class="t">${rad.label}</span><span class="n">Kangxi №${rad.num} · slug <code>${rad.slug}</code></span></div>
  <div class="ours">
    <span class="pill">our referent <b>${rad.ourRef||'—'}</b></span>
    <span class="pill">kangxi <b>${rad.kmean||'—'}</b></span>
    <span class="pill${proxy?' proxy':''}">anchor <b>${reps}</b></span>
  </div>
  ${proxy?`<div class="proxynote">Canonical anchor here isn't a photo — this radical is abstract/structural. A clean <b>visual proxy</b> (its shape, etymology, or a typical instance) is still worth keeping; reject mainly when the image reads as a <i>different meaning</i> than «${rad.ourRef||rad.kmean||rad.label}».</div>`:''}
  ${rad.keyword?`<div class="kw">recommended keyword: ${rad.keyword}</div>`:''}
  ${rad.boundary?`<div class="boundary"><b>Intended boundary.</b> ${rad.boundary}</div>`:''}
  <div class="grid" id="grid"></div>`;
  const g=main.querySelector('#grid');rad.images.forEach(im=>g.appendChild(card(im)));
  document.querySelectorAll('.navitem').forEach((e,i)=>e.classList.toggle('sel',i===sel));
  counts();
}
function exportQC(){
  const out={generated:new Date().toISOString(),decisions:[]};
  DATA.forEach(rad=>rad.images.forEach(im=>out.decisions.push({num:rad.num,slug:rad.slug,glyph:rad.glyph,ourRef:rad.ourRef||'',kmean:rad.kmean||'',reps:rad.reps||[],imageAnchor:rad.imageAnchor!==false,keyword:rad.keyword||'',file:im.file,path:im.path,declared:im.declared,drift:im.drift||'',missing:!!im.missing,license:im.license,licenseOk:licOk(im.license),decision:dec[im.path]||'undecided',title:im.title||'',credit:im.credit,source:im.source,notes:im.notes||''})));
  const b=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='qc-decisions.json';a.click();
}
nav();render();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Build a self-contained referent-imagery QC viewer.")
    ap.add_argument("--pack", default=str(DEFAULT_PACK), help="pack dir (folder-per-radical)")
    ap.add_argument("--out", default="", help="output HTML path (default <pack>/viewer.html)")
    args = ap.parse_args()

    root = os.path.abspath(args.pack)
    if not os.path.isdir(root):
        raise SystemExit(f"pack dir not found: {root}")
    radicals = gather(root)
    if not radicals:
        raise SystemExit(f"no numbered radical folders with JSON found under {root}")

    payload = json.dumps(radicals, ensure_ascii=False)
    total_imgs = sum(len(r["images"]) for r in radicals)
    page = HTML.replace("__DATA__", payload).replace("__NR__", str(len(radicals)))
    out = os.path.abspath(args.out) if args.out else os.path.join(root, "viewer.html")
    open(out, "w", encoding="utf-8").write(page)

    print(f"wrote {out}")
    print(f"{len(radicals)} radicals, {total_imgs} images")
    missing = [f"{r['num']} {r['slug']}" for r in radicals if not r["glyph"]]
    if missing:
        print(f"note: {len(missing)} radicals with no docx glyph/notes: {', '.join(missing[:12])}"
              + (" …" if len(missing) > 12 else ""))


if __name__ == "__main__":
    main()
