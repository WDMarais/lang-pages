// /glyph/ — single-endpoint DOSSIER. You give it one glyph; it gives you the view that
// glyph deserves. Deliberately NOT the graph/ladder projection: no tier index, no ego
// spiral, no browsing. One endpoint, everything the data layer knows about it, in the
// order you actually want it — what it looks like, what it's confused with, what it's
// made of, what it builds, what it means, and which assets exist.
//
// Addressable: /glyph/#己 — so a dossier is linkable, back/forward works, and the box is
// just another way to set the hash.

let G = null;

loadGraph().then(g => {
  G = g;
  window.addEventListener('hashchange', route);
  const box = document.getElementById('q');
  box.addEventListener('keydown', e => { if (e.key === 'Enter') { submit(box.value); } });
  document.getElementById('go').addEventListener('click', () => submit(box.value));
  document.getElementById('examples').addEventListener('click', e => {
    const b = e.target.closest('[data-goto]');
    if (b) { location.hash = encodeURIComponent(b.dataset.goto); }
  });
  route();
});

function submit(v) {
  const q = (v || '').trim();
  if (q) { location.hash = encodeURIComponent(q); }
}

// go(target) — target is a node id (g:己 / w:可不@cn) or a bare glyph.
function go(target) {
  location.hash = encodeURIComponent(target);
}

