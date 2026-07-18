// JP-centered projection — a single-language (日本語) focus-study view, graph-backed.
//
// Master-detail: a tier-grouped rail of glyphs on the left, one large card on the
// right. JP-forward — the hero is glyph + reading, and the meaning is shown as an
// illustrated REFERENT (procedural dot-piles for number referents) rather than an
// English headline. Reads the GENERATED graph (nodes + edges + bindings): the
// vocabulary and the referent illustration are both edge queries, not card fields.
// Reuses diagram() from cards3.js; owns its own (larger) HanziWriter init.

const JP_TIER = [
  { tier: 'char',      label: '漢字',      sub: 'kanji' },
  { tier: 'component', label: '部首・部件', sub: 'radicals & components' },
  { tier: 'stroke',    label: '画',        sub: 'strokes' },
];

// Number referents get a concrete quantity illustration (concrete-first): N dots.
// Non-number referents fall back to the gloss until per-referent icons exist.
const JP_NUM = { one: 1, two: 2, three: 3, four: 4, five: 5,
                 six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };

// Split kanji readings into 音読み / 訓読み. `readings` are on'yomi when on=true,
// else kun'yomi; `kun` is always kun. (Same reading-class logic as cards3.js.)
function jpReadings(kanji) {
  if (!kanji) { return { on: [], kun: [] }; }
  const on = kanji.on ? (kanji.readings || []) : [];
  const kun = [...(kanji.on ? [] : (kanji.readings || [])), ...(kanji.kun || [])];
  return { on, kun };
}

function jpReadingRow(cls, tag, list) {
  if (!list.length) { return ''; }
  return html`<div class="jp-yomi ${cls}"><span class="jp-yomi-tag">${tag}</span>${list.join('・')}</div>`;
}

// Mark the okurigana tail (七[つ], 入[る]); compounds (二人) render plain.
function jpWordSurface(w) {
  const s = w.glyph, oku = w.okurigana;
  if (oku && s.endsWith(oku)) {
    return html`${s.slice(0, s.length - oku.length)}<span class="jp-oku">${oku}</span>`;
  }
  return html`${s}`;
}

function jpVocab(words) {
  if (!words.length) { return ''; }
  return html`
      <div class="jp-vocab">
        <div class="jp-vocab-tag">語彙</div>
        ${words.map(w => html`
        <div class="jp-word">
          <span class="jp-word-surface">${jpWordSurface(w)}</span>
          <span class="jp-word-reading">${w.reading}</span>
          <span class="jp-word-gloss">${w.gloss}</span>
        </div>`)}
      </div>`;
}

// Referent slot — the meaning, illustrated. Numbers get a dot-pile (the proof);
// everything else shows the gloss and leaves the illustration slot for later.
function jpReferent(ref) {
  if (!ref) { return ''; }
  const n = JP_NUM[ref.id.slice(2)];  // strip "r:"
  // Ten-frame: a fixed 2×5 grid, first n cells filled. The frame is identical on
  // every number card, so the count reads against a stable anchor (七 = 5 + 2,
  // three short of ten). Our number referents cap at ten.
  const dots = n
    ? html`<div class="jp-dots">${Array.from({ length: 10 }, (_, i) =>
        html`<span class="jp-dot${i < n ? '' : ' empty'}"></span>`)}</div>`
    : html`<div class="jp-illus-todo"></div>`;
  return html`
        <div class="jp-referent">
          <div class="jp-ref-label">意味</div>
          ${dots}
          <div class="jp-ref-gloss">${ref.label}</div>
        </div>`;
}

// WK progression — radical (mnemonic-cautioned) + kanji, demoted to a small strip.
function jpWk(prog) {
  if (!prog) return '';
  let rad = '';
  if (prog.name) {
    const meaning = prog.kind === 'meaning';
    rad = html`<span class="jp-wk-item ${meaning ? 'wk-meaning' : 'wk-mnemonic'}">${
      meaning ? '' : mnemonic(prog.icon)}<span class="jp-wk-tag">部首</span> ${prog.name}
        <span class="jp-lvl">Lv.${prog.level}</span></span>`;
  }
  const k = prog.kanji;
  const kan = k ? html`<span class="jp-wk-item wk-meaning"><span class="jp-wk-tag">漢字</span> ${k.name}
        <span class="jp-lvl">Lv.${k.level}</span></span>` : '';
  if (!rad && !kan) return '';
  return html`<div class="jp-wk">${rad}${kan}</div>`;
}

