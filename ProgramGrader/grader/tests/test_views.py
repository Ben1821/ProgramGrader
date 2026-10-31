import re
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from grader.models import CriterionScore, Exam, Folder, Question, Submission, TestCase as Case


def settings_post(exam, questions=(), weights=None):
    """組出設定頁 formset 的 POST 資料；questions 為 (code, points) 新增列。"""
    data = {'name': exam.name, 'folder': exam.folder_id, 'similarity_threshold': exam.similarity_threshold}
    existing_q = list(exam.questions.all())
    rows = [(q.id, q.code, q.points) for q in existing_q] + [('', c, p) for c, p in questions]
    data.update({'q-TOTAL_FORMS': len(rows), 'q-INITIAL_FORMS': len(existing_q),
                 'q-MIN_NUM_FORMS': 0, 'q-MAX_NUM_FORMS': 1000})
    for i, (pk, code, points) in enumerate(rows):
        data.update({f'q-{i}-id': pk, f'q-{i}-code': code, f'q-{i}-points': points,
                     f'q-{i}-time_limit': 5, f'q-{i}-order': i})
    criteria = list(exam.criteria.all())
    weights = weights or [c.weight for c in criteria]
    data.update({'c-TOTAL_FORMS': len(criteria), 'c-INITIAL_FORMS': len(criteria),
                 'c-MIN_NUM_FORMS': 0, 'c-MAX_NUM_FORMS': 1000})
    for i, (c, w) in enumerate(zip(criteria, weights)):
        data.update({f'c-{i}-id': c.id, f'c-{i}-name': c.name, f'c-{i}-weight': w,
                     f'c-{i}-description': c.description, f'c-{i}-order': i})
    return data


