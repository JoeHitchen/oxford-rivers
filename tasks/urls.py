from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    path('status/<uuid:task_id>/', views.task_status, name = 'status'),
    path('start/', views.task_start, name = 'start'),
    path('', views.index, name = 'index'),
]

