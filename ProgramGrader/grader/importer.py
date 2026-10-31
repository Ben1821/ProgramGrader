"""把上傳的資料夾檔案匯入考卷：只看檔名「學號_題號.py」，重新上傳採合併。"""
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .models import Submission
from .runner import run_submission

FILENAME_RE = re.compile(r'^([A-Za-z0-9]+)_([A-Za-z0-9]+)\.py$')


def parse_filename(path):
    m = FILENAME_RE.match(PurePosixPath(path.replace('\\', '/')).name)
    return (m[1].upper(), m[2].upper()) if m else None


def decode(data):
    for encoding in ('utf-8-sig', 'cp950'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode('utf-8', errors='replace')


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    students: set = field(default_factory=set)
    warnings: list = field(default_factory=list)


def import_files(exam, files):
    report = ImportReport()
    questions = {q.code.upper(): q for q in exam.questions.all()}
    picked = {}
    for path, data in files:
        if not path.lower().endswith('.py'):
            continue
        parsed = parse_filename(path)
        if parsed is None:
            report.warnings.append(f'檔名格式不符：{path}')
            continue
        if parsed[1] not in questions:
            report.warnings.append(f'找不到題目 {parsed[1]}：{path}')
            continue
        if parsed in picked:
            report.warnings.append(f'重複檔案，採用 {path}（捨棄 {picked[parsed][0]}）')
        picked[parsed] = (path, data)

    for (student, code), (path, data) in picked.items():
        report.students.add(student)
        text = decode(data)
        sub = Submission.objects.filter(question=questions[code], student_id=student).first()
        if sub is None:
            sub = Submission.objects.create(question=questions[code], student_id=student,
                                            filename=PurePosixPath(path).name, code=text)
            report.created += 1
        elif sub.code != text:
            # 程式碼換了：保留人工分數當預填值，但要重新複查
            sub.code, sub.filename, sub.graded = text, PurePosixPath(path).name, False
            sub.save(update_fields=['code', 'filename', 'graded'])
            report.updated += 1
        else:
            report.unchanged += 1
            continue
        run_submission(sub)
    return report
