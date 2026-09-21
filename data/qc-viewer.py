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


CC_URL = re.compile(r"creativecommons\.org/(?:licenses|publicdomain)/([a-z0-9-]+)(?:/([0-9.]+))?", re.I)
# Commons states a multi-licensed file's terms as a category, not a CC link:
# `…/wiki/Category:CC-BY-SA-3.0,2.5,2.0,1.0` means CC BY-SA at any of those versions.
COMMONS_LIC = re.compile(r"commons\.wikimedia\.org/wiki/Category:CC-(BY(?:-SA)?)-([0-9.,]+)", re.I)


def derive_license(im):
    """A readable licence for an entry whose `license` is the linker's unfilled
    '(other — enter URL)' placeholder. The contributor still recorded the real
    licence in `license_url`, and a CC URL names it unambiguously — so read it off
    rather than showing the maintainer a placeholder. Returns (label, derived).

    It does NOT merely relabel refusals: the derived name goes through the same
    licOk() check as any other, so a placeholder hiding CC BY-ND stays refused and
    one hiding CC0 now passes. Both are the right call — the gate is being applied
    to the licence the contributor actually recorded, instead of to a form default
    that says nothing. Anything without a CC URL to read is left exactly as it came
    in, and so stays refused."""
    lic = (im.get("license") or "").strip()
    if not lic.startswith("(other"):
        return lic, False
    url = im.get("license_url") or ""
    cm = COMMONS_LIC.search(url)
    if cm:
        best = max(cm.group(2).split(","), key=lambda v: [int(x) for x in v.split(".") if x.isdigit()])
        return f"CC {cm.group(1).upper()} {best}", True
    m = CC_URL.search(url)
    if not m:
        return lic, False
    code, ver = m.group(1).lower(), (m.group(2) or "")
    if code == "zero":
        return ("CC0 " + ver).strip(), True
    if code in ("mark", "certification"):
        return "Public Domain Mark " + ver if ver else "Public Domain Mark", True
    return ("CC " + code.upper() + " " + ver).strip(), True


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
        # A folder holds ONE submission JSON per contributor (`<slug>.json`,
        # `<slug>-lmar.json`, …), so two batches for the same radical render side by
        # side, each image carrying its provenance. A sibling `<slug>-meta.json` (a
        # separate marking webapp's per-image flags) is NOT a manifest — skip it.
        jfs = sorted(p for p in glob.glob(os.path.join(d, "*.json"))
                     if not os.path.basename(p).endswith("-meta.json"))
        if not jfs:
            continue
        reldir = os.path.relpath(d, root).replace(os.sep, "/")
        imgs, slug, label, contributors = [], "", "", []
        for jf in jfs:
            data = json.load(open(jf))
            key = next((k for k in data if not k.startswith("_")), None)
            entry = data.get(key) if key else None
            if not isinstance(entry, dict) or "images" not in entry:
                print(f"skip {name}/{os.path.basename(jf)}: unexpected JSON shape")
                continue
            who = data.get("_contributor", "") or "unattributed"
            if who not in contributors:
                contributors.append(who)
            slug = slug or key
            label = label or entry.get("label", key)
            for im in entry.get("images", []):
                f = im["file"]
                disk = os.path.join(d, "images", f)
                drift = ""
                missing = False
                if not os.path.exists(disk):
                    base = os.path.splitext(f)[0]
                    alts = sorted(glob.glob(os.path.join(d, "images", base + ".*")))
                    if alts:
                        f = os.path.basename(alts[0])  # extension drift (json .jpg vs disk .webp)
                        drift = f
                    else:
                        missing = True  # declared file absent, no same-basename fallback
                lic, derived = derive_license(im)
                imgs.append({**im, "file": f, "declared": im["file"], "by": who,
                             "license": lic, "licenseDerived": derived,
                             "path": f"{reldir}/images/{f}", "drift": drift, "missing": missing})
        if not slug:
            continue
        note = docx.get(num, {})
        o = ours.get(num, {})
        reps = o.get("reps", [])
        radicals.append({
            "num": num,
            "slug": slug,
            "label": label,
            "contributors": contributors,
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
#bar .storage{color:var(--mut);font-size:12px;display:flex;align-items:center;gap:7px}
#bar .storage .sbar{width:84px;height:6px;border-radius:4px;background:#1e242f;border:1px solid var(--line);overflow:hidden}
#bar .storage .sfill{height:100%;width:0;background:var(--good);transition:width .25s,background .25s}
#bar .storage .sfill.warn{background:var(--warn)}
#bar .storage .sfill.danger{background:var(--bad)}
#bar .storage.alert{color:var(--warn)}
#bar .storage.alert.danger{color:var(--bad);font-weight:700}
#filters{padding:6px 12px 10px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel);z-index:2}
#filters input,#filters select{width:100%;background:#0f1218;border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:6px 9px;font:inherit;font-size:13px;margin-top:6px}
#filters input::placeholder{color:#5f6775}
.by{display:inline-block;border:1px solid var(--line);border-radius:20px;padding:1px 8px;font-size:11px;color:var(--mut);background:#161a21}
.card .by{margin-left:auto}
.title-row{display:flex;align-items:center;gap:8px}
.navitem .who{font-size:10px;color:#5f6775;letter-spacing:.03em}
.hint{color:var(--mut);font-size:12px;margin-left:4px}
</style></head><body>
<div id="nav">
  <h1>__PACK__ · <span id="navcount">__NR__</span></h1>
  <div id="filters">
    <input id="q" type="search" placeholder="filter — number, slug or glyph" autocomplete="off">
    <select id="who"></select>
  </div>
  <div id="navlist"></div>
</div>
<div id="main"></div>
<div id="bar"><span>Kept <b id="nk">0</b> · Rejected <span class="r" id="nrj">0</span> · Undecided <span id="nu">0</span> <span class="hint" id="scope"></span></span>
<span class="hint">j/k move · / filter</span>
<span id="storage" class="storage" title="Browser local-storage used by your Keep/Reject decisions."><span id="sLabel">storage: —</span><span class="sbar"><span class="sfill" id="sFill"></span></span></span>
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
const PACK=__PACKJSON__;
// Decisions are namespaced per pack, so a second pack can't inherit the first's
// Keep/Reject calls. The original pack wrote to a bare 'qc' key — adopt it once,
// without deleting it, so an older export stays recoverable.
const LS_KEY='qc:'+PACK;
function loadDecisions(){
  try{
    const own=localStorage.getItem(LS_KEY);
    if(own!==null) return JSON.parse(own);
    const legacy=localStorage.getItem('qc');
    if(legacy!==null){localStorage.setItem(LS_KEY,legacy);return JSON.parse(legacy);}
  }catch(e){console.warn('could not read saved decisions',e);}
  return {};
}
const dec=loadDecisions();
function save(){try{localStorage.setItem(LS_KEY,JSON.stringify(dec));}catch(e){alert('Could not save — storage may be full. Export your decisions now.');}counts();}
const LS_QUOTA=5*1024*1024;   // ~5 MB per-origin cap (common browser default)
function storageBytes(){let n=0;try{for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);n+=k.length+(localStorage.getItem(k)||'').length;}}catch(e){}return n*2;}
function fmtMB(b){return (b/1048576).toFixed(b<104857?2:1)+' MB';}
function updateStorage(){
  const el=document.getElementById('storage');if(!el)return;
  const used=storageBytes(),pct=Math.min(100,Math.round(used/LS_QUOTA*100));
  const fill=document.getElementById('sFill');
  fill.style.width=pct+'%';fill.className='sfill'+(pct>=90?' danger':pct>=70?' warn':'');
  document.getElementById('sLabel').textContent='storage: '+fmtMB(used)+' / ~'+fmtMB(LS_QUOTA)+' ('+pct+'%)';
  el.className='storage'+(pct>=90?' alert danger':pct>=70?' alert':'');
  el.title=pct>=70?'Near this browser’s storage limit — click Export decisions now to be safe.':'Browser local-storage used by your Keep/Reject decisions.';
}
// ── state ──────────────────────────────────────────────────────────────────
// `sel` (which radical) and `who` (contributor filter) live in the URL, so a
// radical is linkable and the back button walks the review. The text filter is
// view-only state: putting keystrokes in the URL would spam history for nothing.
let sel=0,who='',q='';
const ALL_WHO=[...new Set(DATA.flatMap(r=>r.contributors||[]))].sort();
function imagesOf(rad){return who?rad.images.filter(im=>im.by===who):rad.images;}
function matches(rad){
  if(who&&!(rad.contributors||[]).includes(who))return false;
  if(!q)return true;
  const t=q.toLowerCase();
  return String(rad.num)===t||String(rad.num).startsWith(t)||
    (rad.slug||'').toLowerCase().includes(t)||(rad.label||'').toLowerCase().includes(t)||
    (rad.glyph||'').includes(q);
}
function buildHash(){
  const p=new URLSearchParams();
  p.set('n',DATA[sel].num);
  if(who)p.set('c',who);
  return '#'+p.toString();
}
function applyHash(){
  const p=new URLSearchParams(location.hash.slice(1));
  const n=parseInt(p.get('n'),10);
  const c=p.get('c')||'';
  who=ALL_WHO.includes(c)?c:'';
  const i=DATA.findIndex(r=>r.num===n);
  sel=i>=0?i:0;
}
function go(){                      // one way to navigate: set the hash, let it render
  const h=buildHash();
  if(location.hash===h){nav();render();}else{location.hash=h;}
}
// ── rendering ──────────────────────────────────────────────────────────────
function counts(){
  let k=0,r=0,u=0;
  DATA.forEach(rad=>imagesOf(rad).forEach(im=>{const s=dec[im.path];if(s==='keep')k++;else if(s==='rej')r++;else u++;}));
  nk.textContent=k;nrj.textContent=r;nu.textContent=u;
  document.getElementById('scope').textContent=who?`(${who} only)`:'';
  document.querySelectorAll('.navitem').forEach(el=>{
    const rad=DATA[+el.dataset.i];const ims=imagesOf(rad);
    const bad=ims.some(im=>!licOk(im.license)||im.missing);
    const done=ims.length&&ims.every(im=>dec[im.path]);
    el.querySelector('.dot').style.background=bad?'var(--bad)':done?'var(--good)':'var(--line)';
  });
  updateStorage();
}
function nav(){
  navlist.innerHTML='';
  let shown=0;
  DATA.forEach((rad,i)=>{
    if(!matches(rad))return;
    shown++;
    const el=document.createElement('div');el.className='navitem'+(i===sel?' sel':'');
    el.dataset.i=i;
    const px=rad.imageAnchor===false?`<span class="px" title="canonical anchor is ${(rad.reps||[]).join('/')||'non-image'} — proxy image">◇</span>`:'';
    const cs=(rad.contributors||[]);
    const whoTag=cs.length>1?`<span class="who">${cs.join(' + ')}</span>`:'';
    el.innerHTML=`<div class="g">${rad.glyph||'?'}</div><div class="meta"><span class="lb">${rad.label}${px}</span><span class="sub">№${rad.num} · ${rad.slug} ${whoTag}</span></div><div class="cnt">${imagesOf(rad).length}</div><div class="dot"></div>`;
    el.onclick=()=>{sel=i;go();};navlist.appendChild(el);
  });
  document.getElementById('navcount').textContent=shown===DATA.length?DATA.length:`${shown}/${DATA.length}`;
}
function step(d){                   // j/k and arrows walk the FILTERED list
  const vis=DATA.map((r,i)=>i).filter(i=>matches(DATA[i]));
  if(!vis.length)return;
  const at=vis.indexOf(sel);
  sel=vis[Math.max(0,Math.min(vis.length-1,(at<0?0:at)+d))];
  go();
  const el=navlist.querySelector(`.navitem[data-i="${sel}"]`);
  if(el)el.scrollIntoView({block:'nearest'});
}
function card(im){
  const ok=licOk(im.license);const state=dec[im.path]||'';
  const c=document.createElement('div');c.className='card'+(state==='rej'?' rej':'');
  c.innerHTML=`<div class="imgwrap"><span class="badge ${ok?'ok':'no'}">${ok?'✓ '+im.license:'✗ '+(im.license||'no license')}</span>${im.missing?'<div class="miss">FILE MISSING</div>':`<img loading="lazy" src="${im.path}" onerror="this.closest('.imgwrap').classList.add('broken');this.alt='failed: '+this.src">`}</div>
  <div class="body">
    <div class="title-row"><span class="title">${im.title||im.file}</span><span class="by" title="contributed by">${im.by||'—'}</span></div>
    <div class="row"><b>Credit:</b> ${im.credit||'—'}</div>
    <div class="row"><b>License:</b> <span class="lic ${ok?'ok':'no'}">${im.license||'—'}</span>${im.licenseDerived?' <span class="hint" title="contributor left the license field unfilled; read from license_url">(from URL)</span>':''}</div>
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
    <span class="pill">from <b>${(rad.contributors||[]).join(' + ')||'—'}</b></span>
    <span class="pill${proxy?' proxy':''}">anchor <b>${reps}</b></span>
  </div>
  ${proxy?`<div class="proxynote">Canonical anchor here isn't a photo — this radical is abstract/structural. A clean <b>visual proxy</b> (its shape, etymology, or a typical instance) is still worth keeping; reject mainly when the image reads as a <i>different meaning</i> than «${rad.ourRef||rad.kmean||rad.label}».</div>`:''}
  ${rad.keyword?`<div class="kw">recommended keyword: ${rad.keyword}</div>`:''}
  ${rad.boundary?`<div class="boundary"><b>Intended boundary.</b> ${rad.boundary}</div>`:''}
  <div class="grid" id="grid"></div>`;
  const g=main.querySelector('#grid');
  const ims=imagesOf(rad);
  if(!ims.length)g.innerHTML='<div class="row">No images from this contributor for this radical.</div>';
  ims.forEach(im=>g.appendChild(card(im)));
  document.querySelectorAll('.navitem').forEach(e=>e.classList.toggle('sel',+e.dataset.i===sel));
  counts();
}
function exportQC(){
  // Always the WHOLE pack, never the current filter — a partial export silently
  // reverts to 'undecided' downstream, which reads as a reject.
  const out={generated:new Date().toISOString(),pack:PACK,decisions:[]};
  DATA.forEach(rad=>rad.images.forEach(im=>out.decisions.push({num:rad.num,slug:rad.slug,glyph:rad.glyph,by:im.by||'',ourRef:rad.ourRef||'',kmean:rad.kmean||'',reps:rad.reps||[],imageAnchor:rad.imageAnchor!==false,keyword:rad.keyword||'',file:im.file,path:im.path,declared:im.declared,drift:im.drift||'',missing:!!im.missing,license:im.license,licenseOk:licOk(im.license),decision:dec[im.path]||'undecided',title:im.title||'',credit:im.credit,source:im.source,notes:im.notes||''})));
  const b=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='qc-decisions.json';a.click();
}
// ── controls + boot ────────────────────────────────────────────────────────
const whoSel=document.getElementById('who');
whoSel.innerHTML=`<option value="">all contributors (${ALL_WHO.length})</option>`+
  ALL_WHO.map(w=>`<option value="${w}">${w}</option>`).join('');
whoSel.onchange=()=>{
  who=whoSel.value;
  // the radical in view may have nothing from this contributor — land on one that does,
  // rather than leaving the nav and the panel disagreeing about what's selected
  if(!matches(DATA[sel])){const i=DATA.findIndex(matches);if(i>=0)sel=i;}
  go();
};
const qBox=document.getElementById('q');
qBox.oninput=()=>{q=qBox.value.trim();nav();};
document.addEventListener('keydown',e=>{
  if(e.target.matches('input,select,textarea'))return;
  if(e.key==='j'||e.key==='ArrowDown'){e.preventDefault();step(1);}
  else if(e.key==='k'||e.key==='ArrowUp'){e.preventDefault();step(-1);}
  else if(e.key==='/'){e.preventDefault();qBox.focus();}
});
function route(){applyHash();whoSel.value=who;nav();render();}
window.addEventListener('hashchange',route);
if(!location.hash)history.replaceState(null,'',buildHash());
route();
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
    pack_name = os.path.basename(root)
    page = (HTML.replace("__DATA__", payload)
                .replace("__PACKJSON__", json.dumps(pack_name))
                .replace("__PACK__", html.escape(pack_name))
                .replace("__NR__", str(len(radicals))))
    out = os.path.abspath(args.out) if args.out else os.path.join(root, "viewer.html")
    open(out, "w", encoding="utf-8").write(page)

    print(f"wrote {out}")
    by = {}
    for r in radicals:
        for im in r["images"]:
            by[im.get("by", "?")] = by.get(im.get("by", "?"), 0) + 1
    print(f"{len(radicals)} radicals, {total_imgs} images  ("
          + ", ".join(f"{w} {n}" for w, n in sorted(by.items())) + ")")
    missing = [f"{r['num']} {r['slug']}" for r in radicals if not r["glyph"]]
    if missing:
        print(f"note: {len(missing)} radicals with no docx glyph/notes: {', '.join(missing[:12])}"
              + (" …" if len(missing) > 12 else ""))


if __name__ == "__main__":
    main()
