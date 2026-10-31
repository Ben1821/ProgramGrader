from django.urls import path

from . import views

app_name = 'grader'

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('exam/<int:pk>/', views.exam_overview, name='exam_overview'),
    path('exam/<int:pk>/settings/', views.exam_settings, name='exam_settings'),
    path('exam/<int:pk>/upload/', views.exam_upload, name='exam_upload'),
    path('exam/<int:pk>/csv/', views.exam_csv, name='exam_csv'),
    path('question/<int:pk>/cases/', views.question_cases, name='question_cases'),
    path('question/<int:pk>/rerun/', views.question_rerun, name='question_rerun'),
    path('question/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('question/<int:pk>/grade/', views.grade, name='grade'),
    path('criterion/<int:pk>/delete/', views.criterion_delete, name='criterion_delete'),
]
