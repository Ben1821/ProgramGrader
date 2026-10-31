import csv
import io

from .scoring import fmt, student_rows


def build_csv(exam):
    out = io.StringIO()
    out.write('﻿')  # BOM：讓 Excel 正確辨識 UTF-8 中文
    writer = csv.writer(out, lineterminator='\r\n')
    writer.writerow(['學號', *(q.code for q in exam.questions.all()), '總分'])
    for row in student_rows(exam):
        writer.writerow([row['student_id'], *(fmt(c[2]) for c in row['cells']), fmt(row['total'])])
    return out.getvalue()
