// Shared three-view (中文 · 日本語 · Wanikani) card renderer.
// A page supplies its data file via <div id="cards" data-src="...json">.
// JSON shape: { groups: [ { title?, sub?, cards: [...] } ] }
// A card animates its stroke order only if it carries an `svg` field; otherwise
// the diagram is just the (crisp Kai) glyph — used for deferred / un-tuned cards.

function diagram(c) {
  const strokes = c.svg && c.svg.strokes ? c.svg.strokes : [];
  const tracers = strokes.map((s, i) => {
    const begin = (i * 0.7).toFixed(2);
    return `<circle class="sc-startdot" cx="${s.start[0]}" cy="${s.start[1]}" r="3.5"/>` +
      `<circle class="sc-tracer" r="4">` +
      `<animateMotion dur="1.9s" begin="${begin}s" repeatCount="indefinite" ` +
      `calcMode="linear" keyTimes="0;0.55;1" keyPoints="0;1;1" path="${s.d}"/></circle>`;
  }).join('');
  return `
        <svg class="sc-hero" viewBox="0 0 100 100" aria-hidden="true">
          <text class="sc-gtext" x="50" y="50">${c.glyph}</text>
          ${tracers}
        </svg>`;
}

// ── Mnemonic line-icons for shape-mnemonic Wanikani names ──
const ICONS = {
  ground: '<path d="M5 28 H35"/><path d="M13 28 Q20 18 27 28"/><path d="M9 28 v-3"/><path d="M31 28 v-3"/>',
  slide:  '<path d="M11 33 V13 H15"/><path d="M15 13 C24 13 22 33 31 33"/><path d="M8 33 H34"/><path d="M7 19 H11"/><path d="M7 24 H11"/>',
  drop:   '<path d="M20 6 C20 6 9 21 9 28 a11 11 0 0 0 22 0 C31 21 20 6 20 6 Z"/>',
  barb:   '<path d="M27 8 V24 a8 8 0 1 1 -16 0"/><path d="M11 24 l-2 -5"/><path d="M11 24 l5 -1"/>',
  fins:   '<path d="M6 20 C13 12 27 12 33 20 C27 28 13 28 6 20 Z"/><path d="M6 20 L1 15 L3 20 L1 25 Z"/><circle cx="27" cy="18" r="1.3"/><path d="M17 12 l3 -5 l3 5"/>',
  lid:    '<path d="M6 27 a14 9 0 0 1 28 0 Z"/><path d="M5 27 H35"/><path d="M20 14 v-4"/>',
};
function mnemonic(name) {
  return `<svg class="sc-mnemonic" viewBox="0 0 40 40" aria-hidden="true">${ICONS[name] || ''}</svg>`;
}

function play(src) {
  return `<button class="vplay sc-play" data-src="${src}" aria-label="play">▶</button>`;
}

function langView(cls, label, v, audioName, audioEx) {
  const name = `<span class="sc-name">${v.name}</span>` +
    (v.reading ? ` <span class="sc-reading">${v.reading}</span>` : '');
  const extra = v.extra ? `<div class="sc-extra">${v.extra}</div>` : '';
  const ex = v.ex ? `
        <div class="sc-ex">
          <span class="sc-exlabel">例</span>
          <span class="sc-exchar">${v.ex.char}</span>
          <span class="sc-reading">${v.ex.reading}</span>
          <span class="en">— ${v.ex.gloss}</span>
          ${play(audioEx)}
        </div>` : '';
  return `
      <div class="sc-view ${cls}">
        <div class="sc-vlabel">${label}</div>
        <div class="sc-nameline">${name}${play(audioName)}</div>
        <div class="sc-gloss en">${v.gloss || ''}</div>
        ${extra}${ex}
      </div>`;
}

// Wanikani column. meaning → green/solid (transfers); mnemonic → red/dashed + icon.
function wkView(wk) {
  if (!wk) {
    return `
      <div class="sc-view v-wk empty">
        <div class="sc-vlabel">Wanikani</div>
        <div class="sc-empty">—</div>
      </div>`;
  }
  const glyph = wk.glyph ? ` <span class="sc-altglyph">${wk.glyph}</span>` : '';
  const meaning = wk.kind === 'meaning';
  const visual = meaning ? `<div class="sc-check">✓</div>` : mnemonic(wk.icon);
  const flag = meaning
    ? `<div class="sc-only sc-true">实义 · 通用</div>`
    : `<div class="sc-only">仅助记</div>`;
  return `
      <div class="sc-view v-wk ${meaning ? 'wk-meaning' : 'wk-mnemonic'}">
        <div class="sc-vlabel">Wanikani <span class="sc-lvl">Lv.${wk.level}</span></div>
        ${visual}
        <div class="sc-nameline"><span class="sc-name">${wk.name}</span>${glyph}</div>
        ${flag}
      </div>`;
}

const TAG_LABEL = { stroke: '笔画', comp: '部件', char: '字' };

function renderCard(c) {
  const img = c.image ? `<img class="sc-img" src="${c.image}" alt="">` : '';
  const tagCls = c.tag === 'char' ? 'tag-char' : (c.tag === 'comp' ? 'tag-comp' : '');
  const tag = `<span class="sc-tag ${tagCls}">${TAG_LABEL[c.tag] || '笔画'}</span>`;
  return `
    <div class="scard">
      <div class="sc-glyph">
        ${diagram(c)}
        ${tag}
        ${img}
      </div>
      <div class="sc-views">
        ${langView('v-cn', '中文', c.cn, `audio/cn-${c.slug}.mp3`, `audio/cn-${c.slug}-ex.mp3`)}
        ${langView('v-jp', '日本語', c.jp, `audio/jp-${c.slug}.mp3`, `audio/jp-${c.slug}-ex.mp3`)}
        ${wkView(c.wk)}
      </div>
    </div>`;
}

function renderGroup(g) {
  const head = g.title
    ? `<div class="sc-grouphead"><span class="sc-gtitle">${g.title}</span>${g.sub ? `<span class="sc-gsub">${g.sub}</span>` : ''}</div>`
    : '';
  return `<div class="sc-group">${head}${g.cards.map(renderCard).join('')}</div>`;
}

const host = document.getElementById('cards');
fetch(host.dataset.src)
  .then(r => r.json())
  .then(d => { host.innerHTML = d.groups.map(renderGroup).join(''); });
