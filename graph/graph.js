// /graph/ — current-glyph-centered LOCAL graph (Obsidian-style) over the data layer.
// A compact tier index picks a glyph; the ego stage shows its immediate neighbours
// (parts above, appears-in below, referent aside) with clean local wires; the
// cards3 three-view sits below for full facts. Reuses renderCard()/initHanzi().

const TIERS = [
  { key: 'stroke',    zh: '笔画', en: 'strokes' },
  { key: 'component', zh: '部件', en: 'components' },
  { key: 'char',      zh: '字',   en: 'characters' },
  { key: 'frontier',  zh: '前沿', en: 'frontier' },
];
const TAGMAP = { stroke: 'stroke', component: 'comp', char: 'char' };
const CAP = 6; // max neighbours shown per side before "+N"

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
  ladder.innerHTML = TIERS.map(t => `
    <div class="band">
      <div class="band-label">
        <span class="bl-zh">${t.zh}</span>
        <span class="bl-en en">${t.en}</span>
        <span class="bl-n">${groups[t.key].length}</span>
      </div>
      <div class="band-chips">
        ${groups[t.key].map(n =>
          `<button class="chip${n.frontier ? ' frontier' : ''}" data-glyph="${n.glyph}">${n.glyph}</button>`
        ).join('') || '<span class="band-empty">—</span>'}
      </div>
    </div>`).join('');
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
  renderDetail(glyph);
}

// ── ego stage: deterministic local-graph layout (no physics) ──
function spread(n, lo = 16, hi = 84) {
  if (n <= 0) return [];
  if (n === 1) return [(lo + hi) / 2];
  const step = (hi - lo) / (n - 1);
  return Array.from({ length: n }, (_, i) => lo + i * step);
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
  return `<button class="egonode nb ${cls}${fr}" data-key="${glyph}" data-glyph="${glyph}"
            style="left:${x}%;top:${y}%">${glyph}</button>`;
}

function renderEgo(glyph) {
  const P = parts[glyph] || [], A = appears[glyph] || [];
  const Ps = P.slice(0, CAP), As = A.slice(0, CAP);
  const px = spread(Ps.length), ax = spread(As.length);
  const f = facts(glyph);
  const center = byGlyph[glyph] && byGlyph[glyph].frontier ? 'egonode center frontier' : 'egonode center';
  let html = `<div class="${center}" data-key="center">
      <span class="ec-glyph">${glyph}</span>
      ${(f.py || f.kana) ? `<span class="ec-facts">${[f.py, f.kana].filter(Boolean).join(' · ')}</span>` : ''}
      ${f.wk ? `<span class="ec-wk ${f.mean ? 'mean' : 'mnem'}">${f.wk}</span>` : ''}
    </div>`;
  Ps.forEach((g, i) => (html += nb(g, px[i], 15, 'part')));
  As.forEach((g, i) => (html += nb(g, ax[i], 85, 'whole')));
  if (P.length > CAP) html += `<div class="egonode more" style="left:92%;top:15%">+${P.length - CAP}</div>`;
  if (A.length > CAP) html += `<div class="egonode more" style="left:92%;top:85%">+${A.length - CAP}</div>`;
  const refId = denotesOf[glyph];
  if (refId && refLabel[refId]) {
    html += `<div class="egonode ref" data-key="ref" style="left:89%;top:50%">
        <span class="er-zh">义</span><span class="er-txt en">${refLabel[refId]}</span></div>`;
  }
  const stage = document.getElementById('ego');
  stage.innerHTML = '<svg id="egowires"></svg>' + html;
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
  let lines = '';
  Object.entries(egoEls).forEach(([key, el]) => {
    if (key === 'center') return;
    const cls = el.classList.contains('part') ? 'up'
      : el.classList.contains('whole') ? 'down' : 'ref';
    const b = ctr(key);
    if (c && b) lines += `<line x1="${c.x}" y1="${c.y}" x2="${b.x}" y2="${b.y}" class="wire ${cls}"/>`;
  });
  svg.innerHTML = lines;
}

// ── full facts: reuse cards3 (or a frontier stub) ──
function renderDetail(glyph) {
  const node = byGlyph[glyph];
  const panel = document.getElementById('detail');
  if (node.frontier) {
    const built = parts[glyph] || [];
    panel.innerHTML = `
      <div class="frontier-card">
        <div class="fc-glyph">${glyph}</div>
        <div class="fc-meta">
          <div class="fc-tag">前沿 · <span class="en">frontier</span></div>
          ${built.length ? `<div class="fc-built">含 ${built.map(g => `<b>${g}</b>`).join(' ')}</div>` : ''}
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
  if (b.example) v.ex = { char: b.example.glyph, reading: b.example.reading, gloss: b.example.gloss };
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
