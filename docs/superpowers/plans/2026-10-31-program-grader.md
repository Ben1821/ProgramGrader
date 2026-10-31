# ProgramGrader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一個本機 Django 網站：設定考卷評分標準 → 上傳學生 Python 程式資料夾 → 自動跑測資 → 依題連續人工評分 → 匯出 CSV。

**Architecture:** 單一 Django app `grader`。純邏輯拆成無 Django view 依賴的模組（`scoring.py` 計分、`runner.py` 執行測資、`importer.py` 解析上傳、`export.py` 產 CSV），各自單元測試；views 只負責表單與畫面。學生程式碼存 DB 文字欄位，執行時寫到暫存目錄，用 `sys.executable` 子程序 + 包裝腳本執行。

**Tech Stack:** Python 3.14、Django 6.1、SQLite、Django template + 原生 JS、Django `TestCase`。

**Spec:** `docs/superpowers/specs/2026-10-31-program-grader-design.md`

## Global Constraints

- 路徑：git 根目錄 = `/Users/yehweipingrubi/Desktop/Django/ProgramGrader`；Django 專案目錄（`manage.py`）= `ProgramGrader/`；app 放 `ProgramGrader/grader/`。
- 測試指令（在 `ProgramGrader/` 下）：`../.venv/bin/python manage.py test grader`。
- 不新增第三方套件；不需登入；介面文字繁體中文。
- 檔名格式 `學號_題號.py`，只看檔名，不看子資料夾。
- 一題配分 S：測資全過 `S/2`、未全過（錯誤／超時／執行錯誤／語法錯誤）`S/4`、未交 0；人工四項總額 `S/2`，每項上限 `S/2 × 比例`。
- 沒有測資的題目視為全過。
- 預設評分項目：題目需求理解 30%「是否理解題目要求，知道需要完成哪些功能」／核心邏輯與觀念 30%「計算公式、條件判斷、程式流程是否正確」／功能實作與結果 25%「是否完成指定功能，輸出是否符合預期」／程式可執行性 15%「是否存在語法錯誤、變數錯誤或其他執行問題」。比例加總必須 100。
- 時間限制預設 5 秒，每組測資各自計時。
- 比對：忽略 `input()` 提示文字、每行行尾空白、結尾多餘空行。
- 分數一律 `Decimal`（2 位小數），人工分最小單位 0.1；顯示與 CSV 共用 `scoring.fmt()`。
- CSV：UTF-8 with BOM，欄位 `學號, <題號…>, 總分`，依學號排序，評語不輸出。
- 重新上傳 = 合併；人工分數永不因上傳／重跑而被刪除。

## Review Focus

1. 學生程式無窮迴圈 → 超時被殺掉、算未全過，網站不卡住（Task 3 `test_timeout`）。
2. 學生程式要求的輸入比測資多 → `EOFError` 立即算執行錯誤，不會卡到超時（Task 3 `test_eof_is_error`）。
3. 學生檔案是 Big5/cp950 或帶 BOM → 照樣能匯入與顯示，不炸 500（Task 4 `test_decodes_big5_and_bom`）。
4. 檔名大小寫不一（`d1234567_a01.py`）→ 學號、題號都轉大寫比對，照樣匯入（Task 4 `test_case_insensitive`）。
5. 學生程式輸出巨量文字 → 儲存的實際輸出／stderr 截斷到 2000 字元，頁面不爆（Task 3 `test_output_truncated`）。

---

### Task 1: App 骨架與資料模型

**Files:**
- Create: `ProgramGrader/grader/__init__.py`, `apps.py`, `models.py`, `admin.py`, `tests/__init__.py`, `tests/test_models.py`, `migrations/`
- Modify: `ProgramGrader/ProgramGrader/settings.py`（`INSTALLED_APPS` 加 `'grader'`、`LANGUAGE_CODE = 'zh-hant'`、`TIME_ZONE = 'Asia/Taipei'`、`DATA_UPLOAD_MAX_NUMBER_FILES = 5000`、`DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024`）

