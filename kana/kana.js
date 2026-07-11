// Renders the kana mora board from kana/data.json (built by data/build-kana.py).
// Depends on shared/base.js for the `html` template + the .vplay audio handler.
// The board flips hiragana⇄katakana as the primary glyph via a body class.

const AUDIO = '/audio/kana/';   // content-keyed mora bank, voiced from the kana glyph

function toggleScript() {
  document.body.classList.toggle('show-kata');
  const btn = document.getElementById('scriptBtn');
  if (btn) btn.textContent = document.body.classList.contains('show-kata') ? 'ひらがな' : 'カタカナ';
}

function moraTile(c) {
  if (!c) return html`<div class="mora empty"></div>`;
  return html`
    <button class="mora vplay" data-src="${AUDIO}${c.romaji}.mp3" title="${c.romaji}">
      <span class="m-hira">${c.hira}</span>
      <span class="m-kata">${c.kata}</span>
      <span class="m-romaji">${c.romaji}</span>
    </button>`;
}

function gridSection(rows) {
  return html`<div class="kana-grid">${rows.map(row => html`
    <div class="kana-row">${row.map(moraTile)}</div>`)}`;
}

const SECTIONS = [
  ['gojuon', '五十音', 'gojūon', 'base'],
  ['dakuten', '濁音', 'dakuten ゛', 'voiced'],
  ['handakuten', '半濁音', 'handakuten ゜', 'p-sounds'],
  ['yoon', '拗音', 'yōon', 'glides'],
];

function render(data) {
  document.getElementById('board').innerHTML = html`${SECTIONS.map(([key, jp, roma, en]) => html`
    <div class="wrap kana-section">
      <div class="sec-label"><span class="en">${en}</span><span class="zh-alt">${roma}</span></div>
      <h2>${jp} <span class="sec-roma">${roma}</span></h2>
      <div class="sec-rule"></div>
      ${gridSection(data[key])}
    </div>`)}`;
}

fetch('data.json').then(r => r.json()).then(render);