function jpFocusCard(state, id) {
  const n = state.byId[id];
  const b = state.jpBind[id];
  const prog = b && b.program;
  const { on, kun } = jpReadings(prog && prog.kanji);
  const kana = (!on.length && !kun.length && b && b.readings[0]) ? b.readings[0] : '';
  return html`
    <article class="jp-focus-card">
      <div class="jp-focus-top">
        <div class="jp-focus-glyph">${diagram({ hw: n.media && n.media.hw, glyph: n.glyph })}</div>
        <div class="jp-focus-head">
          <div class="jp-readings">
            ${jpReadingRow('on', '音', on)}
            ${jpReadingRow('kun', '訓', kun)}
            ${kana ? html`<div class="jp-yomi"><span class="jp-yomi-tag">仮</span>${kana}</div>` : ''}
          </div>
          ${jpReferent(state.refOf[id])}
          ${jpWk(prog)}
        </div>
      </div>
      ${jpVocab(state.vocabOf[id] || [])}
    </article>`;
}

function jpRail(state) {
  return JP_TIER.map(g => {
    const items = state.glyphs.filter(n => n.tier === g.tier);
    if (!items.length) return '';
    return html`
      <div class="jp-rail-group">
        <div class="jp-rail-head">${g.label}</div>
        <div class="jp-rail-items">${items.map(n => {
          const b = state.jpBind[n.id];
          return html`<button class="jp-rail-item" data-id="${n.id}" title="${b ? b.gloss : ''}"><span class="jp-rail-glyph">${n.glyph}</span></button>`;
        })}</div>
      </div>`;
  }).join('');
}

// Larger, animated glyph for the focus pane (cards3's initHanzi is fixed at 112).
// Each select() replaces the focus innerHTML, detaching the previous writer's SVG —
// but its loop keeps scheduling rAF/timeouts on the orphaned node. Stop the old one
// (pauseAnimation clears its pending timeouts) before minting the next, or every
// navigation leaks another live loop.
function jpFocusHanzi(state, char) {
  const el = document.querySelector('.jp-focus-glyph .sc-hw');
  if (!el || typeof HanziWriter === 'undefined') return;
  if (state.focusWriter) state.focusWriter.pauseAnimation();
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const navy = getComputedStyle(document.documentElement).getPropertyValue('--navy').trim() || '#1E2A4A';
  const w = HanziWriter.create(el, char, {
    width: 240, height: 240, padding: 16,
    strokeColor: navy, outlineColor: '#D8D2C4', showOutline: true,
    strokeAnimationSpeed: 1, delayBetweenStrokes: 240,
    charDataLoader: (c, done) => fetch(`../shared/hanzi-data/${c}.json`).then(r => r.json()).then(done),
  });
  state.focusWriter = w;
  if (!reduce) w.loopCharacterAnimation();
}

function jpMount(state) {
  state.rail.innerHTML = jpRail(state);
  const select = id => {
    state.focus.innerHTML = jpFocusCard(state, id);
    state.rail.querySelectorAll('.jp-rail-item').forEach(b =>
      b.classList.toggle('sel', b.dataset.id === id));
    const n = state.byId[id];
    if (n.media && n.media.hw) jpFocusHanzi(state, n.glyph);
  };
  state.rail.addEventListener('click', e => {
    const btn = e.target.closest('.jp-rail-item');
    if (btn) select(btn.dataset.id);
  });
  const first = state.glyphs.find(n => n.tier === 'char') || state.glyphs[0];
  if (first) select(first.id);
}

const jpApp = document.getElementById('jp-app');
if (jpApp) {
  Promise.all([
    fetch('../data/nodes.json').then(r => r.json()),
    fetch('../data/edges.json').then(r => r.json()),
    fetch('../data/bindings.json').then(r => r.json()),
  ]).then(([nd, ed, bd]) => {
    const byId = {};
    nd.nodes.forEach(n => { byId[n.id] = n; });
    const jpBind = {};
    bd.bindings.forEach(b => { if (b.lang === 'jp') jpBind[b.glyph_id] = b; });
    const vocabOf = {}, refOf = {};
    ed.edges.forEach(e => {
      const from = byId[e.from];
      if (e.kind === 'composes' && byId[e.to] && byId[e.to].kind === 'word') {
        (vocabOf[e.from] = vocabOf[e.from] || []).push(byId[e.to]);
      }
      if (e.kind === 'denotes' && from && from.kind === 'glyph' && byId[e.to]) {
        refOf[e.from] = byId[e.to];
      }
    });
    jpMount({
      byId, jpBind, vocabOf, refOf, focusWriter: null,
      glyphs: nd.nodes.filter(n => n.kind === 'glyph' && !n.frontier),
      rail: jpApp.querySelector('.jp-rail'),
      focus: jpApp.querySelector('.jp-focus'),
    });
  });
}
