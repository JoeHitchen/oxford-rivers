from django.urls import path

from . import views

app_name = 'flags'

urlpatterns = [
    path('<slug:tag>/', views.AdvisoryHistory.as_view(), name = 'advisory_history'),
    path('', views.index, name = 'index'),
]
