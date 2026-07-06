// Shared four-view (Pandanese · 中文 · 日本語 · Wanikani) card renderer.
// Programs bookend the two real-language views: Pandanese (CN-side) left,
// Wanikani (JP-side) right, with 中文 · 日本語 centered for direct comparison.
// A page supplies its data file via <div id="cards" data-src="...json">.
// JSON shape: { groups: [ { title?, sub?, cards: [...] } ] }
// A card animates its stroke order via HanziWriter when it sets `hw: true`;
// otherwise the diagram is just the crisp Kai glyph — for deferred / un-tuned cards.

// Page-level layout mode, set from <div id="cards" data-layout="…">. Default ''
// = the four-column comparison card; 'radical' = the lighter /kangxi/ card.
let LAYOUT = '';

function diagram(c) {
  // Character cards opt into data-driven stroke-order animation (HanziWriter);
  // init happens after innerHTML in initHanzi(). Un-tuned cards degrade to the glyph.
  if (c.hw) return html`<div class="sc-hw" data-char="${c.glyph}"></div>`;
  return html`
        <svg class="sc-hero" viewBox="0 0 100 100" aria-hidden="true">
          <text class="sc-gtext" x="50" y="50">${c.glyph}</text>
        </svg>`;
}

// ── Mnemonic line-icons for shape-mnemonic Wanikani names ──
const ICONS = {
  ground: '<path d="M5 28 H35"/><path d="M13 28 Q20 18 27 28"/><path d="M9 28 v-3"/><path d="M31 28 v-3"/>',
  slide:  '<path d="M11 33 V13 H15"/><path d="M15 13 C24 13 22 33 31 33"/><path d="M8 33 H34"/><path d="M7 19 H11"/><path d="M7 24 H11"/>',
  drop:   '<path d="M20 6 C20 6 9 21 9 28 a11 11 0 0 0 22 0 C31 21 20 6 20 6 Z"/>',
  barb:   '<circle cx="25" cy="7.3" r="2.3"/><path d="M25 9.6 V20.5 A6.5 6.5 0 1 1 12 20.5 L13.5 13"/><path d="M13.5 13 L8.5 15.5"/>',
  fins:   '<path d="M6 20 C13 12 27 12 33 20 C27 28 13 28 6 20 Z"/><path d="M6 20 L1 15 L3 20 L1 25 Z"/><circle cx="27" cy="18" r="1.3"/><path d="M17 12 l3 -5 l3 5"/>',
  lid:    '<path d="M6 27 a14 9 0 0 1 28 0 Z"/><path d="M5 27 H35"/><path d="M20 14 v-4"/>',
  prison: '<path d="M9 9 H31 V33 H9 Z"/><path d="M16 9 V33"/><path d="M23 9 V33"/>',
  cross:  '<path d="M16 7 H24 V16 H33 V24 H24 V33 H16 V24 H7 V16 H16 Z"/>',
  gun:    '<path d="M7 13 H32 V19 H21 L18 31 H12 L15 19 H7 Z"/><path d="M16 19 q2 4 5 1"/><path d="M26 13 V10 H30 V13"/>',
  toe:    '<ellipse cx="18" cy="27" rx="8" ry="5"/><circle cx="13" cy="15" r="3"/><circle cx="20" cy="12" r="2.6"/><circle cx="26" cy="15" r="2.1"/>',
  tv:     '<path d="M6 15 H30 V31 H6 Z"/><path d="M10 19 H26 V28 H10 Z"/><path d="M14 15 L9 6"/><path d="M22 15 L27 6"/><path d="M13 31 v3"/><path d="M23 31 v3"/>',
};
function mnemonic(name) {
  return html`<svg class="sc-mnemonic" viewBox="0 0 40 40" aria-hidden="true">${raw(ICONS[name] || '')}</svg>`;
}

function play(src) {
  return html`<button class="vplay sc-play" data-src="${src}" aria-label="play">▶</button>`;
}

function langView(cls, label, v, audioName, audioEx) {
  const name = html`<span class="sc-name">${v.name}</span>${
    v.reading ? html` <span class="sc-reading">${v.reading}</span>` : ''}`;
  const extra = v.extra ? html`<div class="sc-extra">${v.extra}</div>` : '';
  const ex = v.appearsIn ? html`
        <div class="sc-ex">
          <span class="sc-exlabel">例</span>
          <span class="sc-exchar">${v.appearsIn.char}</span>
          <span class="sc-reading">${v.appearsIn.reading}</span>
          <span class="en">— ${v.appearsIn.gloss}</span>
          ${play(audioEx)}
        </div>` : '';
  return html`
      <div class="sc-view ${cls}">
        <div class="sc-vlabel">${label}</div>
        <div class="sc-nameline">${name}${play(audioName)}</div>
        <div class="sc-gloss en">${v.gloss || ''}</div>
        ${extra}${ex}
      </div>`;
}