**Interfaces:**
- Produces（`grader.models`）：
  - `Exam(name: CharField unique)`；`Exam.create_with_defaults(name) -> Exam` 建立考卷並建立四個預設 `Criterion`。
  - `Criterion(exam FK related_name='criteria', name, weight: Decimal(5,2) 百分比, description, order)`，`Meta.ordering = ['order', 'id']`。
  - `Question(exam FK related_name='questions', code: CharField 已大寫, points: Decimal(6,2), time_limit: PositiveInteger 預設 5, order)`，`unique_together = (exam, code)`，`ordering = ['order', 'id']`。
  - `TestCase(question FK related_name='cases', input_text: Text, expected_output: Text, order)`。
  - `Submission(question FK related_name='submissions', student_id: CharField 已大寫, filename, code: Text, tests_passed: Bool, test_results: JSONField 預設 list, graded: Bool 預設 False, comment: Text blank)`，`unique_together = (question, student_id)`。
  - `CriterionScore(submission FK related_name='scores', criterion FK, score: Decimal(6,2))`，`unique_together = (submission, criterion)`。

- [ ] **Step 1: 寫失敗測試 `tests/test_models.py`**

```python
def test_create_with_defaults_adds_four_criteria(self):
    exam = Exam.create_with_defaults('A')
    names = [c.name for c in exam.criteria.all()]
    self.assertEqual(names, ['題目需求理解', '核心邏輯與觀念', '功能實作與結果', '程式可執行性'])
    self.assertEqual(sum(c.weight for c in exam.criteria.all()), Decimal('100'))

def test_submission_unique_per_student_question(self):
    # 同 question + student_id 建第二筆 → IntegrityError
```

- [ ] **Step 2: 跑測試確認失敗**（`ImportError` / app 未安裝）
- [ ] **Step 3: `startapp grader`、改 settings、寫 models、`makemigrations grader`**；admin 註冊所有 model（方便除錯）。
- [ ] **Step 4: 跑 `../.venv/bin/python manage.py test grader` → PASS**
- [ ] **Step 5: Commit** `feat: add grader app and models`

---

### Task 2: 計分模組 `scoring.py`

**Files:**
- Create: `ProgramGrader/grader/scoring.py`, `ProgramGrader/grader/tests/test_scoring.py`

**Interfaces:**
- Consumes: Task 1 models。
- Produces（`grader.scoring`）：
  - `test_score(points: Decimal, passed: bool) -> Decimal`：`points/2` 或 `points/4`。
  - `criterion_cap(points: Decimal, weight: Decimal) -> Decimal`：`points / 2 * weight / 100`。
  - `question_score(sub: Submission | None) -> Decimal`：None → 0；否則 `test_score + Σ scores`。
  - `cell_status(sub: Submission | None) -> str`：`'missing'` / `'done'`（`sub.graded`）/ `'pending'`。
  - `student_rows(exam) -> list[dict]`：`[{'student_id', 'cells': [(question, sub|None, score, status)…], 'total': Decimal, 'complete': bool}]`，依學號排序，題目依 `order`。總覽頁與 CSV 共用。
  - `fmt(value: Decimal) -> str`：量化到 0.01 後去尾端 0（`Decimal('12.50')→'12.5'`、`Decimal('10.00')→'10'`）。
  - `invalidate_over_cap(exam) -> int`：任何 `CriterionScore.score > criterion_cap(...)` 的 submission 設 `graded=False`，回傳受影響數。

- [ ] **Step 1: 寫失敗測試**

