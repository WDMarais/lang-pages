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

// appears-in (children) radial rings — the layer *count* is a magnitude gauge:
// sparse glyph → 1 ring; hub → 3. Fill inner→outer; cap at 3 then spill to a list.
const RING_CAPS = [6, 8, 10];                      // per-ring max & distribution weight (≈circumference), inner→outer
const RING_RXY  = [[26, 25], [37, 37], [45, 48]]; // [rx, ry] % of stage, inner→outer
const RING_SPAN = 240;                            // sweep centred south (leaves top for parts)
const RING_OFF  = 11;                             // per-ring angular stagger (deg) — break spokes
const RING_AT   = [6, 14];                         // ring-count gauge: ≤6 → 1 ring, ≤14 → 2, else 3
const RING_TOTAL = RING_CAPS.reduce((a, b) => a + b, 0);

// golden-angle (Vogel) spiral params — uniform-density alternative to rings.
const GOLDEN       = Math.PI * (3 - Math.sqrt(5)); // ~137.508°
const SPIRAL_SCALE = 8;                            // % of stage between successive shells (≈ tile pitch)
const SPIRAL_R0    = 13;                           // % inner clearance so seeds miss the centre card
const SPIRAL_TILT  = Math.PI / 2;                  // start index 0 pointing south

let byGlyph = {}, bindById = {}, refLabel = {}, denotesOf = {};
const parts = {};    // G → glyphs G is built from   (edge part → G)
const appears = {};  // G → glyphs G appears in       (edge G → whole)
let chipEls = {}, egoEls = {}, wireEls = {}, selected = null;

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
// centre glyph in a card (with its parts as chips); appears-in placed around it
// as rings or a golden spiral. degrees: 0 = east, 90 = south, 270 = north.

// choose how many rings to use (the gauge) and how many tiles go in each. the
// ring COUNT still encodes magnitude (RING_AT thresholds), but within the active
// rings the load is split proportional to circumference (RING_CAPS as weights),
// via largest-remainder, so every ring lands at ~equal fill — no crowded-inner /
// starved-outer. returns {counts:[…], shown, overflow}.
function ringPlan(n) {
  const shown = Math.min(n, RING_TOTAL);
  const R = shown <= RING_AT[0] ? 1 : shown <= RING_AT[1] ? 2 : RING_CAPS.length;
  const w = RING_CAPS.slice(0, R), ws = w.reduce((a, b) => a + b, 0);
  const counts = w.map(x => Math.floor(shown * x / ws));
  let rem = shown - counts.reduce((a, b) => a + b, 0);
  w.map((x, i) => ({ i, frac: shown * x / ws - counts[i] }))
    .sort((a, b) => b.frac - a.frac)
    .forEach(o => { if (rem-- > 0) counts[o.i]++; });
  return { counts, shown, overflow: n - shown };
}

// place appears-in as concentric shells about a0 (south). a lone ring hugs
// bottom-centre when sparse (tidy fan); nested shells each spread the full sweep,
// staggered, so the annulus reads as even density. returns {pos:[{x,y,ring}], …}.
function rings(n, a0 = 90, span = RING_SPAN) {
  const plan = ringPlan(n);
  const R = plan.counts.length;
  const pos = [];
  plan.counts.forEach((k, r) => {
    if (k <= 0) return;
    const [rx, ry] = RING_RXY[r];
    const arc = k <= 1 ? 0
      : R === 1 ? span * (k - 1) / (RING_CAPS[r] - 1) // lone ring: tidy bottom fan
      : span;                                          // nested shells: full sweep
    const start = a0 - arc / 2 + r * RING_OFF;
    const step = k <= 1 ? 0 : arc / (k - 1);
    for (let i = 0; i < k; i++) {
      const a = (k === 1 ? a0 + r * RING_OFF : start + i * step) * Math.PI / 180;
      pos.push({ x: 50 + rx * Math.cos(a), y: 50 + ry * Math.sin(a), ring: r });
    }
  });
  return { pos, shown: plan.shown, overflow: plan.overflow };
}

