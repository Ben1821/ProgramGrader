// 側邊欄分頁：點擊或左右方向鍵切換
const tabs = [...document.querySelectorAll('.side [role="tab"]')];
function selectTab(tab) {
  tabs.forEach((t) => {
    const on = t === tab;
    t.setAttribute('aria-selected', on);
    t.tabIndex = on ? 0 : -1;
    document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
  });
}
tabs.forEach((tab, i) => {
  tab.tabIndex = tab.getAttribute('aria-selected') === 'true' ? 0 : -1;
  tab.addEventListener('click', () => selectTab(tab));
  tab.addEventListener('keydown', (event) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    const next = tabs[(i + step + tabs.length) % tabs.length];
    selectTab(next);
    next.focus();
  });
});

// 同題分數排序：學號（升冪）或總分（降冪）
document.querySelectorAll('[data-sort]').forEach((button) => {
  button.addEventListener('click', () => {
    const body = document.querySelector('[data-sortable] tbody');
    const rows = [...body.rows];
    const byTotal = button.dataset.sort === 'total';
    rows.sort((a, b) => (byTotal
      ? Number(b.dataset.total) - Number(a.dataset.total)
      : a.dataset.id.localeCompare(b.dataset.id)));
    body.append(...rows);
    document.querySelectorAll('[data-sort]').forEach((b) => b.setAttribute('aria-pressed', b === button));
  });
});
