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
