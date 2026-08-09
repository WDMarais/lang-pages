'use strict';
// /numerals/ — the quantity behind the character.
//   · units 1-10  : glyph + readings + N-dot SVG + 正 tally-mark
//   · powers      : 十百千万億 with the 万-grouping (myriad) system
//   · builder     : a number → its glyph decomposition (the GENERATIVE rule made
//                   tangible — a small basis + one positional rule regenerates the
//                   whole number line; the same function is the p-i-t generator).

let DATA = null;   // data/numerals.json
let ZHENG = null;  // 正 stroke paths (for the tally)

// ── quantity referents (units 1-10) ─────────────────────────────────────────
function dots(v) {
  let out = '';
  for (let left = v; left > 0; ) {
    const n = Math.min(5, left); left -= n;
    let cells = '';
    for (let i = 0; i < 5; i++) { cells += i < n ? '<span class="dot"></span>' : '<span></span>'; }
    out += `<div class="dot-cluster">${cells}</div>`;
  }
  return `<div class="dots">${out}</div>`;
}
// one 正 mark: `lit` strokes inked, the rest ghosted so a partial reads as "in progress".
function mark(lit, kind) {
  const paths = ZHENG.strokes.map((d, i) =>
    `<path class="${i < lit ? 'lit' : 'gh'}" d="${d}"/>`).join('');
  return `<svg viewBox="0 0 1024 1024" class="mark ${kind}"><g transform="scale(1,-1) translate(0,-900)">${paths}</g></svg>`;
}
function tally(v) {
  const full = Math.floor(v / 5), rem = v % 5;
  let out = '';
  for (let i = 0; i < full; i++) { out += mark(5, 'full'); }
  if (rem > 0) { out += mark(rem, 'part'); }
  return `<div class="tally">${out}</div>`;
}
function unitCard(n) {
  return `<div class="ncard">
    <div class="nc-top"><span class="glyph">${n.glyph}</span><span class="val">${n.value}</span></div>
    <div class="reading"><b>${n.cn}</b><span class="jp">${n.jp}</span><span class="en">${n.en}</span></div>
    <div class="ref-label">dots</div>${dots(n.value)}
    <div class="ref-label">正 tally</div>${tally(n.value)}
  </div>`;
}

// ── powers / the myriad system ──────────────────────────────────────────────
function powerCard(p) {
  const compose = p.compose === '—' ? '<span class="pc-atom">atomic place</span>'
                                    : `<span class="pc-compose">${p.compose}</span>`;
  return `<div class="pcard">
    <div class="nc-top"><span class="glyph">${p.glyph}</span><span class="val">10<sup>${p.pow}</sup></span></div>
    <div class="reading"><b>${p.cn}</b><span class="jp">${p.jp}</span><span class="en">${p.en}</span></div>
    <div class="pc-grouped">${p.grouped}</div>
    <div class="pc-rule">${compose}</div>
  </div>`;
}

// ── the builder: number → 汉字 (the positional rule) ─────────────────────────
const DIGIT = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
const SMALL  = ['', '十', '百', '千'];   // 10^0 … 10^3 within a myriad group
const BIG    = ['', '万', '億'];          // group 0,1,2 → 10^0, 10^4, 10^8

// render one 0..9999 group → { chars, terms }. terms feed the visual tree.
function groupChars(g) {
  const digits = [Math.floor(g / 1000) % 10, Math.floor(g / 100) % 10, Math.floor(g / 10) % 10, g % 10];
  let chars = '', terms = [], started = false, zeroPending = false;
  for (let i = 0; i < 4; i++) {
    const d = digits[i], place = 3 - i;
    if (d === 0) { if (started) { zeroPending = true; } continue; }
    if (zeroPending) { chars += '零'; terms.push({ zero: true }); zeroPending = false; }
    chars += DIGIT[d] + SMALL[place];
    terms.push({ coef: DIGIT[d], place: SMALL[place], pv: Math.pow(10, place) });
    started = true;
  }
  return { chars, terms };
}