// golden-angle phyllotaxis: radius ∝ √index gives uniform seed density (no ring
// crowding), and the blob's extent reads as magnitude. offset past the card;
// bucket radius into 3 tiers so the solid→halo grading + wire code still apply.
function spiral(n, cx = 50, cy = 50) {
  const shown = Math.min(n, RING_TOTAL);
  const pos = [];
  for (let i = 0; i < shown; i++) {
    const radius = SPIRAL_R0 + SPIRAL_SCALE * Math.sqrt(i + 0.5);
    const theta = i * GOLDEN + SPIRAL_TILT;
    const ring = i < shown / 3 ? 0 : i < 2 * shown / 3 ? 1 : 2; // solid / halo / faint, by index
    pos.push({ x: cx + radius * Math.cos(theta), y: cy + radius * Math.sin(theta), ring });
  }
  return { pos, shown, overflow: n - shown };
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

  // appears-in layout: rings (?layout=rings) or golden spiral (default). with parts
  // now inside the card, the spiral owns the full 360°. when it overflows, the last
  // slot becomes the "+N → list" affordance, not a dropped child.
  const layout = new URLSearchParams(location.search).get('layout') === 'rings' ? 'rings' : 'spiral';
  const R = layout === 'rings' ? rings(A.length) : spiral(A.length);
  const overflow = R.overflow > 0;
  const nReal = overflow ? R.shown - 1 : R.shown;
  const Ashow = A.slice(0, nReal);
  const sp = layout === 'spiral' ? ' spiral' : '';

  const f = facts(glyph);
  const center = byGlyph[glyph] && byGlyph[glyph].frontier ? 'egonode center frontier' : 'egonode center';
  // parts (what this glyph is built from) live inside the card as clickable chips
  const partStrip = P.length ? html`<div class="ec-parts">${P.map(g =>
    html`<button class="ec-part" data-glyph="${g}">${g}</button>`)}</div>` : '';
  const nodes = [html`<div class="${center}" data-key="center">
      <span class="ec-glyph">${glyph}</span>
      ${(f.py || f.kana) ? html`<span class="ec-facts">${[f.py, f.kana].filter(Boolean).join(' · ')}</span>` : ''}
      ${f.wk ? html`<span class="ec-wk ${f.mean ? 'mean' : 'mnem'}">${f.wk}</span>` : ''}
      ${partStrip}
    </div>`];
  Ashow.forEach((g, i) => { const p = R.pos[i]; nodes.push(nb(g, p.x, p.y, `whole ring${p.ring}${sp}`)); });
  if (overflow) {
    const p = R.pos[R.shown - 1]; // last outer slot → swap to sorted list
    nodes.push(html`<button class="egonode more overflow" data-more="1" style="left:${p.x}%;top:${p.y}%">+${A.length - nReal}</button>`);
  }
  const stage = document.getElementById('ego');
  stage.innerHTML = html`<svg id="egowires"></svg>${nodes}`;
  egoEls = {};
  stage.querySelectorAll('.egonode[data-key]').forEach(e => (egoEls[e.dataset.key] = e));
  stage.querySelectorAll('.egonode.nb').forEach(e => {
    e.addEventListener('click', () => focus(e.dataset.glyph));
    e.addEventListener('mouseenter', () => { const l = wireEls[e.dataset.key]; if (l) l.classList.add('hot'); });
    e.addEventListener('mouseleave', () => { const l = wireEls[e.dataset.key]; if (l) l.classList.remove('hot'); });
  });
  stage.querySelectorAll('.ec-part').forEach(e =>
    e.addEventListener('click', () => focus(e.dataset.glyph)));
  const of = stage.querySelector('.overflow');
  if (of) of.addEventListener('click', () => showList(glyph));
  drawEgoWires();
}

// overflow escape hatch: the full appears-in set as a sorted, scrollable grid —
// the honest browse view the radial "vibe" deliberately isn't.
function showList(glyph) {
  const A = (appears[glyph] || []).slice().sort();
  const stage = document.getElementById('ego');
  stage.innerHTML = html`
    <div class="ego-list">
      <div class="el-head">
        <span>${A.length} <span class="en">appears-in</span> · ${glyph}</span>
        <button class="el-back" type="button">↩ graph</button>
      </div>
      <div class="el-grid">${A.map(g => html`<button class="chip" data-glyph="${g}">${g}</button>`)}</div>
    </div>`;
  stage.querySelector('.el-back').addEventListener('click', () => renderEgo(glyph));
  stage.querySelectorAll('.el-grid .chip').forEach(c =>
    c.addEventListener('click', () => focus(c.dataset.glyph)));
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
    // radial spokes share one origin so they never cross; grade weight by ring
    // (solid → light → dashed) so outer stays ambient without going lineless.
    let cls = 'down';
    if (el.classList.contains('ring1')) cls += ' r1';
    else if (el.classList.contains('ring2')) cls += ' r2';
    const b = ctr(key);
    if (c && b) lines.push(html`<line x1="${c.x}" y1="${c.y}" x2="${b.x}" y2="${b.y}" class="wire ${cls}" data-key="${key}"/>`);
  });
  svg.innerHTML = html`${lines}`;
  wireEls = {};
  svg.querySelectorAll('line[data-key]').forEach(l => (wireEls[l.dataset.key] = l));
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