```python
def test_test_score(self):
    self.assertEqual(test_score(Decimal('20'), True), Decimal('10'))
    self.assertEqual(test_score(Decimal('20'), False), Decimal('5'))
    self.assertEqual(test_score(Decimal('5'), False), Decimal('1.25'))

def test_criterion_cap(self):
    self.assertEqual(criterion_cap(Decimal('20'), Decimal('30')), Decimal('3'))
    self.assertEqual(criterion_cap(Decimal('20'), Decimal('15')), Decimal('1.5'))

def test_question_score_missing_is_zero(self): ...  # None → Decimal('0')
def test_question_score_sums(self): ...  # S=20, passed, 四項 3+3+2.5+1.5 → 20
def test_fmt(self):
    self.assertEqual(fmt(Decimal('12.50')), '12.5'); self.assertEqual(fmt(Decimal('10.00')), '10')
    self.assertEqual(fmt(Decimal('1.25')), '1.25')
def test_student_rows_total_and_complete(self): ...  # 兩題、一題未交 → total 只算有交的、未交那格 status='missing'；有 pending 時 complete=False
def test_invalidate_over_cap(self): ...  # 已 graded、score 3，把 points 從 20 改 10（cap 1.5）→ graded False，回傳 1
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**（全部用 `Decimal`，不用 float）
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: Commit** `feat: scoring rules`

---

### Task 3: 測資執行 `runner.py`

**Files:**
- Create: `ProgramGrader/grader/runner.py`, `ProgramGrader/grader/input_wrapper.py`, `ProgramGrader/grader/tests/test_runner.py`

**Interfaces:**
- Consumes: Task 1 models。
- Produces（`grader.runner`）：
  - `normalize(text: str) -> str`：每行 `rstrip()`、去掉結尾空行。
  - `run_case(code: str, stdin: str, timeout: int) -> dict`：回傳 `{'status': 'ok'|'timeout'|'error', 'output': str, 'stderr': str}`；不做比對，比對在 `run_submission`（`ok` 且 `normalize(output) == normalize(expected)` → `pass`，`ok` 但不同 → `fail`）。
  - `run_submission(sub: Submission) -> None`：對 `sub.question.cases` 逐筆 `run_case`，組 `test_results = [{'input', 'expected', 'output', 'stderr', 'status': 'pass'|'fail'|'timeout'|'error'}…]`，`tests_passed = all(pass)`（無測資 → True），存檔。
  - `run_question(question) -> None`：對該題所有 submission 呼叫 `run_submission`。

**做法（演算法決定）：**
- 學生程式碼寫入 `tempfile.TemporaryDirectory()` 下的 `main.py`，cwd 設在該目錄。
- 執行 `[sys.executable, '-I', <input_wrapper.py 絕對路徑>, 'main.py']`，`input=stdin`、`capture_output=True`、`text=True`、`encoding='utf-8'`、`errors='replace'`、`timeout=timeout`，env 加 `PYTHONIOENCODING=utf-8`。
- `input_wrapper.py`：
  ```python
  import builtins, runpy, sys
  def _input(prompt=''):
      line = sys.stdin.readline()
      if not line:
          raise EOFError
      return line.rstrip('\n')
  builtins.input = _input
  sys.argv = sys.argv[1:]
  runpy.run_path(sys.argv[0], run_name='__main__')
  ```
- `TimeoutExpired` → `'timeout'`；returncode ≠ 0 → `'error'`；否則 `'ok'`。output/stderr 各截斷 2000 字元。

- [ ] **Step 1: 寫失敗測試**

```python
def test_prompt_ignored_and_pass(self):
    r = run_case('n = int(input("請輸入數字："))\nprint(n * 2)', '21\n', 5)
    self.assertEqual(r['status'], 'ok'); self.assertEqual(normalize(r['output']), '42')
def test_normalize(self):
    self.assertEqual(normalize('a  \nb\n\n\n'), 'a\nb')
def test_timeout(self):
    self.assertEqual(run_case('while True: pass', '', 1)['status'], 'timeout')
def test_eof_is_error(self):
    self.assertEqual(run_case('input()\ninput()', '1\n', 5)['status'], 'error')
def test_syntax_error(self):
    r = run_case('print(', '', 5); self.assertEqual(r['status'], 'error'); self.assertIn('SyntaxError', r['stderr'])
def test_output_truncated(self):
    self.assertLessEqual(len(run_case('print("x" * 100000)', '', 5)['output']), 2000)
def test_run_submission_sets_flags(self): ...  # 兩組測資一對一錯 → tests_passed False，test_results[1]['status']=='fail'
def test_run_submission_no_cases_passes(self): ...  # 無測資 → tests_passed True
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: Commit** `feat: test case runner with input prompt suppression`

---

### Task 4: 上傳匯入 `importer.py`