// Wanikani column. meaning → green/solid (transfers); mnemonic → red/dashed + icon.
// WaniKani ships radical and kanji as separate items on one glyph; when a kanji
// has unlocked we collapse both into this column (radical above, kanji below)
// rather than spawning a second near-duplicate card. on'yomi shows in katakana,
// kun'yomi in hiragana — the script itself carries the reading-class cue.
function wkView(wk, kanji) {
  if (!wk && !kanji) {
    return html`
      <div class="sc-view v-wk empty">
        <div class="sc-vlabel">Wanikani</div>
        <div class="sc-empty">—</div>
      </div>`;
  }
  // single radical, no kanji yet → original full-bleed layout (unchanged).
  if (wk && !kanji) {
    const glyph = wk.glyph ? html` <span class="sc-altglyph">${wk.glyph}</span>` : '';
    const meaning = wk.kind === 'meaning';
    const visual = meaning ? html`<div class="sc-check">✓</div>` : mnemonic(wk.icon);
    const flag = meaning
      ? html`<div class="sc-only sc-true">实义 · 通用</div>`
      : html`<div class="sc-only">仅助记</div>`;
    return html`
      <div class="sc-view v-wk ${meaning ? 'wk-meaning' : 'wk-mnemonic'}">
        <div class="sc-vlabel">Wanikani <span class="sc-lvl">Lv.${wk.level}</span></div>
        ${visual}
        <div class="sc-nameline"><span class="sc-name">${wk.name}</span>${glyph}</div>
        ${flag}
      </div>`;
  }
  // radical + kanji → stacked items, each carrying its own meaning/mnemonic cue.
  return html`
      <div class="sc-view v-wk v-wk-stack">
        <div class="sc-vlabel">Wanikani</div>
        ${wk ? wkItem('部首', wk) : ''}
        ${kanji ? kanjiItem(kanji) : ''}
      </div>`;
}

// Pandanese column — CN-side mirror of Wanikani, same meaning(green ✓) /
// mnemonic(red-dashed) coding. Pandanese ships two tiers like WK does: a radical
// plus a CHARACTER item (the CN analog of kanji — real meaning, always green), so
// it takes the same radical+item stacked variant. A mnemonic with no matching
// line-icon (e.g. 向 "TV") drops the visual rather than rendering an empty box.
// Kept in its own tagged block so a release build can strip proprietary mnemonics
// (see memory: strippability).
function pdView(pd, pdc) {
  if (!pd && !pdc) {
    return html`
      <div class="sc-view v-pd empty">
        <div class="sc-vlabel">Pandanese</div>
        <div class="sc-empty">—</div>
      </div>`;
  }
  // single radical, no character yet → original full-bleed layout (unchanged).
  if (pd && !pdc) {
    const meaning = pd.kind === 'meaning';
    const visual = meaning
      ? html`<div class="sc-check">✓</div>`
      : (pd.icon && ICONS[pd.icon] ? mnemonic(pd.icon) : '');
    const flag = meaning
      ? html`<div class="sc-only sc-true">实义 · 通用</div>`
      : html`<div class="sc-only">仅助记</div>`;
    return html`
      <div class="sc-view v-pd ${meaning ? 'pd-meaning' : 'pd-mnemonic'}">
        <div class="sc-vlabel">Pandanese <span class="sc-lvl">Lv.${pd.level}</span></div>
        ${visual}
        <div class="sc-nameline"><span class="sc-name">${pd.name}</span></div>
        ${flag}
      </div>`;
  }
  // radical + character → stacked items, each carrying its own meaning/mnemonic cue.
  return html`
      <div class="sc-view v-pd v-pd-stack">
        <div class="sc-vlabel">Pandanese</div>
        ${pd ? pdItem('部首', pd) : ''}
        ${pdc ? pdCharItem(pdc) : ''}
      </div>`;
}

