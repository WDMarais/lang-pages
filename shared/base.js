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

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.vcontent').forEach(vc => {
    vc.querySelectorAll('.vtab').forEach(tab => {
      tab.addEventListener('click', () => {
        const panel = tab.dataset.panel;
        vc.querySelectorAll('.vtab').forEach(t => t.classList.remove('active'));
        vc.querySelectorAll('.vpanel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        vc.querySelector(`.vpanel[data-panel="${panel}"]`).classList.add('active');
      });
    });
  });
});
