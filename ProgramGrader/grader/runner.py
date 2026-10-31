"""執行學生程式並比對測資。

shortcut: 只有時間限制與輸出大小限制、沒有沙盒，學生程式能讀寫本機檔案；部署上網前要改成容器或其他隔離。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

WRAPPER = Path(__file__).with_name('input_wrapper.py')
MAX_TEXT = 2000  # 存進 DB、顯示在頁面的長度


def normalize(text):
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return '\n'.join(lines)


def run_case(code, stdin, timeout):
    """回傳完整輸出；呼叫端存檔前自行截斷到 MAX_TEXT。輸出寫到檔案，大小上限由 input_wrapper 設定。"""
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, 'main.py').write_text(code, encoding='utf-8')
        out_path, err_path = Path(tmp, 'stdout'), Path(tmp, 'stderr')
        with open(out_path, 'wb') as out, open(err_path, 'wb') as err:
            try:
                proc = subprocess.run(
                    [sys.executable, '-I', '-X', 'utf8', str(WRAPPER), 'main.py'],
                    input=stdin.encode('utf-8'), stdout=out, stderr=err,
                    timeout=timeout, cwd=tmp,
                )
                status = 'ok' if proc.returncode == 0 else 'error'
            except subprocess.TimeoutExpired:
                status = 'timeout'
        read = lambda p: p.read_bytes().decode('utf-8', errors='replace')
        return {'status': status, 'output': read(out_path), 'stderr': read(err_path)}


def run_submission(sub):
    results = []
    for case in sub.question.cases.all():
        r = run_case(sub.code, case.input_text, sub.question.time_limit)
        if r['status'] == 'ok':
            r['status'] = 'pass' if normalize(r['output']) == normalize(case.expected_output) else 'fail'
        results.append({'input': case.input_text, 'expected': case.expected_output,
                        'status': r['status'], 'output': r['output'][:MAX_TEXT],
                        'stderr': r['stderr'][:MAX_TEXT]})
    sub.test_results = results
    sub.tests_passed = all(r['status'] == 'pass' for r in results)
    sub.save(update_fields=['test_results', 'tests_passed'])


def run_question(question):
    for sub in question.submissions.select_related('question'):
        run_submission(sub)
