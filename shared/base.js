// ── html: escaping tagged-template ────────────────
// Interpolations are escaped by default, so data (readings, glosses, names)
// can't inject markup. Values already built with html`` pass through unescaped;
// arrays are flattened and joined; wrap trusted raw markup (e.g. inline SVG icon
// paths) in raw(). No build step — this is the whole templating layer.
class Html { constructor(s) { this.s = s; } toString() { return this.s; } }
const HTML_ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function esc(s) { return String(s).replace(/[&<>"']/g, c => HTML_ESC[c]); }
function raw(s) { return new Html(s == null ? '' : String(s)); }
function htmlVal(v) {
  if (v == null || v === false) return '';
  if (v instanceof Html) return v.s;
  if (Array.isArray(v)) return v.map(htmlVal).join('');
  return esc(v);
}
function html(strings, ...vals) {
  let out = strings[0];
  for (let i = 0; i < vals.length; i++) out += htmlVal(vals[i]) + strings[i + 1];
  return new Html(out);
}

function togglePy() {
  document.body.classList.toggle('show-py');
  const btn = document.getElementById('pyBtn');
  if (btn) btn.textContent = document.body.classList.contains('show-py') ? '隐藏拼音' : '显示拼音';
}

function toggleEn() {
  document.body.classList.toggle('hide-en');
  const btn = document.getElementById('enBtn');
  if (btn) btn.textContent = document.body.classList.contains('hide-en') ? '显示英文' : '隐藏英文';
}

// ── Voice picker ──────────────────────────────────
let currentVoice = null;

function initVoicePicker() {
  const voiceStr   = document.body.dataset.voices;
  const labelStr   = document.body.dataset.voiceLabels;
  if (!voiceStr) return;

  const voices = voiceStr.split(',').filter(Boolean);
  const labels = labelStr ? labelStr.split(',') : voices;
  const saved  = localStorage.getItem('cn-voice');
  currentVoice = voices.includes(saved) ? saved : voices[0];

  const picker = document.getElementById('voice-picker');
  if (!picker) return;

  const render = () => {
    picker.innerHTML = html`${voices.map((v, i) =>
      html`<button class="btn-voice${v === currentVoice ? ' active' : ''}" data-voice="${v}">${labels[i] || v}</button>`)}`;
  };
  render();

  picker.addEventListener('click', e => {
    const btn = e.target.closest('.btn-voice');
    if (!btn) return;
    currentVoice = btn.dataset.voice;
    localStorage.setItem('cn-voice', currentVoice);
    render();
  });
}

document.addEventListener('DOMContentLoaded', initVoicePicker);

// ── Audio playback ────────────────────────────────
let activeBtn = null, activeAudio = null;

function stopCurrent() {
  if (!activeBtn) return;
  if (activeAudio) { activeAudio.pause(); activeAudio.currentTime = 0; activeAudio = null; }
  activeBtn.classList.remove('playing');
  activeBtn = null;
}

document.addEventListener('click', e => {
  const btn = e.target.closest('.vplay');
  if (!btn) return;

  const prev = activeBtn;
  stopCurrent();
  if (prev === btn) return;

  const src = btn.dataset.src || (btn.dataset.slug && currentVoice
    ? `audio/${btn.dataset.slug}-${currentVoice}.mp3`
    : null);
  if (!src) return;

  const audio = new Audio(src);
  activeAudio = audio; activeBtn = btn;
  btn.classList.add('playing');
  audio.addEventListener('ended', () => {
    btn.classList.remove('playing');
    activeBtn = null; activeAudio = null;
  });
  audio.play();
});
