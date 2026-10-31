# ProgramGrader

批改學生 Python 程式作業的 Django 網站：設定評分標準 → 上傳資料夾 → 自動跑測資 → 人工評分 → 匯出 CSV。

需求與設計：`docs/superpowers/specs/2026-10-31-program-grader-design.md`（以它為準）。

## 結構

- `.venv/`：虛擬環境（Python 3.14、Django 6.1）。
- `ProgramGrader/`：Django 專案根目錄（`manage.py` 在這裡）。
- `ProgramGrader/ProgramGrader/`：settings / urls。

## 常用指令

在 `ProgramGrader/`（manage.py 所在）目錄下執行：

```bash
../.venv/bin/python manage.py runserver
../.venv/bin/python manage.py makemigrations
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py test
```

## 關鍵規則（容易做錯的地方）

- 檔名格式 `學號_題號.py`（例 `D1234567_A01.py`），**只看檔名**，子資料夾名稱不參與判斷。
- 一題配分 S：測資全過得 S/2，未全過（含超時、執行錯誤）得 S/4；人工四項評分總額固定 S/2；未交 0 分。
- 跑測資時 `input()` 的提示文字不算輸出（包裝腳本覆寫 `builtins.input`）；比對忽略行尾空白與結尾空行。
- 評分項目是考卷層級，比例加總必須 100%。
- 重新上傳或重跑測資**不可清掉已填的人工分數**。
- 學生程式以 `sys.executable` 子程序執行，有時間限制，但**沒有沙盒**：只能在本機使用，部署上網前必須補隔離。
- CSV：UTF-8 with BOM，欄位 = 學號、各題分數、總分。

## 慣例

- 介面文字用繁體中文。
- 前端用 Django template + 原生 JS，不引入前端框架。
- 不需登入。
