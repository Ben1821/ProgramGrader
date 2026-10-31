from django.db import models

DEFAULT_CRITERIA = [
    ('題目需求理解', 30, '是否理解題目要求，知道需要完成哪些功能'),
    ('核心邏輯與觀念', 30, '計算公式、條件判斷、程式流程是否正確'),
    ('功能實作與結果', 25, '是否完成指定功能，輸出是否符合預期'),
    ('程式可執行性', 15, '是否存在語法錯誤、變數錯誤或其他執行問題'),
]


class Exam(models.Model):
    name = models.CharField('考卷名稱', max_length=100, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def create_with_defaults(cls, name):
        exam = cls.objects.create(name=name)
        Criterion.objects.bulk_create(
            Criterion(exam=exam, name=n, weight=w, description=d, order=i)
            for i, (n, w, d) in enumerate(DEFAULT_CRITERIA)
        )
        return exam


class Criterion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='criteria')
    name = models.CharField('項目名稱', max_length=100)
    weight = models.DecimalField('比例 (%)', max_digits=5, decimal_places=2)
    description = models.TextField('說明', blank=True)
    order = models.PositiveIntegerField('順序', default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    code = models.CharField('題號', max_length=50)
    points = models.DecimalField('配分', max_digits=6, decimal_places=2)
    time_limit = models.PositiveIntegerField('時間限制（秒）', default=5)
    order = models.PositiveIntegerField('順序', default=0)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('exam', 'code')]

    def __str__(self):
        return self.code


class TestCase(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='cases')
    input_text = models.TextField('輸入', blank=True)
    expected_output = models.TextField('預期輸出', blank=True)
    order = models.PositiveIntegerField('順序', default=0)

    class Meta:
        ordering = ['order', 'id']


class Submission(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='submissions')
    student_id = models.CharField('學號', max_length=50)
    filename = models.CharField(max_length=500)
    code = models.TextField()
    tests_passed = models.BooleanField(default=False)
    test_results = models.JSONField(default=list)
    graded = models.BooleanField(default=False)
    comment = models.TextField('評語', blank=True)

    class Meta:
        ordering = ['student_id']
        unique_together = [('question', 'student_id')]


class CriterionScore(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='scores')
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE, related_name='scores')
    score = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = [('submission', 'criterion')]