// radical sub-item: keeps the mnemonic line-icon (the shape-only warning cue).
function pdItem(tag, pd) {
  const meaning = pd.kind === 'meaning';
  const icon = meaning ? '' : (pd.icon && ICONS[pd.icon] ? mnemonic(pd.icon) : '');
  const flag = meaning ? html`<span class="sc-only sc-true">实义</span>` : html`<span class="sc-only">仅助记</span>`;
  return html`
        <div class="sc-pd-item ${meaning ? 'pd-meaning' : 'pd-mnemonic'}">
          ${icon}
          <div class="sc-wk-head"><span class="sc-wk-tag">${tag}</span>
            <span class="sc-name">${pd.name}</span>
            <span class="sc-lvl">Lv.${pd.level}</span></div>
          ${flag}
        </div>`;
}

// character sub-item: real meaning (always → green), the CN analog of kanjiItem.
function pdCharItem(pdc) {
  return html`
        <div class="sc-pd-item pd-meaning">
          <div class="sc-wk-head"><span class="sc-wk-tag">字</span>
            <span class="sc-name">${pdc.name}</span>
            <span class="sc-lvl">Lv.${pdc.level}</span></div>
          <span class="sc-only sc-true">实义 · 通用</span>
        </div>`;
}

// radical sub-item: keeps the mnemonic line-icon (the shape-only warning cue).
function wkItem(tag, wk) {
  const meaning = wk.kind === 'meaning';
  const icon = meaning ? '' : mnemonic(wk.icon);
  const glyph = wk.glyph ? html` <span class="sc-altglyph">${wk.glyph}</span>` : '';
  const flag = meaning ? html`<span class="sc-only sc-true">实义</span>` : html`<span class="sc-only">仅助记</span>`;
  return html`
        <div class="sc-wk-item ${meaning ? 'wk-meaning' : 'wk-mnemonic'}">
          ${icon}
          <div class="sc-wk-head"><span class="sc-wk-tag">${tag}</span>
            <span class="sc-name">${wk.name}</span>${glyph}
            <span class="sc-lvl">Lv.${wk.level}</span></div>
          ${flag}
        </div>`;
}

// kanji sub-item: real meaning (always maps → green) + on/kun reading.
function kanjiItem(k) {
  const on = k.readings || [];
  const kun = k.kun || [];
  const rd = [...on, ...kun].join('・');
  const reading = rd ? html` <span class="sc-reading">${rd}</span>` : '';
  // Script itself cues the class (katakana on'yomi / hiragana kun'yomi); the
  // label just names which classes are present.
  const labels = [];
  if (on.length) labels.push(k.on ? '音読み' : '訓読み');
  if (kun.length) labels.push('訓読み');
  const yomi = labels.join(' · ');
  return html`
        <div class="sc-wk-item wk-meaning">
          <div class="sc-wk-head"><span class="sc-wk-tag">漢字</span>
            <span class="sc-name">${k.name}</span>${reading}
            <span class="sc-lvl">Lv.${k.level}</span></div>
          <span class="sc-only sc-true">${yomi}</span>
        </div>`;
}

const TAG_LABEL = { stroke: '笔画', comp: '部件', char: '字' };

// Kangxi-spine stub: a radical we haven't built a full card for yet. Compact,
// greyed tile carrying only the canonical glyph + Kangxi number + meaning, so the
// /kangxi/ page is a complete, honest 214-deck with the gaps visible.
function renderStub(c) {
  return html`
    <div class="scard scard-stub" title="Kangxi ${c.kx} · ${c.meaning}">
      <span class="sc-kx">${c.kx}</span>
      <svg class="sc-hero sc-stub-glyph" viewBox="0 0 100 100" aria-hidden="true">
        <text class="sc-gtext" x="50" y="50">${c.glyph}</text>
      </svg>
      <div class="sc-stub-meaning en">${c.meaning}</div>
      <div class="sc-stub-py">${c.pinyin || ''}</div>
    </div>`;
}

function renderCard(c) {
  if (c.stub) return renderStub(c);
  const img = c.image ? html`<img class="sc-img" src="${c.image}" alt="">` : '';
  const tagCls = c.tag === 'char' ? 'tag-char' : (c.tag === 'comp' ? 'tag-comp' : '');
  const tag = html`<span class="sc-tag ${tagCls}">${TAG_LABEL[c.tag] || '笔画'}</span>`;
  const kx = c.kx ? html`<span class="sc-kx">${c.kx}</span>` : '';
  return html`
    <div class="scard">
      <div class="sc-glyph">
        ${kx}
        ${diagram(c)}
        ${tag}
        ${img}
      </div>
      <div class="sc-views">
        ${pdView(c.pd, c.pdc)}
        ${langView('v-cn', '中文', c.cn, `${c.audioBase || ''}audio/cn-${c.slug}.mp3`, `${c.audioBase || ''}audio/cn-${c.slug}-ex.mp3`)}
        ${langView('v-jp', '日本語', c.jp, `${c.audioBase || ''}audio/jp-${c.slug}.mp3`, `${c.audioBase || ''}audio/jp-${c.slug}-ex.mp3`)}
        ${wkView(c.wk, c.kanji)}
      </div>
    </div>`;
}

