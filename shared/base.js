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

let activeBtn = null, activeAudio = null;

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.vplay').forEach(btn => {
    btn.addEventListener('click', () => {
      if (activeAudio) {
        activeAudio.pause();
        activeAudio.currentTime = 0;
        activeBtn.classList.remove('playing');
      }
      if (activeBtn === btn) { activeBtn = null; activeAudio = null; return; }

      const { slug, voice, src } = btn.dataset;
      const url = slug
        ? (voice === 'recording' ? `audio/${slug}.mp3` : `audio/${slug}-${voice}.mp3`)
        : src;

      const audio = new Audio(url);
      activeAudio = audio; activeBtn = btn;
      btn.classList.add('playing');
      audio.addEventListener('ended', () => {
        btn.classList.remove('playing');
        activeBtn = null; activeAudio = null;
      });
      audio.play();
    });
  });
});
