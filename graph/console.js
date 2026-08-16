// /graph/console.js — author/debug console over the content graph.
// The seams-showing consumer of the same substrate the ego view browses:
// a coverage dashboard, integrity invariants, and a frontier worklist ranked
// by how much real context each stub already has. Chrome is plain English —
// this is a tool, not a study surface; the only CJK is the glyph data itself.
// Reads the generated graph (nodes/edges/bindings) directly; clicking any glyph
// drives the ego view via the global focus() defined in graph.js.

const CON = {}; // parsed graph, shared across renderers

Promise.all([
  fetch('../data/nodes.json').then(r => r.json()),
  fetch('../data/edges.json').then(r => r.json()),
  fetch('../data/bindings.json').then(r => r.json()),
]).then(([nd, ed, bd]) => {
  CON.nodes = nd.nodes;
  CON.edges = ed.edges;
  CON.bindings = bd.bindings;
  CON.byId = {};
  CON.nodes.forEach(n => (CON.byId[n.id] = n));
  renderCoverage();
  renderIntegrity();
  renderWorklist();
});

// jump to a glyph in the ego stage and scroll it into view
function inspect(glyph) {
  if (typeof focus === 'function') { focus(glyph); }
  const ego = document.getElementById('ego');
  if (ego) { ego.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
}

// ── derived views over the graph ────────────────────────────────────────────
function partition() {
  const glyph = CON.nodes.filter(n => n.kind === 'glyph');
  return {
    real: glyph.filter(n => !n.frontier),
    frontier: glyph.filter(n => n.frontier),
    referent: CON.nodes.filter(n => n.kind === 'referent'),
    word: CON.nodes.filter(n => n.kind === 'word'),
    composes: CON.edges.filter(e => e.kind === 'composes'),
    denotes: CON.edges.filter(e => e.kind === 'denotes'),
  };
}

// ── coverage dashboard: what the graph is made of ───────────────────────────
function renderCoverage() {
  const P = partition();
  const tier = k => P.real.filter(n => n.tier === k).length;
  const charN = tier('char');
  const withKanji = P.real.filter(n => {
    const jp = CON.bindings.find(b => b.id === `b:${n.glyph}@jp`);
    return jp && jp.program && jp.program.kanji;
  }).length;
  const withHw = P.real.filter(n => n.media && n.media.animated).length;

  const tiles = [
    { label: 'glyphs', n: P.real.length,
      sub: `${tier('stroke')} stroke · ${tier('component')} comp · ${charN} char`, cls: 'ink' },
    { label: 'frontier', n: P.frontier.length, sub: 'unbuilt · the worklist', cls: 'muted' },
    { label: 'referents', n: P.referent.length, sub: 'meaning spine', cls: 'gold' },
    { label: 'words', n: P.word.length, sub: 'vocab tier', cls: 'red' },
    { label: 'bindings', n: CON.bindings.length, sub: 'CN + JP layers', cls: 'navy' },
    { label: 'edges', n: CON.edges.length,
      sub: `${P.composes.length} composes · ${P.denotes.length} denotes`, cls: 'navy' },
  ];

  const bar = (label, num, den) => {
    const pct = den ? Math.round((num / den) * 100) : 0;
    return html`
      <div class="cov-bar">
        <div class="cb-head"><span class="cb-label">${label}</span>
          <span class="cb-frac">${num}/${den} · ${pct}%</span></div>
        <div class="cb-track"><div class="cb-fill" style="width:${pct}%"></div></div>
      </div>`;
  };

  document.getElementById('coverage').innerHTML = html`
    <div class="cov-tiles">
      ${tiles.map(t => html`
        <div class="cov-tile ${t.cls}">
          <div class="ct-n">${t.n}</div>
          <div class="ct-label">${t.label}</div>
          <div class="ct-sub">${t.sub}</div>
        </div>`)}
    </div>
    <div class="cov-bars">
      ${bar('kanji meaning authored', withKanji, charN)}
      ${bar('stroke animation', withHw, P.real.length)}
    </div>`;
}

// ── integrity: the invariants the build script keeps, checked live ──────────
// Hand-editing a JSON file can break one; this surfaces it the moment it does.
function renderIntegrity() {
  const P = partition();
  const ids = new Set(CON.nodes.map(n => n.id));
  const indeg = {}, outdeg = {};
  CON.edges.forEach(e => {
    outdeg[e.from] = (outdeg[e.from] || 0) + 1;
    indeg[e.to] = (indeg[e.to] || 0) + 1;
  });
  const bindCount = {};
  CON.bindings.forEach(b => (bindCount[b.glyph_id] = (bindCount[b.glyph_id] || 0) + 1));
  const denToRef = {};
  P.denotes.forEach(e => (denToRef[e.to] = denToRef[e.to] || []).push(e.from));

  const glyphOf = id => (CON.byId[id] && CON.byId[id].glyph) || id;

  const checks = [
    { name: 'dangling edges', level: 'err',
      hits: CON.edges.filter(e => !ids.has(e.from) || !ids.has(e.to)).map(e => `${e.from}→${e.to}`) },
    { name: 'orphan real glyphs', level: 'warn',
      hits: P.real.filter(n => !indeg[n.id] && !outdeg[n.id]).map(n => n.glyph) },
    { name: 'glyph missing a binding', level: 'warn',
      hits: P.real.filter(n => (bindCount[n.id] || 0) < 2).map(n => n.glyph) },
    { name: 'referent with no label', level: 'warn',
      hits: P.referent.filter(r => !r.label).map(r => r.id) },
    { name: 'referent with no denoter', level: 'err',
      hits: P.referent.filter(r => !denToRef[r.id]).map(r => r.id) },
    { name: 'single-denoter referent', level: 'info',
      note: 'join not yet realized — one glyph/word points here; a second language or form would make it a bridge',
      hits: P.referent.filter(r => (denToRef[r.id] || []).length === 1)
        .map(r => ({ label: r.label || r.id, glyph: glyphOf(denToRef[r.id][0]) })) },
  ];

  const chip = h => typeof h === 'string'
    ? html`<button class="ic-chip" onclick="inspect('${h}')">${h}</button>`
    : html`<button class="ic-chip" onclick="inspect('${h.glyph}')"><span class="icc-g">${h.glyph}</span> ${h.label}</button>`;

  const errs = checks.filter(c => c.level !== 'info' && c.hits.length).length;
  document.getElementById('integrity').innerHTML = html`
    <div class="int-summary ${errs ? 'bad' : 'ok'}">
      ${errs ? html`⚠ ${errs} check(s) firing` : html`✓ all structural invariants holding`}
    </div>
    ${checks.map(c => html`
      <div class="int-row ${c.level} ${c.hits.length ? 'hit' : 'clear'}">
        <span class="ir-dot"></span>
        <span class="ir-name">${c.name}</span>
        <span class="ir-count">${c.hits.length}</span>
        ${c.hits.length ? html`<div class="ir-hits">${c.hits.map(chip)}</div>` : ''}
        ${c.note && c.hits.length ? html`<div class="ir-note">${c.note}</div>` : ''}
      </div>`)}`;
}

// ── frontier worklist: what to author next, ranked by ready context ─────────
// A frontier stub's score = how many REAL glyphs already touch it. High score →
// lots of authored context already exists, so it's the cheapest high-value card.
function renderWorklist() {
  const P = partition();
  const isReal = {}, isFront = {};
  CON.nodes.forEach(n => {
    if (n.kind !== 'glyph') { return; }
    (n.frontier ? isFront : isReal)[n.id] = n;
  });
  const parts = {}, wholes = {}; // frontier id → real glyphs that are its parts / wholes
  P.composes.forEach(e => {
    if (isFront[e.to] && isReal[e.from]) { (parts[e.to] = parts[e.to] || []).push(CON.byId[e.from].glyph); }
    if (isFront[e.from] && isReal[e.to]) { (wholes[e.from] = wholes[e.from] || []).push(CON.byId[e.to].glyph); }
  });
  const ranked = P.frontier.map(n => ({
    glyph: n.glyph,
    parts: parts[n.id] || [],
    wholes: wholes[n.id] || [],
  })).map(w => ({ ...w, score: w.parts.length + w.wholes.length }))
    .sort((a, b) => b.score - a.score || a.glyph.localeCompare(b.glyph));

  const ready = ranked.filter(w => w.score > 0);
  document.getElementById('worklist').innerHTML = html`
    <div class="wl-note">
      ${ready.length} of ${ranked.length} frontier stubs already border authored glyphs.
      Higher score = more context in place = cheapest next card.
    </div>
    <div class="wl-grid">
      ${ranked.map(w => html`
        <button class="wl-item${w.score ? '' : ' cold'}" onclick="inspect('${w.glyph}')">
          <span class="wl-glyph">${w.glyph}</span>
          <span class="wl-score">${w.score}</span>
          <span class="wl-nb">
            ${w.parts.length ? html`<span class="wl-line"><span class="wl-k">built from</span>${w.parts.map(g => html`<b>${g}</b>`)}</span>` : ''}
            ${w.wholes.length ? html`<span class="wl-line"><span class="wl-k">seen in</span>${w.wholes.map(g => html`<b>${g}</b>`)}</span>` : ''}
          </span>
        </button>`)}
    </div>`;
}
