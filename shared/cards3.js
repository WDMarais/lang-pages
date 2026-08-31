// Shared four-view (Pandanese · 中文 · 日本語 · Wanikani) card renderer.
// Programs bookend the two real-language views: Pandanese (CN-side) left,
// Wanikani (JP-side) right, with 中文 · 日本語 centered for direct comparison.
// A page supplies its data file via <div id="cards" data-src="...json">.
// JSON shape: { groups: [ { title?, sub?, cards: [...] } ] }
// A card animates its stroke order via HanziWriter when it sets `animated: true`;
// otherwise the diagram is just the crisp Kai glyph — for deferred / un-tuned cards.

// Page-level layout mode, set from <div id="cards" data-layout="…">. Default ''
// = the four-column comparison card; 'radical' = the lighter /kangxi/ card.
let LAYOUT = '';

// Audio resolves to the shared, content-keyed banks that build-pages stamped onto
// the card: /audio/cn/<key>.mp3 (千→qian1, stroke names→hengzhegou) and
// /audio/jp/<key>.mp3 (セン→sen). Keyed by SOUND, not the glyph — so every reading
// qiān shares one clip and no per-card slug is needed. A readingless view carries no
// key; its play button isn't rendered (langView gates on the reading).
const CN_BANK = '/audio/cn/';
const JP_BANK = '/audio/jp/';
function cnSrc(c, ex) {
  const key = ex ? c.cnExAudioKey : c.cnAudioKey;
  return key ? `${CN_BANK}${key}.mp3` : '';
}
function jpSrc(c, ex) {
  const key = ex ? c.jpExAudioKey : c.jpAudioKey;
  return key ? `${JP_BANK}${key}.mp3` : '';
}

