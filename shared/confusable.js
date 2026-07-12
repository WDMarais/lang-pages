// Confusable panel — renders an authored `confusable` cluster (data/authored.json →
// edges.json "clusters"). Used by /glyph/ and /graph/.
//
// VISUAL-FIRST: the members go side by side, LARGE and stroke-animated, because for a
// visual cluster (己/已/巳 — 开口己、半口已、闭口巳) the difference IS the shape; reading a
// sentence about it is the wrong channel. The prose note is demoted BELOW the tiles.
// Each member carries its own grounding example, so the meanings anchor to distinct
// contexts from the start rather than being told apart after the fact.

const BASIS = {
  visual:   { zh: '形近', en: 'look alike' },
  phonetic: { zh: '音近', en: 'sound alike' },
  semantic: { zh: '义近', en: 'mean alike' },
};

// A member id is g:己 (glyph) or w:可不@cn (word). Glyphs get the animated diagram;
// words render as their surface — there is no stroke data for a multi-glyph surface.
function cfMember(G, id, focusId) {
  const node = G.byId[id];
  const isGlyph = id.startsWith('g:');
  const surface = node ? (node.glyph || '') : id.replace(/^[gw]:/, '').replace(/@\w+$/, '');
  const me = id === focusId;

  let reading = '', gloss = '';
  if (isGlyph && node) {
    const f = gdFacts(G, node.glyph);
    reading = [f.py, f.kana].filter(Boolean).join(' · ');
    gloss = f.gloss;
  } else if (node) {
    reading = node.reading || '';
    gloss = node.gloss || '';
  }

  // stroke-animated when the glyph has hanzi-data; otherwise the crisp glyph itself.
  const hw = isGlyph && node && node.media && node.media.hw;
  const art = hw
    ? html`<div class="cf-hw sc-hw" data-char="${surface}"></div>`
    : html`<div class="cf-plain">${surface}</div>`;

  return html`
    <button class="cf-member${me ? ' me' : ''}" data-goto="${id}"
            title="${me ? 'this one' : `go to ${surface}`}">
      <div class="cf-art">${art}</div>
      <div class="cf-surface">${surface}</div>
      ${reading ? html`<div class="cf-reading">${reading}</div>` : ''}
      ${gloss ? html`<div class="cf-gloss en">${gloss}</div>` : ''}
    </button>`;
}

// grounding: one example per member, keyed by the member id it teaches.
function cfExample(G, ex) {
  const node = G.byId[ex.for];
  const surface = node ? (node.glyph || '') : ex.for;
  const src = ex.audioKey ? `/audio/sent/${ex.audioKey}.mp3` : '';
  return html`
    <div class="cf-ex">
      <div class="cf-ex-for">${surface}</div>
      <div class="cf-ex-body">
        <div class="cf-ex-text">${ex.text}${src ? play(src) : ''}</div>
        <div class="cf-ex-gloss en">${ex.gloss}</div>
      </div>
    </div>`;
}

// renderConfusable(G, id) → the panel(s) for every cluster `id` belongs to, or '' if none.
function renderConfusable(G, id) {
  const cs = G.confusOf[id] || [];
  if (!cs.length) return '';
  return html`${cs.map(c => {
    const b = BASIS[c.basis] || { zh: '易混', en: 'confusable' };
    const others = (c.members || []).filter(m => m !== id).length;
    return html`
      <div class="cf-panel" data-cluster="${c.id}">
        <div class="cf-head">
          <span class="cf-mark">易混</span>
          <span class="cf-basis cf-${c.basis || 'other'}">${b.zh} · <span class="en">${b.en}</span></span>
          <span class="cf-count en">${others} other${others === 1 ? '' : 's'}</span>
        </div>
        <div class="cf-members">${(c.members || []).map(m => cfMember(G, m, id))}</div>
        ${c.examples && c.examples.length
          ? html`<div class="cf-examples">${c.examples.map(e => cfExample(G, e))}</div>` : ''}
        ${c.note ? html`<div class="cf-note en">${c.note}</div>` : ''}
      </div>`;
  })}`;
}

// wire member tiles → navigate. `go` receives the member node id.
function bindConfusable(root, go) {
  root.querySelectorAll('.cf-member[data-goto]').forEach(el =>
    el.addEventListener('click', () => go(el.dataset.goto)));
}