class SettingsViewTests(TestCase):
    def setUp(self):
        self.exam = Exam.create_with_defaults('A')

    def test_create_exam_in_folder_redirects_to_settings(self):
        folder = Folder.objects.create(name='113上')
        r = self.client.post(reverse('grader:exam_create'), {'name': 'B', 'folder': folder.id})
        exam = Exam.objects.get(name='B')
        self.assertRedirects(r, reverse('grader:exam_settings', args=[exam.id]))
        self.assertEqual((exam.folder, exam.criteria.count()), (folder, 4))

    def test_exam_name_unique_per_folder(self):
        r = self.client.post(reverse('grader:exam_create'), {'name': 'A', 'folder': self.exam.folder_id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Exam.objects.filter(name='A').count(), 1)
        other = Folder.objects.create(name='其他')
        self.client.post(reverse('grader:exam_create'), {'name': 'A', 'folder': other.id})
        self.assertEqual(Exam.objects.filter(name='A').count(), 2)

    def test_folder_create_and_home_collapsed(self):
        r = self.client.post(reverse('grader:folder_create'), {'name': '113上'})
        folder = Folder.objects.get(name='113上')
        self.assertRedirects(r, reverse('grader:home') + f'?open={folder.id}')
        html = self.client.get(reverse('grader:home')).content.decode()
        self.assertIn('113上', html)
        self.assertNotIn('<details class="folder" open', html)
        html = self.client.get(reverse('grader:home') + f'?open={folder.id}').content.decode()
        self.assertEqual(html.count('<details class="folder" open'), 1)

    def test_delete_exam_confirms_then_deletes(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        Submission.objects.create(question=q, student_id='S1', filename='', code='')
        url = reverse('grader:exam_delete', args=[self.exam.id])
        self.assertContains(self.client.get(url), '1 題、1 份繳交與 0 筆人工分數')
        self.assertTrue(Exam.objects.exists())
        r = self.client.post(url)
        self.assertRedirects(r, reverse('grader:home') + f'?open={self.exam.folder_id}')
        self.assertFalse(Exam.objects.exists())
        self.assertFalse(Submission.objects.exists())
        self.assertTrue(Folder.objects.exists())

    def test_delete_folder_removes_its_exams_only(self):
        other = Exam.create_with_defaults('B', Folder.objects.create(name='其他'))
        url = reverse('grader:folder_delete', args=[self.exam.folder_id])
        self.assertContains(self.client.get(url), '1 份考卷')
        self.assertRedirects(self.client.post(url), reverse('grader:home'))
        self.assertEqual(list(Exam.objects.all()), [other])

    def test_home_has_delete_links(self):
        r = self.client.get(reverse('grader:home'))
        self.assertContains(r, reverse('grader:folder_delete', args=[self.exam.folder_id]))
        self.assertContains(r, reverse('grader:exam_delete', args=[self.exam.id]))

    def test_back_links(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        self.assertContains(self.client.get(reverse('grader:exam_settings', args=[self.exam.id])),
                            f'href="/?open={self.exam.folder_id}">← 返回')
        self.assertContains(self.client.get(reverse('grader:question_cases', args=[q.id])), '← 返回考卷設定')
        self.assertContains(self.client.get(reverse('grader:grade', args=[q.id])), '← 返回總覽')

    def test_settings_has_add_buttons(self):
        r = self.client.get(reverse('grader:exam_settings', args=[self.exam.id]))
        self.assertContains(r, 'data-add-form="q"')
        self.assertContains(r, 'name="q-__prefix__-code"')

    def test_upload_case_files_appends_in_order(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        Case.objects.create(question=q, input_text='old', expected_output='old', order=0)
        sub = Submission.objects.create(question=q, student_id='S1', filename='', code='print(int(input())*2)')
        files = [SimpleUploadedFile(n, d) for n, d in
                 [('10.in', b'10\r\n'), ('10.out', b'20\n'), ('2.in', b'2\n'), ('2.out', b'4\n'), ('3.in', b'3\n')]]
        r = self.client.post(reverse('grader:question_cases_upload', args=[q.id]), {'files': files}, follow=True)
        self.assertContains(r, '3 缺少 .out 檔')
        self.assertEqual([c.input_text for c in q.cases.all()], ['old', '2\n', '10\n'])
        sub.refresh_from_db()
        self.assertEqual([t['status'] for t in sub.test_results], ['error', 'pass', 'pass'])

    def test_upload_case_files_replace(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        Case.objects.create(question=q, input_text='old', expected_output='old')
        self.client.post(reverse('grader:question_cases_upload', args=[q.id]), {
            'replace': 'on', 'files': [SimpleUploadedFile('1.in', b'1'), SimpleUploadedFile('1.out', b'1')]})
        self.assertEqual([c.input_text for c in q.cases.all()], ['1'])

    def test_settings_page_renders(self):
        r = self.client.get(reverse('grader:exam_settings', args=[self.exam.id]))
        self.assertContains(r, '需與檔名 學號_A01.py 的題號相同')

    def test_question_code_uppercased(self):
        self.client.post(reverse('grader:exam_settings', args=[self.exam.id]),
                         settings_post(self.exam, questions=[('a01', '20')]))
        self.assertEqual(self.exam.questions.get().code, 'A01')

    def test_weights_must_sum_100(self):
        r = self.client.post(reverse('grader:exam_settings', args=[self.exam.id]),
                             settings_post(self.exam, weights=[30, 30, 25, 10]))
        self.assertContains(r, '比例加總需為 100%，目前為 95%')

    def test_points_change_invalidates_over_cap(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        sub = Submission.objects.create(question=q, student_id='S1', filename='', code='', graded=True)
        CriterionScore.objects.create(submission=sub, criterion=self.exam.criteria.first(), score=3)
        data = settings_post(self.exam)
        data['q-0-points'] = '10'
        r = self.client.post(reverse('grader:exam_settings', args=[self.exam.id]), data, follow=True)
        self.assertContains(r, '1 份已評分的作答因評分設定變更需複查')
        sub.refresh_from_db()
        self.assertFalse(sub.graded)

    def test_adding_criterion_reopens_graded(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        sub = Submission.objects.create(question=q, student_id='S1', filename='', code='', graded=True)
        data = settings_post(self.exam, weights=[30, 30, 20, 10])
        data.update({'c-TOTAL_FORMS': 5, 'c-4-name': '程式風格', 'c-4-weight': 10, 'c-4-order': 4})
        self.client.post(reverse('grader:exam_settings', args=[self.exam.id]), data)
        self.assertEqual(self.exam.criteria.count(), 5)
        sub.refresh_from_db()
        self.assertFalse(sub.graded)

    def test_time_limit_change_reruns_tests(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20, time_limit=1)
        Case.objects.create(question=q, expected_output='ok\n')
        sub = Submission.objects.create(question=q, student_id='S1', filename='',
                                        code='import time\ntime.sleep(1.5)\nprint("ok")')
        data = settings_post(self.exam)
        data['q-0-time_limit'] = 5
        self.client.post(reverse('grader:exam_settings', args=[self.exam.id]), data)
        sub.refresh_from_db()
        self.assertTrue(sub.tests_passed)

    def test_save_cases_runs_tests(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        sub = Submission.objects.create(question=q, student_id='S1', filename='', code='print(int(input())+1)')
        self.client.post(reverse('grader:question_cases', args=[q.id]), {
            't-TOTAL_FORMS': 1, 't-INITIAL_FORMS': 0, 't-MIN_NUM_FORMS': 0, 't-MAX_NUM_FORMS': 1000,
            't-0-input_text': '1\r\n', 't-0-expected_output': '2\r\n', 't-0-order': 0})
        self.assertEqual(Case.objects.get().input_text, '1\n')
        sub.refresh_from_db()
        self.assertTrue(sub.tests_passed)

    def test_delete_question_confirm_page_counts(self):
        q = Question.objects.create(exam=self.exam, code='A01', points=20)
        Submission.objects.create(question=q, student_id='S1', filename='', code='')
        url = reverse('grader:question_delete', args=[q.id])
        self.assertContains(self.client.get(url), '1 份繳交')
        self.client.post(url)
        self.assertFalse(Question.objects.exists())

    def test_delete_criterion_warns_weight_sum(self):
        url = reverse('grader:criterion_delete', args=[self.exam.criteria.last().id])
        self.assertContains(self.client.post(url, follow=True), '比例加總目前為 85%')


class UploadAndOverviewTests(TestCase):
    def setUp(self):
        self.exam = Exam.create_with_defaults('A')
        self.q = Question.objects.create(exam=self.exam, code='A01', points=20)

    def test_upload_imports_and_shows_warnings(self):
        r = self.client.post(reverse('grader:exam_upload', args=[self.exam.id]), {'files': [
            SimpleUploadedFile('D1_A01.py', b'print(1)'), SimpleUploadedFile('bad.py', b'')]})
        self.assertContains(r, '檔名格式不符')
        self.assertEqual(Submission.objects.count(), 1)

    def test_overview_shows_status(self):
        Question.objects.create(exam=self.exam, code='A02', points=10, order=1)
        Submission.objects.create(question=self.q, student_id='S1', filename='', code='')
        r = self.client.get(reverse('grader:exam_overview', args=[self.exam.id]))
        self.assertContains(r, 'S1 A01：5 分，待人工評分')
        self.assertContains(r, 'class="cell-missing"')
        self.assertContains(r, '<th scope="row" class="col-student">S1</th>', html=False)

    def test_csv_download(self):
        Submission.objects.create(question=self.q, student_id='S1', filename='', code='', tests_passed=True)
        r = self.client.get(reverse('grader:exam_csv', args=[self.exam.id]))
        self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue(r.content.startswith(b'\xef\xbb\xbf'))
        self.assertIn('S1,10,10', r.content.decode('utf-8-sig'))


class ProgressOverviewTests(TestCase):
    def setUp(self):
        self.exam = Exam.create_with_defaults('A')
        self.q = Question.objects.create(exam=self.exam, code='A01', points=20)
        self.url = reverse('grader:exam_overview', args=[self.exam.id])

    def test_export_warns_while_pending_or_review(self):
        Submission.objects.create(question=self.q, student_id='S1', filename='', code='')
        sub = Submission.objects.create(question=self.q, student_id='S2', filename='', code='')
        CriterionScore.objects.create(submission=sub, criterion=self.exam.criteria.first(), score=1)
        r = self.client.get(self.url)
        self.assertContains(r, '尚有 <strong>1</strong> 份待改、<strong>1</strong> 份需複查', html=False)
        self.assertContains(r, 'class="cell-review"')
        self.assertContains(r, reverse('grader:exam_csv', args=[self.exam.id]))

    def test_export_ok_when_complete_and_no_nav_export(self):
        Submission.objects.create(question=self.q, student_id='S1', filename='', code='', graded=True)
        r = self.client.get(self.url)
        self.assertContains(r, '全部改完，可以匯出')
        self.assertContains(r, '已改 1 / 1 份（100%）')
        self.assertNotContains(self.client.get(reverse('grader:exam_settings', args=[self.exam.id])),
                               reverse('grader:exam_csv', args=[self.exam.id]))

    def test_search_target_rows_have_ids(self):
        Submission.objects.create(question=self.q, student_id='D1234567', filename='', code='')
        r = self.client.get(self.url)
        self.assertContains(r, 'id="student-D1234567"')
        self.assertContains(r, '<option value="D1234567">', html=False)


LONG_CODE = '''n = int(input())
total = 0
for i in range(1, n + 1):
    if i % 2 == 0:
        total += i * i
    else:
        total -= i
print(total)
'''


class ReviewPanelTests(TestCase):
    def setUp(self):
        self.exam = Exam.create_with_defaults('A')
        self.q = Question.objects.create(exam=self.exam, code='A01', points=20)
        self.a = Submission.objects.create(question=self.q, student_id='S1', filename='', code=LONG_CODE)
        self.b = Submission.objects.create(question=self.q, student_id='S2', filename='', graded=True,
                                           code=re.sub(r'\bi\b', 'k', LONG_CODE.replace('total', 'acc')))
        Submission.objects.create(question=self.q, student_id='S3', filename='', code='print(1)')
        for c, v in zip(self.exam.criteria.all(), ['3', '2', '2.5', '1.5']):
            CriterionScore.objects.create(submission=self.b, criterion=c, score=v)
        self.url = reverse('grader:grade', args=[self.q.id])

    def test_similar_panel_flags_renamed_copy(self):
        r = self.client.get(self.url + '?student=S1&tab=similar')
        similar = r.context['similar']
        self.assertEqual(similar[0]['sub'].student_id, 'S2')
        self.assertTrue(similar[0]['flagged'])
        self.assertFalse(similar[-1]['comparable'])  # S3 太短
        self.assertContains(r, '疑似抄襲')
        self.assertContains(r, reverse('grader:compare', args=[self.q.id]) + '?a=S1&amp;b=S2', html=False)

    def test_threshold_from_exam_settings(self):
        self.b.code = LONG_CODE.replace('i * i', 'i * i * 2')
        self.b.save()
        r = self.client.get(self.url + '?student=S1')
        pct = r.context['similar'][0]['percent']
        self.assertLess(pct, 100)
        self.assertTrue(r.context['similar'][0]['flagged'])
        Exam.objects.filter(pk=self.exam.pk).update(similarity_threshold=pct + 1)
        self.assertFalse(self.client.get(self.url + '?student=S1').context['similar'][0]['flagged'])

    def test_peer_scores_list_graded_with_breakdown(self):
        r = self.client.get(self.url + '?student=S1&tab=scores')
        peers = r.context['peers']
        self.assertEqual([p['student_id'] for p in peers], ['S2'])
        self.assertEqual(peers[0]['total'], Decimal('14'))  # 測資未過 5 + 人工 9

    def test_compare_page(self):
        r = self.client.get(reverse('grader:compare', args=[self.q.id]) + '?a=S1&b=S2')
        self.assertContains(r, 'S1 ↔ S2')
        self.assertContains(r, '相似度 <strong>100%</strong>', html=False)
        self.assertContains(r, 'class="diff"')

    def test_compare_short_code_not_flagged(self):
        r = self.client.get(reverse('grader:compare', args=[self.q.id]) + '?a=S3&b=S3')
        self.assertContains(r, '程式太短，不判定相似度')
        self.assertNotContains(r, 'class="flag"')

    def test_compare_other_question_is_404(self):
        other_q = Question.objects.create(exam=self.exam, code='A02', points=10)
        Submission.objects.create(question=other_q, student_id='X9', filename='', code='')
        url = reverse('grader:compare', args=[self.q.id])
        self.assertEqual(self.client.get(url + '?a=S1&b=X9').status_code, 404)
        self.assertEqual(self.client.get(url + '?a=S1').status_code, 404)

    def test_compare_escapes_code(self):
        self.a.code = 'print("<script>alert(1)</script>")'
        self.a.save()
        r = self.client.get(reverse('grader:compare', args=[self.q.id]) + '?a=S1&b=S2')
        self.assertNotContains(r, '<script>alert(1)</script>', html=False)

    def test_review_counts_as_pending_for_next(self):
        Submission.objects.filter(student_id='S3').update(graded=True)
        CriterionScore.objects.create(submission=self.a, criterion=self.exam.criteria.first(), score=1)
        # S1 需複查（有分數未 graded），預設應被帶到 S1
        self.assertEqual(self.client.get(self.url).context['current'], 'S1')


class GradeViewTests(TestCase):
    def setUp(self):
        self.exam = Exam.create_with_defaults('A')
        self.q = Question.objects.create(exam=self.exam, code='A01', points=20)
        self.q2 = Question.objects.create(exam=self.exam, code='A02', points=20)
        for sid, graded in (('S1', True), ('S2', False), ('S3', False)):
            Submission.objects.create(question=self.q, student_id=sid, filename='',
                                      code=f'print("{sid}")', graded=graded)
        Submission.objects.create(question=self.q2, student_id='S4', filename='', code='')
        self.url = reverse('grader:grade', args=[self.q.id])

    def scores(self, *values):
        return {f'c{c.id}': v for c, v in zip(self.exam.criteria.all(), values)}

    def test_get_defaults_to_first_pending(self):
        self.assertContains(self.client.get(self.url), 'print(&quot;S2&quot;)')

    def test_post_saves_and_redirects_next(self):
        r = self.client.post(self.url + '?student=S2', self.scores('3', '2.5', '2', '1.5'))
        self.assertRedirects(r, self.url + '?student=S3')
        sub = Submission.objects.get(question=self.q, student_id='S2')
        self.assertTrue(sub.graded)
        self.assertEqual(sum(s.score for s in sub.scores.all()), Decimal('9'))

    def test_post_last_pending_wraps_then_finishes(self):
        Submission.objects.filter(student_id='S2').update(graded=True)
        r = self.client.post(self.url + '?student=S3', self.scores('3', '3', '2.5', '1.5'))
        self.assertRedirects(r, self.url)
        self.assertContains(self.client.get(self.url), '此題已全部改完')

    def test_prefilled_scores_can_be_resubmitted(self):
        sub = Submission.objects.get(question=self.q, student_id='S2')
        for c, v in zip(self.exam.criteria.all(), ['1', '2.5', '2', '1.5']):
            CriterionScore.objects.create(submission=sub, criterion=c, score=v)
        r = self.client.get(self.url + '?student=S2')
        self.assertContains(r, '設定或程式碼已變更，請複查')
        data = {name: r.context['form'][name].value() for name in r.context['form'].fields}
        self.assertRedirects(self.client.post(self.url + '?student=S2', data), self.url + '?student=S3')

    def test_post_over_cap_rejected(self):
        r = self.client.post(self.url + '?student=S2', self.scores('3.5', '3', '2.5', '1.5'))
        self.assertContains(r, '不可超過上限 3')
        self.assertFalse(Submission.objects.get(question=self.q, student_id='S2').graded)

    def test_missing_student_not_gradable(self):
        r = self.client.get(self.url + '?student=S4')
        self.assertContains(r, 'S4 這題未交')
        self.assertNotContains(r, '儲存並下一位')
