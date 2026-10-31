from decimal import Decimal as D

from django.test import TestCase

from grader.models import CriterionScore, Exam, Question, Submission
from grader.scoring import (cell_status, criterion_cap, fmt, invalidate_over_cap, progress,
                            question_score, student_rows, test_score)


def make_sub(question, student, passed=True, graded=False, scores=()):
    sub = Submission.objects.create(question=question, student_id=student, filename='',
                                    code='', tests_passed=passed, graded=graded)
    for criterion, s in zip(question.exam.criteria.all(), scores):
        CriterionScore.objects.create(submission=sub, criterion=criterion, score=s)
    return sub


class ScoringTests(TestCase):
    def setUp(self):
        self.exam = Exam.create_with_defaults('A')
        self.q1 = Question.objects.create(exam=self.exam, code='A01', points=20, order=0)
        self.q2 = Question.objects.create(exam=self.exam, code='A02', points=10, order=1)

    def test_test_score(self):
        self.assertEqual(test_score(D('20'), True), D('10'))
        self.assertEqual(test_score(D('20'), False), D('5'))
        self.assertEqual(test_score(D('5'), False), D('1.25'))

    def test_criterion_cap(self):
        self.assertEqual(criterion_cap(D('20'), D('30')), D('3'))
        self.assertEqual(criterion_cap(D('20'), D('15')), D('1.5'))

    def test_question_score_missing_is_zero(self):
        self.assertEqual(question_score(None), D('0'))

    def test_question_score_sums(self):
        sub = make_sub(self.q1, 'S1', passed=True, graded=True, scores=[3, 3, D('2.5'), D('1.5')])
        self.assertEqual(question_score(sub), D('20'))

    def test_question_score_failed(self):
        sub = make_sub(self.q1, 'S1', passed=False, graded=True, scores=[3, 3, D('2.5'), D('1.5')])
        self.assertEqual(question_score(sub), D('15'))

    def test_pending_ignores_prefilled_scores(self):
        sub = make_sub(self.q1, 'S1', passed=True, graded=False, scores=[3, 3, D('2.5'), D('1.5')])
        self.assertEqual(question_score(sub), D('10'))

    def test_cell_status(self):
        self.assertEqual(cell_status(None), 'missing')
        self.assertEqual(cell_status(make_sub(self.q1, 'S1', graded=True)), 'done')
        self.assertEqual(cell_status(make_sub(self.q1, 'S2')), 'pending')

    def test_cell_status_review_when_reopened_with_scores(self):
        self.assertEqual(cell_status(make_sub(self.q1, 'S3', graded=False, scores=[1])), 'review')

    def test_progress_counts(self):
        make_sub(self.q1, 'S1', graded=True)
        make_sub(self.q1, 'S2', graded=False, scores=[1])
        make_sub(self.q2, 'S2')
        p = progress(student_rows(self.exam), [self.q1, self.q2])
        q1, q2 = p['questions']
        self.assertEqual((q1['done'], q1['review'], q1['pending'], q1['missing'], q1['percent']), (1, 1, 0, 0, 50))
        self.assertEqual((q2['pending'], q2['missing']), (1, 1))
        self.assertEqual((p['total']['done'], p['total']['submitted'], p['total']['percent']), (1, 3, 33))
        self.assertFalse(student_rows(self.exam)[1]['complete'])

    def test_fmt(self):
        self.assertEqual(fmt(D('12.50')), '12.5')
        self.assertEqual(fmt(D('10.00')), '10')
        self.assertEqual(fmt(D('1.25')), '1.25')
        self.assertEqual(fmt(D('0')), '0')

    def test_student_rows_total_and_complete(self):
        make_sub(self.q1, 'S2', passed=True, graded=True, scores=[3, 3, D('2.5'), D('1.5')])
        make_sub(self.q2, 'S1', passed=False)
        rows = student_rows(self.exam)
        self.assertEqual([r['student_id'] for r in rows], ['S1', 'S2'])
        s1, s2 = rows
        self.assertEqual([c[3] for c in s1['cells']], ['missing', 'pending'])
        self.assertEqual(s1['total'], D('2.5'))
        self.assertFalse(s1['complete'])
        self.assertEqual(s2['total'], D('20'))
        self.assertTrue(s2['complete'])

    def test_invalidate_over_cap(self):
        sub = make_sub(self.q1, 'S1', graded=True, scores=[3, 3, D('2.5'), D('1.5')])
        self.q1.points = 10
        self.q1.save()
        self.assertEqual(invalidate_over_cap(self.exam), 1)
        sub.refresh_from_db()
        self.assertFalse(sub.graded)
        self.assertEqual(question_score(sub), D('5'))
