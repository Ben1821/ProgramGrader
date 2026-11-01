// 學號搜尋：捲到成績表中的那一列並標示，焦點移到該列第一個可點的格子
document.querySelectorAll('[data-student-search]').forEach((form) => {
  const input = form.querySelector('input');
  const status = document.querySelector('.search-status');
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
    const filter = document.querySelector('[data-only-todo]');
    if (filter && filter.checked && row.dataset.complete === 'true') {
      filter.checked = false;
      filter.dispatchEvent(new Event('change'));
    }
    row.classList.add('found');
    row.scrollIntoView({ block: 'center' });
    (row.querySelector('td a') || row).focus({ preventScroll: true });
  });
});

// 只看還沒改完的學生：隱藏 data-complete="true" 的列
const onlyTodo = document.querySelector('[data-only-todo]');
const scoreTable = document.querySelector('table.overview');
if (onlyTodo && scoreTable) {
  onlyTodo.addEventListener('change', () => scoreTable.classList.toggle('show-todo-only', onlyTodo.checked));
}