// ── Radical card (/kangxi/) — light on text, referent-image-forward ──
// Left: animated glyph (+ Kangxi №) over a readings block that toggles CN⇄JP
// (page-level, via toggleLang). Right: a scrollable referent-image gallery — the
// anchor that also absorbs cross-program label divergence (person/man). Images
// are a later content pass; until then the gallery shows a labelled empty state.
function readingLine(langCls, v, audioName) {
  return html`
      <div class="rk-lang ${langCls}">
        <div class="rk-nameline"><span class="sc-name">${v.name}</span>${
          v.reading ? html` <span class="sc-reading">${v.reading}</span>` : ''}${play(audioName)}</div>
        <div class="rk-gloss en">${v.gloss || ''}</div>
      </div>`;
}

function renderKangxiCard(c) {
  if (c.stub) return renderStub(c);
  const base = c.audioBase || '';
  const kx = c.kx ? html`<span class="sc-kx">${c.kx}</span>` : '';
  const imgs = (c.referents || []).flatMap(r =>
    (r.images || []).map(im => html`<img class="rk-ref" src="${im.src}" alt="${r.label}" title="${r.label} · ${im.credit || 'Wikimedia Commons'}${im.license ? ' (' + im.license + ')' : ''}">`));
  const gallery = imgs.length
    ? html`<div class="rk-gallery">${imgs}</div>`
    : html`<div class="rk-gallery rk-empty"><span>${c.cn.gloss || ''}</span></div>`;
  return html`
    <div class="scard rk-card">
      <div class="rk-left">
        <div class="sc-glyph">${kx}${diagram(c)}</div>
        <div class="rk-readings">
          ${readingLine('rk-cn', c.cn, `${base}audio/cn-${c.slug}.mp3`)}
          ${readingLine('rk-jp', c.jp, `${base}audio/jp-${c.slug}.mp3`)}
        </div>
      </div>
      <div class="rk-right">${gallery}</div>
    </div>`;
}

// Page-level CN⇄JP toggle for the radical layout (button lives in the page).
function toggleLang() {
  document.body.classList.toggle('show-jp');
  const b = document.getElementById('langBtn');
  if (b) b.textContent = document.body.classList.contains('show-jp') ? '中文' : '日本語';
}

function renderGroup(g) {
  const head = g.title
    ? html`<div class="sc-grouphead"><span class="sc-gtitle">${g.title}</span>${g.sub ? html`<span class="sc-gsub">${g.sub}</span>` : ''}</div>`
    : '';
  const cardFn = LAYOUT === 'radical' ? renderKangxiCard : renderCard;
  return html`<div class="sc-group">${head}${g.cards.map(cardFn)}</div>`;
}

// Data-driven stroke-order animation for character cards (`hw: true`).
// Self-hosted: lib in shared/vendor, per-char data in shared/hanzi-data (APL).
// Module pages live one level deep, so ../shared/ resolves for all of them.
function initHanzi() {
  if (typeof HanziWriter === 'undefined') return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const navy = getComputedStyle(document.documentElement)
    .getPropertyValue('--navy').trim() || '#1E2A4A';
  document.querySelectorAll('.sc-hw').forEach(el => {
    const w = HanziWriter.create(el, el.dataset.char, {
      width: 112, height: 112, padding: 12,
      strokeColor: navy, outlineColor: '#D8D2C4', showOutline: true,
      strokeAnimationSpeed: 1, delayBetweenStrokes: 240,
      charDataLoader: (c, onComplete) =>
        fetch(`../shared/hanzi-data/${c}.json`).then(r => r.json()).then(onComplete),
    });
    if (!reduce) w.loopCharacterAnimation();
  });
}

// Auto-load when a page provides <div id="cards" data-src>. Pages that reuse
// renderCard()/initHanzi() directly (e.g. /graph/) simply omit #cards.
const host = document.getElementById('cards');
if (host) {
  LAYOUT = host.dataset.layout || '';
  fetch(host.dataset.src)
    .then(r => r.json())
    .then(d => { host.innerHTML = d.groups.map(renderGroup).join(''); initHanzi(); });
}