**Files:**
- Create: `ProgramGrader/grader/importer.py`, `ProgramGrader/grader/tests/test_importer.py`

**Interfaces:**
- Consumes: Task 1 models、Task 3 `run_submission`。
- Produces（`grader.importer`）：
  - `parse_filename(path: str) -> tuple[str, str] | None`：取 basename；必須 `.py`；regex `^([A-Za-z0-9]+)_([A-Za-z0-9]+)\.py$`；回傳 `(學號.upper(), 題號.upper())`。
  - `decode(data: bytes) -> str`：依序試 `utf-8-sig`、`cp950`，都失敗用 `utf-8` + `errors='replace'`。
  - `ImportReport`（dataclass）：`created: int`, `updated: int`, `unchanged: int`, `students: set[str]`, `warnings: list[str]`。
  - `import_files(exam, files: list[tuple[str, bytes]]) -> ImportReport`：
    - 非 `.py` → 略過不警告。
    - `.py` 但 `parse_filename` 為 None → 警告「檔名格式不符：<路徑>」。
    - 題號不在此考卷 → 警告「找不到題目 <題號>：<路徑>」。
    - 同一批中同學號同題重複 → 警告「重複檔案，採用 <後者路徑>」，以後者為準。
    - 新的 → 建立並 `run_submission`；已存在且 code 不同 → 更新 code、`graded=False`、保留 `scores`、`run_submission`；code 相同 → 不動（`unchanged`）。
    - 這批沒出現的既有 submission 不動。

- [ ] **Step 1: 寫失敗測試**

```python
def test_parse_filename(self):
    self.assertEqual(parse_filename('x/y/D1234567_A01.py'), ('D1234567', 'A01'))
    self.assertIsNone(parse_filename('D1234567-A01.py')); self.assertIsNone(parse_filename('D1234567_A01.txt'))
def test_case_insensitive(self): ...  # 'd1234567_a01.py' 匯入到題目 A01，student_id == 'D1234567'
def test_decodes_big5_and_bom(self): ...  # '# 中文\nprint(1)'.encode('cp950') 與 b'\xef\xbb\xbf' + utf8 都能匯入且 code 含「中文」
def test_warnings(self): ...  # 錯檔名、未知題號、重複 → 3 條 warnings；.DS_Store 不產生 warning
def test_reupload_merges_and_keeps_scores(self):
    # 先匯入 S1_A01、S2_A01；給 S1 填 CriterionScore 並 graded=True
    # 再只匯入改過內容的 S1_A01 → S1 graded False、scores 仍在；S2 仍存在
def test_reupload_same_code_unchanged(self): ...  # 內容相同 → graded 維持 True，report.unchanged == 1
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: Commit** `feat: folder import with merge semantics`

---

### Task 5: CSV 匯出 `export.py`

**Files:**
- Create: `ProgramGrader/grader/export.py`, `ProgramGrader/grader/tests/test_export.py`

**Interfaces:**
- Consumes: Task 2 `student_rows`, `fmt`。
- Produces: `build_csv(exam) -> str`（含開頭 `'﻿'`；用 `csv.writer`，`lineterminator='\r\n'`）。

- [ ] **Step 1: 寫失敗測試**

```python
def test_build_csv(self):
    # 題目 A01(20)、A02(10)；S1 A01 全過+人工 10、A02 未交；S2 A01 沒過人工 0、A02 全過人工 0
    text = build_csv(exam)
    self.assertTrue(text.startswith('﻿'))
    rows = list(csv.reader(io.StringIO(text.lstrip('﻿'))))
    self.assertEqual(rows, [['學號', 'A01', 'A02', '總分'], ['S1', '20', '0', '20'], ['S2', '5', '5', '10']])
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: Commit** `feat: csv export`

---

### Task 6: 考卷列表與設定頁

**Files:**
- Create: `ProgramGrader/grader/urls.py`, `views.py`, `forms.py`, `templates/grader/base.html`, `exam_list.html`, `exam_settings.html`, `confirm_delete.html`, `static/grader/style.css`, `tests/test_views_settings.py`
- Modify: `ProgramGrader/ProgramGrader/urls.py`（`path('', include('grader.urls'))`）