function diagram(c) {
  // Character cards opt into data-driven stroke-order animation (HanziWriter);
  // init happens after innerHTML in initHanzi(). Un-tuned cards degrade to the glyph.
  if (c.animated) { return html`<div class="sc-hw" data-char="${c.glyph}"></div>`; }
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
        <div class="sc-nameline">${name}${v.reading ? play(audioName) : ''}</div>
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
  if (on.length) { labels.push(k.on ? '音読み' : '訓読み'); }
  if (kun.length) { labels.push('訓読み'); }
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

// script chip: names the Han form(s) the card glyph is NOT (docs/traditional-
// script.md). `keyed` says which axis the glyph sits on; we surface the other
// side(s), each labelled 简 or 繁 with its sense (个→個/箇, 后→後/后) on hover.
// same → a faint 繁=简 affirming verified no-divergence (distinct from an
// unclassified glyph, which shows nothing). shinjitai-keyed (円) names both.
const SCRIPT_SLOTS = [['simplified', '简'], ['traditional', '繁']];
function scriptChip(s) {
  if (!s) { return ''; }
  if (s.same) {
    return html`<span class="sc-trad sc-trad-same" title="繁简同形 · simplified = traditional">繁=简</span>`;
  }
  const segs = [];
  for (const [key, lbl] of SCRIPT_SLOTS) {
    const form = s[key];
    if (!Array.isArray(form) || !form.length) { continue; }
    const forms = form.map(e => e.when
      ? html`<span class="sc-trad-g" title="${e.when}">${e.glyph}</span>`
      : html`<span class="sc-trad-g">${e.glyph}</span>`);
    segs.push(html`<span class="sc-trad-seg"><span class="sc-trad-lbl">${lbl}</span>${forms}</span>`);
  }
  if (!segs.length) { return ''; }
  return html`<span class="sc-trad">${segs}</span>`;
}

// ── senses dossier (polysemy / polyphony) ──
// A glyph's EXTRA senses ride on the graph node as `senses` (build-graph stamps
// them from the authored senses[] via the coupling rule; see docs/sense-model.md).
// Sense 0 is the primary card above — so when the glyph carries more, this panel
// ── 义 bay: the concrete-referent anchor, shared by /graph/ and /glyph/ ──────────
// One block per SENSE — the referent the glyph POINTS AT (image + label), plus the
// sound(s) that sense takes per language. This is the "a picture-and-sound of an
// elephant IS the referent" panel, deliberately NOT a gloss restatement, and it is
// the single home for the whole sense model: polysemy reads as ① life ② raw down
// the blocks, polyphony as せい vs なま across a block's readings. Lives here (both
// pages load cards3.js) so the graph #referent bay and the glyph dossier can't drift.
// Image is the glyph's own art for now (referent-media is deferred), so polysemous
// senses share it until a referent carries its own image.
function refReadingChips(rows) {
  const live = rows.filter(r => r.reading);
  if (!live.length) { return ''; }
  return html`<div class="ref-rds">${live.map(r => html`
        <span class="ref-lang ${r.cls}"><span class="ref-tag">${r.tag}</span><span class="ref-rd">${r.reading}</span>${r.src ? play(r.src) : ''}</span>`)}</div>`;
}
// resolve every sense of a node into {label, readings[], img} anchor blocks.
function refSenses(G, node) {
  const img = (node.media && node.media.image) || '';
  if (node.kind === 'word') {
    const src = node.jpAudioKey ? `${JP_BANK}${node.jpAudioKey}.mp3`
      : node.cnAudioKey ? `${CN_BANK}${node.cnAudioKey}.mp3` : '';
    const tag = node.audience === 'cn' ? '中' : '日';
    const cls = node.audience === 'cn' ? 'ref-cn' : 'ref-jp';
    const label = (G.denotesOf[node.id] && G.refLabel[G.denotesOf[node.id]]) || node.gloss || '';
    return label ? [{ label, img, readings: [{ cls, tag, reading: node.reading || '', src }] }] : [];
  }
  const cn = G.bindById[`b:${node.glyph}@cn`], jp = G.bindById[`b:${node.glyph}@jp`];
  // sense 0 — the readings block; label handle is the referent, falling back to gloss.
  const primary = {
    label: (G.denotesOf[node.glyph] && G.refLabel[G.denotesOf[node.glyph]])
      || (cn && cn.gloss) || (jp && jp.gloss) || '',
    img,
    readings: [
      { cls: 'ref-cn', tag: '中', reading: (cn && cn.readings[0]) || '', src: node.cnAudioKey ? `${CN_BANK}${node.cnAudioKey}.mp3` : '' },
      { cls: 'ref-jp', tag: '日', reading: (jp && jp.readings[0]) || '', src: node.jpAudioKey ? `${JP_BANK}${node.jpAudioKey}.mp3` : '' },
    ],
  };
  const extras = (node.senses || []).map(s => ({
    label: (s.denotes && G.refLabel[`r:${s.denotes}`]) || s.gloss || '',
    img,
    readings: [
      { cls: 'ref-cn', tag: '中', reading: ((s.cn || {}).readings || [])[0] || '', src: ((s.cn || {}).audioKeys || [])[0] ? `${CN_BANK}${s.cn.audioKeys[0]}.mp3` : '' },
      { cls: 'ref-jp', tag: '日', reading: ((s.jp || {}).readings || [])[0] || '', src: ((s.jp || {}).audioKeys || [])[0] ? `${JP_BANK}${s.jp.audioKeys[0]}.mp3` : '' },
    ],
  }));
  return [primary, ...extras];
}
function renderRefBay(G, node) {
  const senses = refSenses(G, node).filter(s => s.label);
  if (!senses.length) { return ''; }
  const many = senses.length > 1;
  // The referent leads each block — its label now, its image when one lands — so the
  // eye catches the MEANING (life vs raw), not the glyph (already huge in the card).
  const blocks = senses.map((s, i) => html`
        <div class="ref-sense">
          ${many ? html`<span class="ref-num">${i + 1}</span>` : ''}
          ${s.img ? html`<img class="ref-img" src="${s.img}" alt="">` : ''}
          <div class="ref-info">
            <div class="ref-label en">${s.label}</div>
            ${refReadingChips(s.readings)}
          </div>
        </div>`);
  return html`
      <div class="ref-bay${many ? ' ref-poly' : ''}">
        <div class="ref-head"><span class="ref-mark">义</span><span class="ref-cap en">${many ? `referent · ${senses.length} senses` : 'referent'}</span></div>
        ${blocks}
      </div>`;
}

function renderCard(c) {
  if (c.stub) { return renderStub(c); }
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
        ${scriptChip(c.script)}
        ${img}
      </div>
      <div class="sc-views">
        ${pdView(c.pd, c.pdc)}
        ${langView('v-cn', '中文', c.cn, cnSrc(c, false), cnSrc(c, true))}
        ${langView('v-jp', '日本語', c.jp, jpSrc(c, false), jpSrc(c, true))}
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
          v.reading ? html` <span class="sc-reading">${v.reading}</span>` : ''}${v.reading ? play(audioName) : ''}</div>
        <div class="rk-gloss en">${v.gloss || ''}</div>
      </div>`;
}

// Flatten a card's referents to a single image list (each tagged with its label).
function refImages(referents) {
  return (referents || []).flatMap(r =>
    (r.images || []).map(im => ({ ...im, label: r.label })));
}

const refTitle = im => `${im.label} · ${im.credit || 'Wikimedia Commons'}${im.license ? ' (' + im.license + ')' : ''}`;

// Hero collage: show up to 4 available referents at once — the CC0 schematic (the
// controlled anchor) alongside real photos. Layout is count-aware (1 fills, 2
// split, 3 banner+pair, 4 quad); SVGs `contain` so the diagram never crops,
// photos `cover`. Fewer referents → fewer cells, no gaps.
function refCollage(referents) {
  const imgs = refImages(referents).slice(0, 4);
  if (!imgs.length) { return null; }
  const cells = imgs.map(im => {
    const svg = /\.svg(\?|$)/.test(im.src);
    return html`<img class="rk-cell ${svg ? 'rk-cell-svg' : 'rk-cell-photo'}" src="${im.src}" alt="${im.label}" title="${refTitle(im)}">`;
  });
  return html`<div class="rk-hero rk-hero-n${imgs.length}">${cells}</div>`;
}

// /kangxi/ tile. Two states along one gradient: a card WITH referents leads with
// a collage hero + a compact glyph below; a card with NONE yet is glyph-forward —
// the animated glyph IS the hero (no dead dashed box), flipping to collage as
// images get added. The full gallery rides a hidden detail block for Phase 2.
function renderKangxiCard(c) {
  if (c.stub) { return renderStub(c); }
  const kx = c.kx ? html`<span class="sc-kx">${c.kx}</span>` : '';
  const readings = html`
        <div class="rk-readings">
          ${readingLine('rk-cn', c.cn, cnSrc(c, false))}
          ${readingLine('rk-jp', c.jp, jpSrc(c, false))}
        </div>`;
  const collage = refCollage(c.referents);
  if (!collage) {
    return html`
    <div class="scard rk-card rk-card-glyph">
      <div class="rk-herowrap">${kx}
        <div class="rk-hero rk-hero-glyph"><div class="rk-heroglyph">${diagram(c)}</div></div>
      </div>
      <div class="rk-cap">${readings}</div>
    </div>`;
  }
  const imgs = refImages(c.referents).map(im =>
    html`<img class="rk-ref" src="${im.src}" alt="${im.label}" title="${refTitle(im)}">`);
  return html`
    <div class="scard rk-card">
      <div class="rk-herowrap">${kx}${collage}</div>
      <div class="rk-cap">
        <div class="rk-capglyph">${diagram(c)}</div>
        ${readings}
      </div>
      <div class="rk-detail" hidden><div class="rk-gallery">${imgs}</div></div>
    </div>`;
}

// Page-level CN⇄JP toggle for the radical layout (button lives in the page).
function toggleLang() {
  document.body.classList.toggle('show-jp');
  const b = document.getElementById('langBtn');
  if (b) { b.textContent = document.body.classList.contains('show-jp') ? '中文' : '日本語'; }
}

function renderGroup(g) {
  const head = g.title
    ? html`<div class="sc-grouphead"><span class="sc-gtitle">${g.title}</span>${g.sub ? html`<span class="sc-gsub">${g.sub}</span>` : ''}</div>`
    : '';
  // /kangxi/ lays its tiles out as a grid ladder; the comparison page stacks rows.
  if (LAYOUT === 'radical') {
    return html`<div class="sc-group">${head}<div class="rk-grid">${g.cards.map(renderKangxiCard)}</div></div>`;
  }
  return html`<div class="sc-group">${head}${g.cards.map(renderCard)}</div>`;
}

// The one HanziWriter.create call for the site: colours, speed, and the self-hosted
// APL data loader in ONE place, so the grid lifecycle (initHanzi) and the JP focus
// pane (cardsJP.jpFocusHanzi) can't drift on options — they were copy-pasted into two
// files, which is where the /jp/ writer leak was born. `sz` sizes the SVG; `opts`
// overrides per-caller (the focus pane pins its own padding). Callers own the loop and
// (for the grid) the IntersectionObserver; this owns only the create contract.
function hzCreate(el, char, sz, opts) {
  const navy = getComputedStyle(document.documentElement)
    .getPropertyValue('--navy').trim() || '#1E2A4A';
  return HanziWriter.create(el, char, {
    width: sz, height: sz, padding: sz * 0.09,
    strokeColor: navy, outlineColor: '#D8D2C4', showOutline: true,
    strokeAnimationSpeed: 1, delayBetweenStrokes: 240,
    charDataLoader: (c, onComplete) =>
      fetch(`../shared/hanzi-data/${c}.json`).then(r => r.json()).then(onComplete),
    ...(opts || {}),
  });
}

// Data-driven stroke-order animation for character cards (`animated: true`).
// Self-hosted: lib in shared/vendor, per-char data in shared/hanzi-data (APL).
// Module pages live one level deep, so ../shared/ resolves for all of them.
function initHanzi() {
  if (typeof HanziWriter === 'undefined') { return; }
  const nodes = document.querySelectorAll('.sc-hw');
  if (!nodes.length) { return; }
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const writers = new Map();
  const build = (el) => {
    // /kangxi/ tiles get a generous caption glyph; HanziWriter sizes the SVG inline
    // (beating CSS), so the size must be set here, not in the stylesheet.
    // .cf-hw = a confusable member tile, .gl-hw = the /glyph/ dossier hero — both want
    // to be big enough that a stroke-level difference (己/已/巳) is actually legible.
    const sz = el.closest('.rk-heroglyph') ? 200
             : el.classList.contains('gl-hw') ? 148
             : el.classList.contains('cf-hw') ? 132
             : el.closest('.rk-capglyph') ? 104 : 112;
    const w = hzCreate(el, el.dataset.char, sz);
    writers.set(el, w);
    if (!reduce) { w.loopCharacterAnimation(); }
    return w;
  };
  // HanziWriter loops each glyph on its own rAF with NO offscreen culling, so the
  // 214-tile grid would run every animation at once and swamp the main thread. Gate
  // to the viewport: build lazily on approach, pause on exit, resume on return —
  // active loops stay bounded to what's actually visible.
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      const w = writers.get(e.target);
      if (e.isIntersecting) {
        if (!w) { build(e.target); }
        else if (!reduce) { w.resumeAnimation(); }
      } else if (w && !reduce) {
        w.pauseAnimation();
      }
    });
  }, { rootMargin: '300px 0px' });
  nodes.forEach(el => io.observe(el));
}

// Auto-load when a page provides <div id="cards" data-src>. Pages that reuse
// renderCard()/initHanzi() directly (e.g. /graph/) simply omit #cards.
const host = document.getElementById('cards');
if (host) {
  LAYOUT = host.dataset.layout || '';
  if (LAYOUT === 'radical') { host.classList.add('rk-host'); }  // break the tile grid out wider
  fetch(host.dataset.src)
    .then(r => r.json())
    .then(d => { host.innerHTML = d.groups.map(renderGroup).join(''); initHanzi(); });
}
