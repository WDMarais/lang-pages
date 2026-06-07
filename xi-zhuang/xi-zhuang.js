function renderCard(card) {
  const theme = card.theme ? ` ${card.theme}` : '';

  const examples = card.examples.map(ex => {
    const imgSrc = ex.image || '';
    const audioBtns = Object.entries(ex.audio || {}).map(([label, src]) =>
      `<button class="vplay" data-src="${src}">${label}</button>`
    ).join('\n            ');
    return `
          <div class="vex">
            <img class="vex-img" src="${imgSrc}" alt="">
            <div class="zh">${ex.zh}</div>
            <div class="en">${ex.en}</div>
            <div class="vplay-group">
            ${audioBtns}
            </div>
          </div>`;
  }).join('');

  const noteHtml = card.note ? `
          <details class="vnote">
            <summary></summary>
            <div class="vn">${card.note}</div>
          </details>` : '';

  return `
      <div class="vcard${theme}">
        <div class="vhead">
          <div class="vh">${card.hanzi}</div>
          <div class="vp">${card.pinyin}</div>
        </div>
        <div class="vmean">
          <div class="vm">${card.meaning}</div>
          <div class="vm-zh">${card.meaning_zh}</div>
        </div>
        <div class="vcontent">
          ${examples}${noteHtml}
        </div>
      </div>`;
}

function renderSection(containerId, cards) {
  const el = document.getElementById(containerId);
  if (!el || !cards) return;
  el.innerHTML = cards.map(renderCard).join('');
}

fetch('cards.json')
  .then(r => r.json())
  .then(data => {
    renderSection('cards-people', data.people);
    renderSection('cards-suits', data.suits);
    renderSection('cards-body', data.body);
    renderSection('cards-actions', data.actions);
  });
