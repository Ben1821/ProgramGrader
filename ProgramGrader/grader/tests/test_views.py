from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from grader.models import CriterionScore, Exam, Question, Submission, TestCase as Case


def settings_post(exam, questions=(), weights=None):
    """組出設定頁 formset 的 POST 資料；questions 為 (code, points) 新增列。"""
    data = {'name': exam.name}
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

    def test_create_exam_redirects_to_settings(self):
        r = self.client.post(reverse('grader:exam_list'), {'name': 'B'})
        exam = Exam.objects.get(name='B')
        self.assertRedirects(r, reverse('grader:exam_settings', args=[exam.id]))
        self.assertEqual(exam.criteria.count(), 4)

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
        self.assertContains(r, '✋待改')
        self.assertContains(r, '未交')

    def test_csv_download(self):
        Submission.objects.create(question=self.q, student_id='S1', filename='', code='', tests_passed=True)
        r = self.client.get(reverse('grader:exam_csv', args=[self.exam.id]))
        self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8')
        self.assertTrue(r.content.startswith(b'\xef\xbb\xbf'))
        self.assertIn('S1,10,10', r.content.decode('utf-8-sig'))


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
