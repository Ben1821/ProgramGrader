from django.test import TestCase

from grader.models import Exam, Question, Submission, TestCase as Case
from grader.runner import normalize, run_case, run_submission


class RunCaseTests(TestCase):
    def test_prompt_ignored(self):
        r = run_case('n = int(input("請輸入數字："))\nprint(n * 2)', '21\n', 5)
        self.assertEqual(r['status'], 'ok')
        self.assertEqual(normalize(r['output']), '42')

    def test_normalize(self):
        self.assertEqual(normalize('a  \nb\n\n\n'), 'a\nb')
        self.assertEqual(normalize('a\r\nb\r\n'), 'a\nb')

    def test_timeout(self):
        self.assertEqual(run_case('while True: pass', '', 1)['status'], 'timeout')

    def test_eof_is_error(self):
        self.assertEqual(run_case('input()\ninput()', '1\n', 5)['status'], 'error')

    def test_syntax_error(self):
        r = run_case('print(', '', 5)
        self.assertEqual(r['status'], 'error')
        self.assertIn('SyntaxError', r['stderr'])

    def test_endless_output_is_stopped(self):
        r = run_case('while True: print("x" * 100)', '', 5)
        self.assertIn(r['status'], ('error', 'timeout'))

    def test_unicode_output(self):
        self.assertEqual(normalize(run_case('print("中文")', '', 5)['output']), '中文')


class RunSubmissionTests(TestCase):
    def setUp(self):
        exam = Exam.create_with_defaults('A')
        self.q = Question.objects.create(exam=exam, code='A01', points=20)
        self.sub = Submission.objects.create(question=self.q, student_id='S1', filename='',
                                             code='print(int(input()) * 2)')

    def test_run_submission_sets_flags(self):
        Case.objects.create(question=self.q, input_text='2\n', expected_output='4\n', order=0)
        Case.objects.create(question=self.q, input_text='3\n', expected_output='7\n', order=1)
        run_submission(self.sub)
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.tests_passed)
        self.assertEqual([r['status'] for r in self.sub.test_results], ['pass', 'fail'])
        self.assertEqual(self.sub.test_results[1]['expected'], '7\n')

    def test_long_output_compared_in_full_but_stored_truncated(self):
        self.sub.code = 'for i in range(500): print("line", i)'
        Case.objects.create(question=self.q, expected_output=''.join(f'line {i}\n' for i in range(500)))
        run_submission(self.sub)
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.tests_passed)
        self.assertEqual(len(self.sub.test_results[0]['output']), 2000)

    def test_run_submission_no_cases_passes(self):
        run_submission(self.sub)
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.tests_passed)
        self.assertEqual(self.sub.test_results, [])
