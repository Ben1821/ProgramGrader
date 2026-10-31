from django.contrib import admin

from . import models

for m in (models.Exam, models.Criterion, models.Question, models.TestCase,
          models.Submission, models.CriterionScore):
    admin.site.register(m)