**Interfaces:**
- Consumes: Task 1 models、Task 2 `invalidate_over_cap`、Task 3 `run_question`。
- Produces（URL names，app_name=`grader`）：
  - `exam_list` `/`：列表 + 新增考卷表單（POST 用 `Exam.create_with_defaults`）。
  - `exam_settings` `/exam/<id>/settings/`：考卷名稱、題目 inline formset（code/points/time_limit/order + 刪除）、評分項目 inline formset（name/weight/description/order + 刪除）。
  - `question_cases` `/question/<id>/cases/`：該題測資 inline formset（input_text/expected_output），儲存後自動 `run_question`；另有「重跑此題測資」POST `question_rerun` `/question/<id>/rerun/`。
  - `question_delete` / `criterion_delete`：GET 顯示「將刪除 N 份繳交與 M 筆分數」確認頁，POST 刪除。
- 驗證：評分項目 weight 加總 ≠ 100 → formset 非欄位錯誤「比例加總需為 100%，目前為 X%」；題號自動轉大寫、同考卷不可重複；儲存成功後呼叫 `invalidate_over_cap(exam)`，>0 時 messages 提示「N 份已評分的作答因上限變更需複查」。
- 填寫指引（placeholder／說明文字，照抄）：
  - 題號：「例如 A01，需與檔名 學號_A01.py 的題號相同」
  - 配分：「這題總分，例如 20」
  - 時間限制：「每組測資最多執行幾秒，預設 5」
  - 測資輸入：「就像在終端機輸入的內容，每行一個值」
  - 預期輸出：「程式應印出的內容；不用包含 input() 的提示文字，行尾空白會被忽略」
  - 評分項目比例：「百分比，所有項目加總需為 100」
  - 沒有測資的題目在設定頁顯示「此題沒有測資，將視為全部通過」。

- [ ] **Step 1: 寫失敗測試**

```python
def test_create_exam_redirects_to_settings(self): ...  # POST / name='A' → 302 到 settings，exam.criteria.count()==4
def test_weights_must_sum_100(self): ...  # 改成 30/30/25/10 → 200 且頁面含「比例加總需為 100%」
def test_question_code_uppercased(self): ...  # 新增 'a01' → Question.code == 'A01'
def test_save_cases_runs_tests(self): ...  # 有一份 submission，新增測資後 test_results 長度 1
def test_delete_question_confirm_page_counts(self): ...  # GET 頁面含「1 份繳交」
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**（base.html 放全站導覽：考卷列表 › 考卷名 › 設定／上傳／總覽；style.css 手寫，簡潔即可）
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: Commit** `feat: exam settings pages`

---

### Task 7: 上傳頁

**Files:**
- Create: `templates/grader/upload.html`, `upload_result.html`, `tests/test_views_upload.py`
- Modify: `grader/views.py`, `grader/urls.py`

**Interfaces:**
- Consumes: Task 4 `import_files`, `ImportReport`。
- Produces: `exam_upload` `/exam/<id>/upload/`：GET 表單（`<input type="file" name="files" webkitdirectory multiple>`），POST 讀 `request.FILES.getlist('files')`，每個檔用 `f.name` 當路徑（瀏覽器在 webkitdirectory 下會給相對路徑；只取 basename 判斷即可）→ `import_files` → render `upload_result.html`（新增／更新／未變數量、學生數、警告清單、「前往總覽」按鈕）。

- [ ] **Step 1: 寫失敗測試**

```python
def test_upload_imports_and_shows_warnings(self):
    # POST 兩個 SimpleUploadedFile：'D1_A01.py'、'bad.py' → 200，Submission 1 筆，頁面含「檔名格式不符」
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: Commit** `feat: folder upload page`

---

### Task 8: 總覽頁與 CSV 下載

**Files:**
- Create: `templates/grader/overview.html`, `tests/test_views_overview.py`
- Modify: `grader/views.py`, `grader/urls.py`

