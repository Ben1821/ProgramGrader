// 學號搜尋：捲到成績表中的那一列並標示，焦點移到該列第一個可點的格子
document.querySelectorAll('[data-student-search]').forEach((form) => {
  const input = form.querySelector('input');
  const status = form.querySelector('.search-status');
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const id = input.value.trim().toUpperCase();
    document.querySelectorAll('tr.found').forEach((row) => row.classList.remove('found'));
    const row = id && document.getElementById(`student-${id}`);
    if (!row) {
      status.textContent = id ? `找不到 ${id}` : '';
      return;
    }
    status.textContent = '';
    row.classList.add('found');
    row.scrollIntoView({ block: 'center' });
    (row.querySelector('td a') || row).focus({ preventScroll: true });
  });
});
