import csv
import io

from django.test import TestCase

from grader.export import build_csv
from grader.models import CriterionScore, Exam, Question, Submission


class BuildCsvTests(TestCase):
    def test_build_csv(self):
        exam = Exam.create_with_defaults('A')
        q1 = Question.objects.create(exam=exam, code='A01', points=20, order=0)
        q2 = Question.objects.create(exam=exam, code='A02', points=10, order=1)
        s1 = Submission.objects.create(question=q1, student_id='S1', filename='', code='',
                                       tests_passed=True, graded=True)
        for c, score in zip(exam.criteria.all(), ['3', '3', '2.5', '1.5']):
            CriterionScore.objects.create(submission=s1, criterion=c, score=score)
        Submission.objects.create(question=q1, student_id='S2', filename='', code='', tests_passed=False)
        Submission.objects.create(question=q2, student_id='S2', filename='', code='', tests_passed=True)

        text = build_csv(exam)
        self.assertTrue(text.startswith('﻿'))
        rows = list(csv.reader(io.StringIO(text.lstrip('﻿'))))
        self.assertEqual(rows, [['學號', 'A01', 'A02', '總分'],
                                ['S1', '20', '0', '20'],
                                ['S2', '5', '5', '10']])
