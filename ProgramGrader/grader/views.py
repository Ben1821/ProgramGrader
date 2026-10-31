from urllib.parse import quote

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .export import build_csv
from .forms import CaseFormSet, CriterionFormSet, ExamForm, GradeForm, QuestionFormSet
from .importer import import_files
from .models import Criterion, CriterionScore, Exam, Question, Submission
from .runner import run_question
from .scoring import cell_status, fmt, invalidate_over_cap, student_rows, test_score


def exam_list(request):
    form = ExamForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        exam = Exam.create_with_defaults(form.cleaned_data['name'])
        return redirect('grader:exam_settings', exam.id)
    return render(request, 'grader/exam_list.html', {'exams': Exam.objects.order_by('-id'), 'form': form})


def exam_settings(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    data = request.POST if request.method == 'POST' else None
    form = ExamForm(data, instance=exam)
    questions = QuestionFormSet(data, instance=exam, prefix='q')
    criteria = CriterionFormSet(data, instance=exam, prefix='c')
    if data is not None and form.is_valid() and questions.is_valid() and criteria.is_valid():
        retime = [f.instance for f in questions.initial_forms if 'time_limit' in f.changed_data]
        with transaction.atomic():
            form.save()
            questions.save()
            criteria.save()
            invalidated = invalidate_over_cap(exam)
            if criteria.new_objects:  # 已改完的作答缺新項目的分數，全部退回待改
                invalidated += Submission.objects.filter(question__exam=exam, graded=True).update(graded=False)
        for q in retime:
            run_question(q)
        messages.success(request, '已儲存設定' + (f'，並以新的時間限制重跑 {len(retime)} 題測資' if retime else ''))
        if invalidated:
            messages.warning(request, f'{invalidated} 份已評分的作答因評分設定變更需複查')
        return redirect('grader:exam_settings', exam.id)
    return render(request, 'grader/exam_settings.html',
                  {'exam': exam, 'form': form, 'questions': questions, 'criteria': criteria})


def question_cases(request, pk):
    question = get_object_or_404(Question, pk=pk)
    formset = CaseFormSet(request.POST or None, instance=question, prefix='t')
    if request.method == 'POST' and formset.is_valid():
        formset.save()
        run_question(question)
        messages.success(request, f'已儲存測資並重跑 {question.submissions.count()} 份作答')
        return redirect('grader:question_cases', question.id)
    return render(request, 'grader/question_cases.html',
                  {'exam': question.exam, 'question': question, 'formset': formset})


@require_POST
def question_rerun(request, pk):
    question = get_object_or_404(Question, pk=pk)
    run_question(question)
    messages.success(request, f'已重跑 {question.submissions.count()} 份作答')
    return redirect('grader:question_cases', question.id)


def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    return _confirm_delete(request, question, f'題目 {question.code}', question.exam,
                           question.submissions.count(),
                           CriterionScore.objects.filter(submission__question=question).count())


def criterion_delete(request, pk):
    criterion = get_object_or_404(Criterion, pk=pk)
    return _confirm_delete(request, criterion, f'評分項目「{criterion.name}」', criterion.exam,
                           0, criterion.scores.count())


def _confirm_delete(request, obj, label, exam, submissions, scores):
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f'已刪除{label}')
        total = sum(c.weight for c in exam.criteria.all())
        if total != 100:
            messages.warning(request, f'評分項目比例加總目前為 {fmt(total)}%，請調整為 100% 後儲存')
        return redirect('grader:exam_settings', exam.id)
    return render(request, 'grader/confirm_delete.html',
                  {'exam': exam, 'label': label, 'submissions': submissions, 'scores': scores})


def exam_upload(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == 'POST':
        # Django 只保留上傳檔案的檔名，正好符合「只看檔名」的規則
        files = [(f.name, f.read()) for f in request.FILES.getlist('files')]
        report = import_files(exam, files)
        return render(request, 'grader/upload_result.html', {'exam': exam, 'report': report})
    return render(request, 'grader/upload.html', {'exam': exam})


def exam_overview(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    return render(request, 'grader/overview.html',
                  {'exam': exam, 'questions': exam.questions.all(), 'rows': student_rows(exam)})


def exam_csv(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    response = HttpResponse(build_csv(exam), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(exam.name + '_scores.csv', safe='')}"
    return response


def grade(request, pk):
    question = get_object_or_404(Question.objects.select_related('exam'), pk=pk)
    exam = question.exam
    subs = {s.student_id: s for s in question.submissions.prefetch_related('scores')}
    students = sorted(set(Submission.objects.filter(question__exam=exam)
                          .values_list('student_id', flat=True)))
    roster = [(sid, cell_status(subs.get(sid))) for sid in students]
    pending = [sid for sid, status in roster if status == 'pending']

    current = request.GET.get('student') or (pending[0] if pending else None)
    sub = subs.get(current)
    ctx = {'exam': exam, 'question': question, 'roster': roster, 'current': current, 'sub': sub,
           'graded_count': sum(status == 'done' for _, status in roster),
           'submitted_count': len(subs)}
    if sub is None:
        return render(request, 'grader/grade.html', ctx)

    criteria = exam.criteria.all()
    # DB 存兩位小數（1.00），表單只收一位，先格式化成 '1' 才能原樣送回
    initial = {f'c{s.criterion_id}': fmt(s.score) for s in sub.scores.all()}
    initial['comment'] = sub.comment
    form = GradeForm(request.POST or None, initial=initial, criteria=criteria, points=question.points)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            for criterion, score in form.scores().items():
                CriterionScore.objects.update_or_create(submission=sub, criterion=criterion,
                                                        defaults={'score': score})
            sub.comment = form.cleaned_data['comment']
            sub.graded = True
            sub.save(update_fields=['comment', 'graded'])
        nxt = _next_pending(pending, current)
        url = reverse('grader:grade', args=[question.id])
        return redirect(f'{url}?student={quote(nxt)}' if nxt else url)

    ctx.update(form=form, lines=sub.code.splitlines(),
               test_points=test_score(question.points, sub.tests_passed),
               needs_review=not sub.graded and bool(initial.keys() - {'comment'}))
    return render(request, 'grader/grade.html', ctx)


def _next_pending(pending, current):
    """目前學生之後的下一位待改者，到底就從頭找。"""
    rest = [sid for sid in pending if sid != current]
    after = [sid for sid in rest if sid > current]
    return (after or rest or [None])[0]
