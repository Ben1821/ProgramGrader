import random

from django.test import SimpleTestCase, TestCase

from grader.models import Exam, Question, Submission
from grader.similarity import MIN_TOKENS, similar_submissions, similarity, tokens

ORIGINAL = '''
# 計算總和
n = int(input("請輸入："))
total = 0
for i in range(1, n + 1):
    if i % 2 == 0:
        total += i * i
    else:
        total -= i
print("答案是", total)
'''

RENAMED = '''
count = int(input("請輸入："))   # 改了變數名、註解和空白
s = 0
for k in range(1, count + 1):
    if k % 2 == 0:
        s += k * k
    else:
        s -= k

print("答案是", s)
'''

DIFFERENT = '''
data = list(map(int, input().split()))
best = max(data)
while best > 0:
    best //= 3
    print(best)
'''


class SimilarityTests(SimpleTestCase):
    def test_renamed_variables_comments_and_spacing_are_ignored(self):
        self.assertEqual(similarity(tokens(ORIGINAL), tokens(RENAMED)), 100)

    def test_different_programs_score_low(self):
        self.assertLess(similarity(tokens(ORIGINAL), tokens(DIFFERENT)), 60)

    def test_builtins_and_keywords_are_kept(self):
        t = tokens('print(len(x))')
        self.assertIn('print', t)
        self.assertIn('len', t)
        self.assertNotIn('x', t)

    def test_syntax_error_falls_back(self):
        t = tokens('def f(:\n  return 1  # 註解\n')
        self.assertTrue(t)
        self.assertNotIn('註解', ' '.join(t))

    def test_short_programs_are_short(self):
        self.assertLess(len(tokens('print(1)')), MIN_TOKENS)
        self.assertGreaterEqual(len(tokens(ORIGINAL)), MIN_TOKENS)

    def test_lone_carriage_return_with_unicode(self):
        for code in ('a\r中', 'é \ré:\t}a=', 'x = "中"\r\nprint(x)\r\n'):
            self.assertIsInstance(tokens(code), list)

    def test_fallback_normalizes_names(self):
        broken_a = 'def f(:\n  total = total + 1\n'
        broken_b = 'def g(:\n  acc = acc + 1\n'
        self.assertEqual(similarity(tokens(broken_a), tokens(broken_b)), 100)

    def test_empty(self):
        self.assertEqual(similarity([], []), 0)


class SimilarSubmissionsTests(TestCase):
    def test_pruned_top_matches_brute_force(self):
        exam = Exam.create_with_defaults('A')
        q = Question.objects.create(exam=exam, code='A01', points=10)
        random.seed(3)
        bodies = [ORIGINAL, RENAMED, DIFFERENT]
        subs = []
        for n in range(40):
            lines = random.choice(bodies).strip().splitlines()
            random.shuffle(lines[1:3])
            extra = '\n'.join(f'v{n}_{k} = {k}' for k in range(n % 5))
            subs.append(Submission.objects.create(question=q, student_id=f'S{n:02d}', filename='',
                                                  code='\n'.join(lines) + '\n' + extra))
        Submission.objects.create(question=q, student_id='TINY', filename='', code='print(1)')
        me = subs[0]
        got = similar_submissions(me, limit=5)
        brute = sorted(((o, similarity(tokens(me.code), tokens(o.code))) for o in subs[1:]),
                       key=lambda r: r[1], reverse=True)[:5]
        self.assertEqual([p for _, p, _ in got], [p for _, p in brute])
        self.assertTrue(all(ok for _, _, ok in got))

    def test_short_ones_fill_remaining_slots(self):
        exam = Exam.create_with_defaults('A')
        q = Question.objects.create(exam=exam, code='A01', points=10)
        me = Submission.objects.create(question=q, student_id='S1', filename='', code=ORIGINAL)
        Submission.objects.create(question=q, student_id='S2', filename='', code=RENAMED)
        Submission.objects.create(question=q, student_id='S3', filename='', code='print(1)')
        got = similar_submissions(me)
        self.assertEqual([(o.student_id, ok) for o, _, ok in got], [('S2', True), ('S3', False)])