**Interfaces:**
- Consumes: Task 2 `student_rows`, `fmt`；Task 5 `build_csv`。
- Produces:
  - `exam_overview` `/exam/<id>/`：表格列＝學號、欄＝題號＋總分；格子顯示 `fmt(score)` + 狀態（done「✔」、pending「✋待改」、missing「未交」）；總分在 `complete=False` 時加「*」與圖例「* 尚未改完」。格子連到 `grade` 並帶 `?student=<學號>`；欄標題連到 `grade`（無參數）。
  - `exam_csv` `/exam/<id>/csv/`：`HttpResponse(build_csv(exam), content_type='text/csv; charset=utf-8')`，`Content-Disposition: attachment; filename="<考卷名>_scores.csv"`（中文名用 `filename*=UTF-8''…`）。
- 需要 `fmt` 的 template filter：`grader/templatetags/grader_extras.py` 的 `score` filter → `fmt`。

- [ ] **Step 1: 寫失敗測試**

```python
def test_overview_shows_status(self): ...  # 頁面含 '✋' 與 '未交'
def test_csv_download(self):
    r = self.client.get(reverse('grader:exam_csv', args=[exam.id]))
    self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8'); self.assertTrue(r.content.startswith(b'\xef\xbb\xbf'))
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: Commit** `feat: overview table and csv download`

---

### Task 9: 批改頁（依題連續批改）

**Files:**
- Create: `templates/grader/grade.html`, `static/grader/grade.js`, `tests/test_views_grade.py`
- Modify: `grader/views.py`, `grader/urls.py`, `grader/forms.py`

**Interfaces:**
- Consumes: Task 1 models、Task 2 `criterion_cap`, `test_score`, `cell_status`, `fmt`。
- Produces: `grade` `/question/<id>/grade/`
  - GET：`?student=` 指定學生，否則選第一位 `pending`；全改完則顯示「此題已全部改完」+ 回總覽。
  - 左：該題所有出現在本考卷的學號（含未交，未交灰色不可點），各帶狀態；進度「已改 x / 有交 y」。
  - 中：程式碼（`<pre>` 每行加行號，等寬字體）；測資結果列表，非 pass 的展開顯示 輸入／預期／實際／stderr；顯示「測資分：fmt(test_score)」。
  - 右：每個 Criterion 一個 `<input type="number" step="0.1" min="0" max="cap">`，標籤「名稱（上限 cap）」與 description；預填既有分數；評語 textarea；按鈕「儲存並下一位」。
  - 若 `graded=False` 且已有分數 → 顯示「設定或程式碼已變更，請複查」。
  - POST：驗證每項 `0 ≤ score ≤ cap`（server 端，超過回同頁顯示錯誤），全部項目必填；寫入 `CriterionScore`（update_or_create）、`comment`、`graded=True`；redirect 到下一位 pending（依學號順序，從目前學生之後找，找不到再從頭找），都沒有則 redirect 到同頁顯示全部改完。
  - `grade.js`：在評分欄位按 Enter 送出表單；（可選）`↑/↓` 在欄位間移動。

- [ ] **Step 1: 寫失敗測試**

```python
def test_get_defaults_to_first_pending(self): ...  # S1 已 graded、S2 pending → 頁面含 S2 的程式碼
def test_post_saves_and_redirects_next(self): ...  # POST S2 合法分數 → graded True、302 且 Location 含 student=S3
def test_post_over_cap_rejected(self): ...  # S=20 需求理解填 3.5（cap 3）→ 200、graded 仍 False、頁面含「上限」
def test_missing_student_not_gradable(self): ...  # ?student=未交者 → 不顯示評分表單，顯示「未交」
```

- [ ] **Step 2: 跑測試確認失敗**
- [ ] **Step 3: 實作**
- [ ] **Step 4: 跑測試 → PASS**
- [ ] **Step 5: 手動煙霧測試**：`runserver`，建考卷 A（A01 配分 20、一組測資），上傳含 3 個學生資料夾（一份正確、一份無窮迴圈、一份 Big5 編碼）→ 總覽 → 批改 → 匯出 CSV 用 Excel/Numbers 開啟中文正常。
- [ ] **Step 6: Commit** `feat: sequential grading page`
