function togglePy() {
  document.body.classList.toggle('show-py');
  const btn = document.getElementById('pyBtn');
  if (btn) btn.textContent = document.body.classList.contains('show-py') ? '隐藏拼音' : '显示拼音';
}
