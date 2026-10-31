from django.urls import path

from . import views

app_name = 'grader'

urlpatterns = [
    path('', views.home, name='home'),
    path('folder/new/', views.folder_create, name='folder_create'),
    path('folder/<int:pk>/delete/', views.folder_delete, name='folder_delete'),
    path('exam/new/', views.exam_create, name='exam_create'),
    path('exam/<int:pk>/delete/', views.exam_delete, name='exam_delete'),
    path('exam/<int:pk>/', views.exam_overview, name='exam_overview'),
    path('exam/<int:pk>/settings/', views.exam_settings, name='exam_settings'),
    path('exam/<int:pk>/upload/', views.exam_upload, name='exam_upload'),
    path('exam/<int:pk>/csv/', views.exam_csv, name='exam_csv'),
    path('question/<int:pk>/cases/', views.question_cases, name='question_cases'),
    path('question/<int:pk>/cases/upload/', views.question_cases_upload, name='question_cases_upload'),
    path('question/<int:pk>/rerun/', views.question_rerun, name='question_rerun'),
    path('question/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('question/<int:pk>/grade/', views.grade, name='grade'),
    path('question/<int:pk>/compare/', views.compare, name='compare'),
    path('criterion/<int:pk>/delete/', views.criterion_delete, name='criterion_delete'),
]
