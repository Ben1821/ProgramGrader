"""計分規則：一題配分 S，測資全過 S/2、未全過 S/4，人工評分總額 S/2，未交 0。"""
from decimal import Decimal

from .models import CriterionScore, Submission


def test_score(points, passed):
    return Decimal(points) / (2 if passed else 4)


def criterion_cap(points, weight):
    return Decimal(points) / 2 * Decimal(weight) / 100


def question_score(sub):
    if sub is None:
        return Decimal('0')
    score = test_score(sub.question.points, sub.tests_passed)
    if sub.graded:  # 待改時舊人工分只是批改頁的預填值，不計入
        score += sum((s.score for s in sub.scores.all()), Decimal('0'))
    return score


def cell_status(sub):
    """missing 未交、done 已完成、review 評過但被退回需複查、pending 從未評過。"""
    if sub is None:
        return 'missing'
    if sub.graded:
        return 'done'
    return 'review' if sub.scores.all() else 'pending'


def progress(rows, questions):
    """總覽頁進度區：整體與每題的 done / pending / review / missing 份數。"""
    keys = ('done', 'pending', 'review', 'missing')
    per_q = [dict.fromkeys(keys, 0) | {'question': q} for q in questions]
    for row in rows:
        for counts, (_, _, _, status) in zip(per_q, row['cells']):
            counts[status] += 1
    total = {k: sum(c[k] for c in per_q) for k in keys}
    for c in per_q + [total]:
        c['submitted'] = c['done'] + c['pending'] + c['review']
        # 無條件捨去：999/1000 不能顯示成 100%
        c['percent'] = c['done'] * 100 // c['submitted'] if c['submitted'] else None
    return {'questions': per_q, 'total': total}


def student_rows(exam):
    """總覽頁與 CSV 共用：每位學生一列，cells 依題目順序為 (question, sub, score, status)。"""
    questions = list(exam.questions.all())
    subs = {(s.student_id, s.question_id): s for s in
            Submission.objects.filter(question__exam=exam)
            .select_related('question').prefetch_related('scores')}
    rows = []
    for student in sorted({sid for sid, _ in subs}):
        cells = []
        for q in questions:
            sub = subs.get((student, q.id))
            cells.append((q, sub, question_score(sub), cell_status(sub)))
        rows.append({
            'student_id': student,
            'cells': cells,
            'total': sum((c[2] for c in cells), Decimal('0')),
            'complete': all(c[3] in ('done', 'missing') for c in cells),
        })
    return rows


def fmt(value):
    """介面與 CSV 共用的分數格式：最多兩位小數、去掉尾端 0。"""
    text = f'{Decimal(value).quantize(Decimal("0.01")):f}'
    return text.rstrip('0').rstrip('.') if '.' in text else text


def invalidate_over_cap(exam):
    """配分或比例改小後，分數超過新上限的作答退回待改。"""
    over = {s.submission_id for s in CriterionScore.objects
            .filter(criterion__exam=exam).select_related('criterion', 'submission__question')
            if s.score > criterion_cap(s.submission.question.points, s.criterion.weight)}
    return Submission.objects.filter(id__in=over, graded=True).update(graded=False)
