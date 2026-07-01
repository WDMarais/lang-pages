// /graph/ — current-glyph-centered LOCAL graph (Obsidian-style) over the data layer.
// A compact tier index picks a glyph; the ego stage shows its immediate neighbours
// (parts above, appears-in below) with clean local wires, and the meaning (义)
// sits in its own bay alongside; the cards3 three-view sits below for full facts.
// Reuses renderCard()/initHanzi().

const TIERS = [
  { key: 'stroke',    zh: '笔画', en: 'strokes' },
  { key: 'component', zh: '部件', en: 'components' },
  { key: 'char',      zh: '字',   en: 'characters' },
  { key: 'frontier',  zh: '前沿', en: 'frontier' },
];
const TAGMAP = { stroke: 'stroke', component: 'comp', char: 'char' };
const CAP = 10; // max neighbours shown per side before "+N" (two bands hold more)

let byGlyph = {}, bindById = {}, refLabel = {}, denotesOf = {};
const parts = {};    // G → glyphs G is built from   (edge part → G)
const appears = {};  // G → glyphs G appears in       (edge G → whole)
let chipEls = {}, egoEls = {}, selected = null;

Promise.all([
  fetch('../data/nodes.json').then(r => r.json()),
  fetch('../data/edges.json').then(r => r.json()),
  fetch('../data/bindings.json').then(r => r.json()),
]).then(([nd, ed, bd]) => {
  bd.bindings.forEach(b => (bindById[b.id] = b));
  nd.nodes.forEach(n => {
    if (n.kind === 'glyph') byGlyph[n.glyph] = n;
    else if (n.kind === 'referent') refLabel[n.id] = n.label;
  });
  ed.edges.forEach(e => {
    if (e.kind === 'composes') {
      const f = e.from.slice(2), t = e.to.slice(2);
      (appears[f] = appears[f] || []).push(t);
      (parts[t] = parts[t] || []).push(f);
    } else if (e.kind === 'denotes') {
      denotesOf[e.from.slice(2)] = e.to;
    }
  });
  renderIndex(nd.nodes);
  window.addEventListener('resize', () => { if (selected) drawEgoWires(); });
  focus('木');
});

// ── compact tier index (pick a glyph; no wires here) ──
function renderIndex(nodes) {
  const groups = { stroke: [], component: [], char: [], frontier: [] };
  nodes.forEach(n => {
    if (n.kind !== 'glyph') return;
    groups[n.frontier ? 'frontier' : n.tier].push(n);
  });
  const ladder = document.getElementById('ladder');
  ladder.innerHTML = html`${TIERS.map(t => html`
    <div class="band">
      <div class="band-label">
        <span class="bl-zh">${t.zh}</span>
        <span class="bl-en en">${t.en}</span>
        <span class="bl-n">${groups[t.key].length}</span>
      </div>
      <div class="band-chips">
        ${groups[t.key].length
          ? groups[t.key].map(n => html`<button class="chip${n.frontier ? ' frontier' : ''}" data-glyph="${n.glyph}">${n.glyph}</button>`)
          : html`<span class="band-empty">—</span>`}
      </div>
    </div>`)}`;
  chipEls = {};
  ladder.querySelectorAll('.chip').forEach(c => (chipEls[c.dataset.glyph] = c));
  ladder.addEventListener('click', e => {
    const btn = e.target.closest('.chip');
    if (btn) focus(btn.dataset.glyph);
  });
}

function focus(glyph) {
  selected = glyph;
  Object.values(chipEls).forEach(c => c.classList.toggle('sel', c.dataset.glyph === glyph));
  renderEgo(glyph);
  renderReferent(glyph);
  renderDetail(glyph);
}

// referent (义) — the glyph's meaning, in its own bay beside the ego graph
function renderReferent(glyph) {
  const refId = denotesOf[glyph];
  const label = refId && refLabel[refId];
  document.getElementById('referent').innerHTML = html`
    <div class="ref-mark">义</div>
    <div class="ref-body">
      ${label ? html`<div class="ref-label en">${label}</div>` : ''}
      <div class="ref-cap en">meaning · 义</div>
    </div>`;
}

// ── ego stage: deterministic local-graph layout (no physics) ──
// place n nodes on an elliptical arc around the centre, fanned about a0
// (degrees: 0 = east, 90 = south, 270 = north). spanMax stays under 180 so the
// fans keep to the top/bottom and leave the east–west sides clear.
function arc(n, a0, rx = 32, ry = 40, spanMax = 122) {
  if (n <= 0) return [];
  const span = n === 1 ? 0 : Math.min(spanMax, 24 * (n - 1));
  const start = a0 - span / 2, step = n === 1 ? 0 : span / (n - 1);
  return Array.from({ length: n }, (_, i) => {
    const r = (start + i * step) * Math.PI / 180;
    return { x: 50 + rx * Math.cos(r), y: 50 + ry * Math.sin(r) };
  });
}

// fan a group about a0; past ~5 it splits into two concentric bands so a dense
// side (e.g. 一's many appears-in) reads as two rows instead of one crush.
// alternates items outer/inner so neighbours nestle between bands.
function fan(n, a0) {
  if (n <= 5) return arc(n, a0);
  const outerN = Math.ceil(n / 2);
  const outer = arc(outerN, a0, 36, 40, 150);
  const inner = arc(n - outerN, a0, 24, 26, 132);
  const pos = [];
  for (let i = 0, o = 0, k = 0; i < n; i++) pos.push(i % 2 ? inner[k++] : outer[o++]);
  return pos;
}

