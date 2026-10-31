// 「新增一列」按鈕：複製 <template id="<prefix>-empty"> 的空白表單，並更新 Django formset 的 TOTAL_FORMS
document.querySelectorAll('[data-add-form]').forEach((button) => {
  button.addEventListener('click', () => {
    const prefix = button.dataset.addForm;
    const total = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const html = document.getElementById(`${prefix}-empty`).innerHTML.replaceAll('__prefix__', total.value);
    document.getElementById(`${prefix}-rows`).insertAdjacentHTML('beforeend', html);
    total.value = Number(total.value) + 1;
  });
});
