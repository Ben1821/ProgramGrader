from django.test import TestCase

from grader.importer import import_files, parse_filename
from grader.models import CriterionScore, Exam, Question, Submission, TestCase as Case


class ParseFilenameTests(TestCase):
    def test_parse_filename(self):
        self.assertEqual(parse_filename('x/y/D1234567_A01.py'), ('D1234567', 'A01'))
        self.assertEqual(parse_filename('d1234567_a01.py'), ('D1234567', 'A01'))
        self.assertIsNone(parse_filename('D1234567-A01.py'))
        self.assertIsNone(parse_filename('D1234567_A01.txt'))


class ImportFilesTests(TestCase):
    def setUp(self):
        self.exam = Exam.create_with_defaults('A')
        self.q = Question.objects.create(exam=self.exam, code='A01', points=20)
        Case.objects.create(question=self.q, input_text='', expected_output='1\n')

    def sub(self, student):
        return Submission.objects.get(question=self.q, student_id=student)

    def test_imports_and_runs_tests(self):
        report = import_files(self.exam, [('dir/S1_A01.py', b'print(1)')])
        self.assertEqual((report.created, report.students), (1, {'S1'}))
        self.assertTrue(self.sub('S1').tests_passed)

    def test_case_insensitive(self):
        import_files(self.exam, [('d1234567_a01.py', b'print(1)')])
        self.assertEqual(self.sub('D1234567').filename, 'd1234567_a01.py')

    def test_decodes_big5_and_bom(self):
        import_files(self.exam, [
            ('S1_A01.py', '# 中文\nprint(1)'.encode('cp950')),
            ('S2_A01.py', b'\xef\xbb\xbf' + '# 中文\nprint(1)'.encode('utf-8')),
        ])
        for s in ('S1', 'S2'):
            self.assertTrue(self.sub(s).code.startswith('# 中文'))
            self.assertTrue(self.sub(s).tests_passed)

    def test_warnings(self):
        report = import_files(self.exam, [
            ('d/bad-name.py', b''),
            ('d/S1_B09.py', b''),
            ('d1/S2_A01.py', b'print(0)'),
            ('d2/S2_A01.py', b'print(1)'),
            ('d/.DS_Store', b''),
        ])
        self.assertEqual(len(report.warnings), 3)
        self.assertIn('檔名格式不符', report.warnings[0])
        self.assertIn('找不到題目 B09', report.warnings[1])
        self.assertIn('d2/S2_A01.py', report.warnings[2])
        self.assertEqual(self.sub('S2').code, 'print(1)')

    def test_reupload_merges_and_keeps_scores(self):
        import_files(self.exam, [('S1_A01.py', b'print(0)'), ('S2_A01.py', b'print(1)')])
        s1 = self.sub('S1')
        CriterionScore.objects.create(submission=s1, criterion=self.exam.criteria.first(), score=3)
        Submission.objects.filter(pk=s1.pk).update(graded=True)

        report = import_files(self.exam, [('S1_A01.py', b'print(1)')])
        s1.refresh_from_db()
        self.assertEqual(report.updated, 1)
        self.assertFalse(s1.graded)
        self.assertTrue(s1.tests_passed)
        self.assertEqual(s1.scores.count(), 1)
        self.assertTrue(Submission.objects.filter(student_id='S2').exists())

    def test_reupload_same_code_unchanged(self):
        import_files(self.exam, [('S1_A01.py', b'print(1)')])
        Submission.objects.update(graded=True)
        report = import_files(self.exam, [('S1_A01.py', b'print(1)')])
        self.assertEqual(report.unchanged, 1)
        self.assertTrue(self.sub('S1').graded)