// decompose n (0 … 10^8) into its characters + a flat term list for the tree.
function decompose(n) {
  if (n === 0) { return { value: 0, chars: '零', terms: [{ coef: '零', place: '', pv: 1 }] }; }
  const groups = [];               // groups[0] = lowest 4 digits
  for (let x = n; x > 0; x = Math.floor(x / 10000)) { groups.push(x % 10000); }
  let chars = '', terms = [];
  for (let gi = groups.length - 1; gi >= 0; gi--) {
    const g = groups[gi];
    if (g === 0) {                 // empty group — maybe a 零 bridge to lower groups
      if (gi > 0 && groups.slice(0, gi).some(v => v > 0) && chars && !chars.endsWith('零')) {
        chars += '零'; terms.push({ zero: true });
      }
      continue;
    }
    if (chars && g < 1000 && !chars.endsWith('零')) { chars += '零'; terms.push({ zero: true }); }
    const gc = groupChars(g);
    chars += gc.chars; terms.push(...gc.terms);
    if (gi > 0) { chars += BIG[gi]; terms.push({ coef: '', place: BIG[gi], pv: Math.pow(10, 4 * gi), marker: true }); }
  }
  if (chars.startsWith('一十')) { chars = chars.slice(1); }   // 10-19: 一十X → 十X
  return { value: n, chars, terms };
}

// group digits by 4 (myriad), not 3 — 12345678 → 1234,5678
function groupBy4(n) {
  const s = String(n); let out = '';
  for (let i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 4 === 0) { out += ','; }
    out += s[i];
  }
  return out;
}

function renderBuild(n) {
  const out = document.getElementById('build-out');
  if (!(n >= 0 && n <= 100000000)) {
    out.innerHTML = `<div class="build-hint">enter a whole number from 0 to 100000000</div>`;
    return;
  }
  const d = decompose(n);
  // the assembled 汉字
  let chips = '';
  for (const t of d.terms) {
    if (t.zero)      { chips += `<div class="term zero"><span class="t-glyph">零</span><span class="t-pv">skip</span></div>`; }
    else if (t.marker) { chips += `<div class="term marker"><span class="t-glyph">${t.place}</span><span class="t-pv">×${t.pv.toLocaleString()}</span></div>`; }
    else {
      const pv = t.pv === 1 ? 'units' : `×${t.pv.toLocaleString()}`;
      chips += `<div class="term"><span class="t-glyph">${t.coef}${t.place}</span><span class="t-pv">${pv}</span></div>`;
    }
  }
  // 两 note: a bare 2 (二) before 百/千/万 is colloquially 两
  const twoNote = /二[百千万]/.test(d.chars)
    ? `<div class="build-note"><span class="en">colloquial: </span>二 before 百/千/万 is usually <b>两</b> — ${d.chars.replace(/二([百千万])/g, '两$1')}</div>`
    : '';
  out.innerHTML = `
    <div class="build-chars">${d.chars}</div>
    <div class="build-digits">${groupBy4(n)}</div>
    <div class="build-tree">${chips}</div>
    ${twoNote}`;
}

function wireBuilder() {
  const input = document.getElementById('build-input');
  input.addEventListener('input', () => renderBuild(parseInt(input.value, 10)));
  document.querySelectorAll('.preset').forEach(b =>
    b.addEventListener('click', () => { input.value = b.dataset.n; renderBuild(parseInt(b.dataset.n, 10)); }));
  renderBuild(parseInt(input.value, 10));
}

// ── boot ────────────────────────────────────────────────────────────────────
Promise.all([
  fetch('../data/numerals.json').then(r => r.json()),
  fetch('../shared/hanzi-data/正.json').then(r => r.json()),
]).then(([data, zheng]) => {
  DATA = data; ZHENG = zheng;
  document.getElementById('units-grid').innerHTML  = DATA.units.map(unitCard).join('');
  document.getElementById('powers-grid').innerHTML = DATA.powers.map(powerCard).join('');
  wireBuilder();
}).catch(e => {
  document.getElementById('units-grid').textContent = 'failed to load numerals data: ' + e;
});
