from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from grader.models import Exam, Question, Submission


class ExamModelTests(TestCase):
    def test_create_with_defaults_adds_four_criteria(self):
        exam = Exam.create_with_defaults('A')
        names = [c.name for c in exam.criteria.all()]
        self.assertEqual(names, ['題目需求理解', '核心邏輯與觀念', '功能實作與結果', '程式可執行性'])
        self.assertEqual(sum(c.weight for c in exam.criteria.all()), Decimal('100'))

    def test_submission_unique_per_student_question(self):
        exam = Exam.create_with_defaults('A')
        q = Question.objects.create(exam=exam, code='A01', points=20)
        Submission.objects.create(question=q, student_id='D1', filename='D1_A01.py', code='')
        with self.assertRaises(IntegrityError):
            Submission.objects.create(question=q, student_id='D1', filename='D1_A01.py', code='')