function facts(glyph) {
  const cn = bindById[`b:${glyph}@cn`], jp = bindById[`b:${glyph}@jp`];
  const py = (cn && cn.readings[0]) || '';
  const kana = (jp && jp.readings[0]) || '';
  const p = jp && jp.program;
  return { py, kana, wk: p && p.source === 'wanikani' ? p.name : '', mean: p && p.kind === 'meaning' };
}

function nb(glyph, x, y, cls) {
  const fr = byGlyph[glyph] && byGlyph[glyph].frontier ? ' frontier' : '';
  return html`<button class="egonode nb ${cls}${fr}" data-key="${glyph}" data-glyph="${glyph}"
            style="left:${x}%;top:${y}%">${glyph}</button>`;
}

function renderEgo(glyph) {
  const P = parts[glyph] || [], A = appears[glyph] || [];
  const Pshow = P.slice(0, CAP), Ashow = A.slice(0, CAP);
  const pp = fan(P.length > CAP ? CAP + 1 : Pshow.length, 270); // parts fan across the top
  const ap = fan(A.length > CAP ? CAP + 1 : Ashow.length, 90);  // appears-in across the bottom
  const f = facts(glyph);
  const center = byGlyph[glyph] && byGlyph[glyph].frontier ? 'egonode center frontier' : 'egonode center';
  const nodes = [html`<div class="${center}" data-key="center">
      <span class="ec-glyph">${glyph}</span>
      ${(f.py || f.kana) ? html`<span class="ec-facts">${[f.py, f.kana].filter(Boolean).join(' · ')}</span>` : ''}
      ${f.wk ? html`<span class="ec-wk ${f.mean ? 'mean' : 'mnem'}">${f.wk}</span>` : ''}
    </div>`];
  Pshow.forEach((g, i) => nodes.push(nb(g, pp[i].x, pp[i].y, 'part')));
  Ashow.forEach((g, i) => nodes.push(nb(g, ap[i].x, ap[i].y, 'whole')));
  if (P.length > CAP) { const m = pp[CAP]; nodes.push(html`<div class="egonode more" style="left:${m.x}%;top:${m.y}%">+${P.length - CAP}</div>`); }
  if (A.length > CAP) { const m = ap[CAP]; nodes.push(html`<div class="egonode more" style="left:${m.x}%;top:${m.y}%">+${A.length - CAP}</div>`); }
  const stage = document.getElementById('ego');
  stage.innerHTML = html`<svg id="egowires"></svg>${nodes}`;
  egoEls = {};
  stage.querySelectorAll('.egonode[data-key]').forEach(e => (egoEls[e.dataset.key] = e));
  stage.querySelectorAll('.egonode.nb').forEach(e =>
    e.addEventListener('click', () => focus(e.dataset.glyph)));
  drawEgoWires();
}

function drawEgoWires() {
  const stage = document.getElementById('ego');
  const svg = document.getElementById('egowires');
  if (!svg) return;
  const sr = stage.getBoundingClientRect();
  svg.setAttribute('width', sr.width);
  svg.setAttribute('height', sr.height);
  svg.setAttribute('viewBox', `0 0 ${sr.width} ${sr.height}`);
  const ctr = key => {
    const el = egoEls[key];
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.left - sr.left + r.width / 2, y: r.top - sr.top + r.height / 2 };
  };
  const c = ctr('center');
  const lines = [];
  Object.entries(egoEls).forEach(([key, el]) => {
    if (key === 'center') return;
    const cls = el.classList.contains('part') ? 'up' : 'down';
    const b = ctr(key);
    if (c && b) lines.push(html`<line x1="${c.x}" y1="${c.y}" x2="${b.x}" y2="${b.y}" class="wire ${cls}"/>`);
  });
  svg.innerHTML = html`${lines}`;
}

// ── full facts: reuse cards3 (or a frontier stub) ──
function renderDetail(glyph) {
  const node = byGlyph[glyph];
  const panel = document.getElementById('detail');
  if (node.frontier) {
    const built = parts[glyph] || [];
    panel.innerHTML = html`
      <div class="frontier-card">
        <div class="fc-glyph">${glyph}</div>
        <div class="fc-meta">
          <div class="fc-tag">前沿 · <span class="en">frontier</span></div>
          ${built.length ? html`<div class="fc-built">含${built.map(g => html` <b>${g}</b>`)}</div>` : ''}
        </div>
      </div>`;
    return;
  }
  panel.innerHTML = renderCard(cardFromNode(node));
  initHanzi();
}

function cardFromNode(node) {
  const cn = bindById[`b:${node.glyph}@cn`], jp = bindById[`b:${node.glyph}@jp`];
  return {
    glyph: node.glyph, slug: node.slug, tag: TAGMAP[node.tier],
    image: node.media.image, hw: node.media.hw, audioBase: `../${node.source}/`,
    cn: view(cn), jp: view(jp), wk: wkFrom(jp), kanji: kanjiFrom(jp),
  };
}
function kanjiFrom(jp) {
  const k = jp.program && jp.program.kanji;
  return k ? { name: k.name, readings: k.readings, on: k.on, level: k.level } : null;
}
function view(b) {
  const v = { name: b.name, reading: b.readings[0] || '', gloss: b.gloss, extra: b.extra };
  if (b.appearsIn) v.appearsIn = { char: b.appearsIn.glyph, reading: b.appearsIn.reading, gloss: b.appearsIn.gloss };
  return v;
}
function wkFrom(jp) {
  const p = jp.program;
  if (!p || p.source !== 'wanikani' || !p.name) return null;
  const wk = { name: p.name, level: p.level, kind: p.kind };
  if (p.altglyph) wk.glyph = p.altglyph;
  if (p.icon) wk.icon = p.icon;
  return wk;
}
