import difflib
from urllib.parse import quote

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.views.decorators.http import require_POST

from .export import build_csv
from .forms import (CaseFormSet, CriterionFormSet, ExamForm, ExamSettingsForm, FolderForm, GradeForm,
                    QuestionFormSet)
from .importer import import_files, pair_case_files
from .models import Criterion, CriterionScore, Exam, Folder, Question, Submission, TestCase
from .runner import run_question
from .scoring import cell_status, fmt, invalidate_over_cap, progress, question_score, student_rows, test_score
from .similarity import comparable, similar_submissions, similarity, tokens


def home(request, folder_form=None, exam_form=None):
    # ?open=<資料夾 id> 讓指定資料夾展開，其餘摺疊
    open_id = exam_form['folder'].value() if exam_form else request.GET.get('open')
    return render(request, 'grader/home.html', {
        'folders': Folder.objects.prefetch_related('exams'),
        'folder_form': folder_form or FolderForm(),
        'exam_form': exam_form,
        'open_id': str(open_id or ''),
    })


@require_POST
def folder_create(request):
    form = FolderForm(request.POST)
    if not form.is_valid():
        return home(request, folder_form=form)
    folder = form.save()
    return redirect(f"{reverse('grader:home')}?open={folder.id}")


@require_POST
def exam_create(request):
    form = ExamForm(request.POST)
    if not form.is_valid():
        return home(request, exam_form=form)
    exam = Exam.create_with_defaults(form.cleaned_data['name'], form.cleaned_data['folder'])
    return redirect('grader:exam_settings', exam.id)


def exam_settings(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    data = request.POST if request.method == 'POST' else None
    form = ExamSettingsForm(data, instance=exam)
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
def question_cases_upload(request, pk):
    question = get_object_or_404(Question, pk=pk)
    pairs, warnings = pair_case_files([(f.name, f.read()) for f in request.FILES.getlist('files')])
    with transaction.atomic():
        if request.POST.get('replace') and pairs:
            question.cases.all().delete()
        start = max((c.order for c in question.cases.all()), default=-1) + 1
        TestCase.objects.bulk_create(
            TestCase(question=question, input_text=i, expected_output=o, order=start + n)
            for n, (i, o) in enumerate(pairs))
    for w in warnings:
        messages.warning(request, w)
    if pairs:
        run_question(question)
        messages.success(request, f'已匯入 {len(pairs)} 組測資並重跑 {question.submissions.count()} 份作答')
    return redirect('grader:question_cases', question.id)


@require_POST
def question_rerun(request, pk):
    question = get_object_or_404(Question, pk=pk)
    run_question(question)
    messages.success(request, f'已重跑 {question.submissions.count()} 份作答')
    return redirect('grader:question_cases', question.id)


def folder_delete(request, pk):
    folder = get_object_or_404(Folder, pk=pk)
    subs = Submission.objects.filter(question__exam__folder=folder)
    impact = (f'{folder.exams.count()} 份考卷、{subs.count()} 份繳交與 '
              f'{CriterionScore.objects.filter(submission__in=subs).count()} 筆人工分數')
    return _confirm_delete(request, folder, f'資料夾「{folder.name}」', reverse('grader:home'), impact)


def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    subs = Submission.objects.filter(question__exam=exam)
    impact = (f'{exam.questions.count()} 題、{subs.count()} 份繳交與 '
              f'{CriterionScore.objects.filter(submission__in=subs).count()} 筆人工分數')
    return _confirm_delete(request, exam, f'考卷「{exam.name}」',
                           f"{reverse('grader:home')}?open={exam.folder_id}", impact, exam=exam)


def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    impact = (f'{question.submissions.count()} 份繳交與 '
              f'{CriterionScore.objects.filter(submission__question=question).count()} 筆人工分數')
    return _confirm_delete(request, question, f'題目 {question.code}',
                           reverse('grader:exam_settings', args=[question.exam_id]), impact, exam=question.exam)


def criterion_delete(request, pk):
    criterion = get_object_or_404(Criterion, pk=pk)
    exam = criterion.exam
    response = _confirm_delete(request, criterion, f'評分項目「{criterion.name}」',
                               reverse('grader:exam_settings', args=[exam.id]),
                               f'{criterion.scores.count()} 筆人工分數', exam=exam)
    if request.method == 'POST':
        total = sum(c.weight for c in exam.criteria.all())
        if total != 100:
            messages.warning(request, f'評分項目比例加總目前為 {fmt(total)}%，請調整為 100% 後儲存')
    return response


def _confirm_delete(request, obj, label, back_url, impact, exam=None):
    """GET 顯示會一併刪掉哪些資料，POST 才真的刪除並回到 back_url。"""
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f'已刪除{label}')
        return redirect(back_url)
    return render(request, 'grader/confirm_delete.html',
                  {'exam': exam, 'label': label, 'impact': impact, 'back_url': back_url})


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
    questions = list(exam.questions.all())
    rows = student_rows(exam)
    return render(request, 'grader/overview.html', {'exam': exam, 'questions': questions, 'rows': rows,
                                                    'progress': progress(rows, questions)})


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
    pending = [sid for sid, status in roster if status in ('pending', 'review')]

    current = request.GET.get('student') or (pending[0] if pending else None)
    sub = subs.get(current)
    tab = request.GET.get('tab') if request.GET.get('tab') in ('students', 'scores', 'similar') else 'students'
    ctx = {'exam': exam, 'question': question, 'roster': roster, 'current': current, 'sub': sub, 'tab': tab,
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
               needs_review=not sub.graded and bool(initial.keys() - {'comment'}),
               criteria=criteria, peers=_peer_scores(subs, criteria, current),
               similar=[{'sub': other, 'percent': pct, 'comparable': ok,
                         'flagged': ok and pct >= exam.similarity_threshold,
                         'score': question_score(other), 'status': cell_status(other)}
                        for other, pct, ok in similar_submissions(sub)])
    return render(request, 'grader/grade.html', ctx)


def _peer_scores(subs, criteria, current):
    """同題已改作答的總分與各項細分，給批改頁「同題分數」比對用。"""
    peers = []
    for sid, s in sorted(subs.items()):
        if not s.graded:
            continue
        by_criterion = {c.criterion_id: c.score for c in s.scores.all()}
        peers.append({'student_id': sid, 'total': question_score(s), 'current': sid == current,
                      'breakdown': [by_criterion.get(c.id) for c in criteria]})
    return peers


def compare(request, pk):
    question = get_object_or_404(Question.objects.select_related('exam'), pk=pk)
    a = get_object_or_404(question.submissions, student_id=request.GET.get('a'))
    b = get_object_or_404(question.submissions, student_id=request.GET.get('b'))
    table = difflib.HtmlDiff(wrapcolumn=70).make_table(
        a.code.splitlines(), b.code.splitlines(), escape(a.student_id), escape(b.student_id))
    ta, tb = tokens(a.code), tokens(b.code)
    return render(request, 'grader/compare.html', {
        'exam': question.exam, 'question': question, 'a': a, 'b': b,
        'percent': similarity(ta, tb), 'comparable': comparable(ta, tb),
        'a_score': question_score(a), 'b_score': question_score(b),
        'table': mark_safe(table),  # HtmlDiff 會 escape 程式碼；表頭的學號已在上面 escape
    })


def _next_pending(pending, current):
    """目前學生之後的下一位待改者，到底就從頭找。"""
    rest = [sid for sid in pending if sid != current]
    after = [sid for sid in rest if sid > current]
    return (after or rest or [None])[0]
