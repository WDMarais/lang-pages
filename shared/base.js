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
    picker.innerHTML = voices.map((v, i) =>
      `<button class="btn-voice${v === currentVoice ? ' active' : ''}" data-voice="${v}">${labels[i] || v}</button>`
    ).join('');
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