function route() {
  const raw = decodeURIComponent((location.hash || '').replace(/^#/, '')).trim();
  const box = document.getElementById('q');
  if (!raw) { renderEmpty(); return; }
  box.value = raw;
  render(resolve(raw));
}

// ── resolution ──────────────────────────────────────────────────────────────────
// Generous on input: a node id, a bare glyph, or a word surface. Reports honestly
// which state we landed in — real / frontier / ambiguous / absent — because "absent"
// is a real and useful answer for an authoring probe, not an error.
//
// A bare SURFACE is not an identity: 大人 is BOTH w:大人@jp (おとな) and w:大人@cn
// (dàrén) — the homograph fork the word-node ids exist to keep apart. Silently
// preferring one audience would hide the other from anyone typing the surface. So we
// gather every candidate and, if more than one survives, we ASK rather than guess.
// Stated generally (not as an audience special-case) it also covers the collision
// waiting to happen: a one-char word that shares its surface with a glyph node.
function candidates(q) {
  if (G.byId[q]) { return [G.byId[q]]; }               // an explicit id is already an identity
  const out = [];
  if (G.byGlyph[q]) { out.push(G.byGlyph[q]); }        // bare glyph → g:X
  for (const aud of ['cn', 'jp']) {                // surface → w:X@aud, every audience
    const n = G.byId[`w:${q}@${aud}`];
    if (n) { out.push(n); }
  }
  return out;
}

function resolve(q) {
  const cs = candidates(q);
  if (cs.length === 1) { return { state: nodeState(cs[0]), node: cs[0], id: cs[0].id }; }
  if (cs.length > 1) { return { state: 'ambiguous', q, options: cs }; }

  // nothing carries it — offer its constituent glyphs, which usually DO exist
  const glyphs = [...q].filter(c => G.byGlyph[c]);
  return { state: 'absent', q, glyphs };
}
function nodeState(n) {
  if (n.kind === 'glyph') { return n.frontier ? 'frontier' : 'real'; }
  return 'real';
}

// ── render ──────────────────────────────────────────────────────────────────────
function renderEmpty() {
  document.getElementById('dossier').innerHTML = html`
    <div class="gl-empty">
      <div class="gl-empty-mark">字</div>
      <p class="en">Enter a single glyph — or a word surface — to open its dossier.</p>
      <div class="gl-try en">try:
        ${['己', '已', '巳', '人', '入', '可不', '木'].map(g =>
          html` <button class="gl-chip" data-goto="${g}">${g}</button>`)}
      </div>
    </div>`;
  document.getElementById('examples').innerHTML = '';
}

const AUD = { cn: { zh: '中文', en: 'Chinese' }, jp: { zh: '日本語', en: 'Japanese' } };
const KIND = { glyph: { zh: '字', en: 'glyph' }, word: { zh: '词', en: 'word' } };

// One surface, several nodes. Show them ALL and make the user pick — each choice
// navigates to the node's explicit id, so the resulting URL is unambiguous and
// linkable (#w:大人@jp), and the fork is visible rather than silently resolved.
function renderAmbiguous(r) {
  return html`
    <div class="gl-ambig">
      <div class="gl-ambig-head">
        <div class="gl-ambig-glyph">${r.q}</div>
        <div>
          <div class="gl-state ambiguous">歧义<span class="en"> · ${r.options.length} nodes share this surface</span></div>
          <p class="en">A surface isn't an identity — pick the one you mean.</p>
        </div>
      </div>
      <div class="gl-ambig-opts">
        ${r.options.map(n => {
          const isWord = n.kind === 'word';
          const aud = isWord ? AUD[n.audience] : null;
          const k = KIND[n.kind] || { zh: '', en: n.kind };
          const f = isWord ? null : gdFacts(G, n.glyph);
          const reading = isWord ? (n.reading || '') : [f.py, f.kana].filter(Boolean).join(' · ');
          const gloss = isWord ? (n.gloss || '') : f.gloss;
          return html`
            <button class="gl-ambig-opt" data-goto="${n.id}">
              <div class="gl-ao-tags">
                <span class="gl-ao-kind">${k.zh} <span class="en">${k.en}</span></span>
                ${aud ? html`<span class="gl-ao-aud gl-ao-${n.audience}">${aud.zh} <span class="en">${aud.en}</span></span>` : ''}
              </div>
              <div class="gl-ao-surface">${n.glyph || ''}</div>
              ${reading ? html`<div class="gl-ao-reading">${reading}</div>` : ''}
              ${gloss ? html`<div class="gl-ao-gloss en">${gloss}</div>` : ''}
              <div class="gl-ao-id en">${n.id}</div>
            </button>`;
        })}
      </div>
    </div>`;
}

function render(r) {
  const host = document.getElementById('dossier');

  if (r.state === 'ambiguous') {
    host.innerHTML = renderAmbiguous(r);
    document.getElementById('examples').innerHTML = '';
    bindGoto(host);
    return;
  }

  if (r.state === 'absent') {
    host.innerHTML = html`
      <div class="gl-absent">
        <div class="gl-absent-glyph">${r.q}</div>
        <div class="gl-state absent">缺<span class="en"> · absent from the graph</span></div>
        <p class="en">No node carries this. It isn't authored, and nothing composes it.</p>
        ${r.glyphs && r.glyphs.length ? html`
          <div class="gl-try en">its glyphs are in the graph:
            ${r.glyphs.map(g => html` <button class="gl-chip" data-goto="${g}">${g}</button>`)}
          </div>` : ''}
      </div>`;
    bindGoto(host);
    return;
  }

  const n = r.node;
  const isWord = n.kind === 'word';
  const surface = n.glyph || '';

  host.innerHTML = html`
    ${hero(n, r, isWord, surface)}
    ${renderRefBay(G, n)}
    ${renderConfusable(G, r.id)}
    ${isWord ? wordBody(n) : glyphBody(n, surface)}
    ${assets(n, r, isWord)}`;

  // the full four-view card, for a real glyph only (cards3 needs both bindings)
  if (!isWord && r.state === 'real') {
    document.getElementById('examples').innerHTML = renderCard(cardFromNode(G, n));
  } else {
    document.getElementById('examples').innerHTML = '';
  }
  bindConfusable(host, go);
  bindGoto(host);
  initHanzi();
}

function hero(n, r, isWord, surface) {
  const f = isWord ? null : gdFacts(G, surface);
  const reading = isWord ? (n.reading || '') : [f.py, f.kana].filter(Boolean).join(' · ');
  const gloss = isWord ? (n.gloss || '') : f.gloss;
  const animated = !isWord && n.media && n.media.animated;
  const tier = isWord ? 'word · 词' : (n.frontier ? 'frontier · 前沿' : `${n.tier} · ${({ stroke: '笔画', component: '部件', char: '字' })[n.tier] || ''}`);
  // a word plays its whole-word clip from its own bank: JP romaji or CN pinyin base
  const wordSrc = !isWord ? null
    : n.jpAudioKey ? `/audio/jp/${n.jpAudioKey}.mp3`
    : n.cnAudioKey ? `/audio/cn/${n.cnAudioKey}.mp3` : null;

  return html`
    <div class="gl-hero">
      <div class="gl-hero-art">
        ${animated ? html`<div class="gl-hw sc-hw" data-char="${surface}"></div>`
             : html`<div class="gl-hero-glyph${[...surface].length > 1 ? ' multi' : ''}">${surface}</div>`}
      </div>
      <div class="gl-hero-facts">
        <div class="gl-state ${r.state}">${r.state === 'frontier'
          ? html`前沿<span class="en"> · frontier</span>`
          : html`在图<span class="en"> · in graph</span>`}</div>
        <div class="gl-tier en">${tier}</div>
        ${reading ? html`<div class="gl-reading">${reading}${wordSrc
          ? html`<button class="vplay sc-play" style="margin-left:.5rem" data-src="${wordSrc}" aria-label="play">▶</button>`
          : ''}</div>` : ''}
        ${gloss ? html`<div class="gl-gloss en">${gloss}</div>` : ''}
        <div class="gl-id en">${r.id}</div>
      </div>
    </div>`;
}

// The referent — the thing the glyph POINTS AT — is rendered above by the shared 义
// bay (renderRefBay): image + label + per-sense readings, the concrete-referent anchor
// ("a picture-and-sound of an elephant IS the referent", not a gloss). It used to live
// here as a plain 所指 text row; it now shares one surface with /graph/'s #referent bay.
function glyphBody(n, surface) {
  const P = G.parts[surface] || [];
  const A = G.appears[surface] || [];
  const vars = n.variants || [];

  return html`
    <div class="gl-rels">
      ${relRow('部件', 'built from', P, 'nothing decomposes it — it is a primitive here')}
      ${relRow('出现于', 'appears in', A, 'nothing in the graph is built from it yet')}
      ${vars.length ? relRow('异体', 'variant forms', vars, '') : ''}
    </div>`;
}

function wordBody(n) {
  const parts = [...(n.glyph || '')].filter(c => G.byGlyph[c]);
  return html`
    <div class="gl-rels">
      ${relRow('部件', 'written with', parts, '')}
      ${n.okurigana ? html`
        <div class="gl-rel">
          <div class="gl-rel-label"><span>送假名</span><span class="en">okurigana</span></div>
          <div class="gl-rel-body"><span class="gl-ref">${n.okurigana}</span></div>
        </div>` : ''}
    </div>`;
}

function relRow(zh, en, glyphs, emptyNote) {
  if (!glyphs.length && !emptyNote) { return ''; }
  return html`
    <div class="gl-rel">
      <div class="gl-rel-label"><span>${zh}</span><span class="en">${en}</span></div>
      <div class="gl-rel-body">
        ${glyphs.length
          ? glyphs.map(g => html`<button class="gl-chip${G.byGlyph[g] && G.byGlyph[g].frontier ? ' frontier' : ''}" data-goto="${g}">${g}</button>`)
          : html`<span class="gl-none en">${emptyNote}</span>`}
      </div>
    </div>`;
}

// assets: what actually exists for this node. An authoring probe wants to see the
// GAPS (no stroke data, no audio) as plainly as the hits.
function assets(n, r, isWord) {
  const rows = [];
  if (!isWord) {
    rows.push(['stroke data', n.media && n.media.animated ? 'hanzi-writer' : null]);
    rows.push(['image', n.media && n.media.image ? n.media.image : null]);
    rows.push(['cn audio', n.cnAudioKey ? `/audio/cn/${n.cnAudioKey}.mp3` : null]);
    rows.push(['jp audio', n.jpAudioKey ? `/audio/jp/${n.jpAudioKey}.mp3` : null]);
  } else {
    rows.push(['reading', n.reading || null]);
    if (n.audience === 'jp') { rows.push(['jp audio', n.jpAudioKey ? `/audio/jp/${n.jpAudioKey}.mp3` : null]); }
    if (n.audience === 'cn') { rows.push(['cn audio', n.cnAudioKey ? `/audio/cn/${n.cnAudioKey}.mp3` : null]); }
  }
  return html`
    <div class="gl-assets">
      <div class="gl-assets-label en">assets</div>
      <div class="gl-assets-grid">
        ${rows.map(([k, v]) => html`
          <div class="gl-asset${v ? '' : ' missing'}">
            <span class="gl-asset-k en">${k}</span>
            <span class="gl-asset-v en">${v || '—'}</span>
          </div>`)}
      </div>
    </div>`;
}

function bindGoto(root) {
  root.querySelectorAll('[data-goto]').forEach(el => {
    if (el.classList.contains('cf-member')) { return; }   // confusable panel binds its own
    el.addEventListener('click', () => go(el.dataset.goto));
  });
}
