// Renders the Bopomofo chart + syllable bank from zhuyin/data.json (a projection of
// the symbol store, built by data/build-phonetics.py). Depends on shared/base.js for
// the `html` tagged template and the .vplay audio click handler.

const AUDIO = '../audio/cn/';   // content-keyed syllable bank, shared by every page + card

// Pinyin initial of a syllable base ('qian' → 'q', 'zhi' → 'zh', 'er' → '∅') for
// grouping the bank into syllabary rows. Zero-initial (a/e/o/y/w) groups under '∅'.
const INITIALS = ['zh','ch','sh','b','p','m','f','d','t','n','l','g','k','h','j','q','x','r','z','c','s'];
function initialOf(base) {
  for (const i of INITIALS) if (base.startsWith(i)) return i;
  return '∅';
}

function syllableTile(e) {
  const rep = e.glyphs[0];
  const more = e.glyphs.length > 1 ? html`<span class="syl-more">+${e.glyphs.length - 1}</span>` : '';
  return html`
    <button class="syl vplay" data-src="${AUDIO}${e.key}.mp3" title="${e.glyphs.map(g => g.glyph).join(' ')}">
      <span class="syl-zh">${e.zhuyin}</span>
      <span class="syl-py">${e.pinyin}</span>
      <span class="syl-glyph">${rep.glyph}${more}</span>
    </button>`;
}

function render(data) {
  // Bopomofo chart
  document.getElementById('chart').innerHTML = html`${Object.entries(data.chart).map(([group, rows]) => html`
    <div class="chart-group">
      <div class="chart-label">${group}</div>
      <div class="chart-row">${rows.map(r => html`
        <div class="bpmf"><span class="bpmf-zh">${r.zhuyin}</span><span class="bpmf-py">${r.pinyin}</span></div>`)}</div>
    </div>`)}`;

  // Syllable bank, grouped by initial in canonical order
  const groups = new Map();
  for (const e of Object.values(data.syllables)) {
    const i = initialOf(e.base);
    if (!groups.has(i)) groups.set(i, []);
    groups.get(i).push(e);
  }
  const order = [...INITIALS, '∅'].filter(i => groups.has(i));
  document.getElementById('bank').innerHTML = html`${order.map(i => html`
    <div class="bank-group">
      <div class="bank-initial">${i}</div>
      <div class="bank-row">${groups.get(i).sort((a, b) => a.key.localeCompare(b.key)).map(syllableTile)}</div>
    </div>`)}`;
}

fetch('data.json').then(r => r.json()).then(render);
