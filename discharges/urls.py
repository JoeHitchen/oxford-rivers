from django.urls import path

from . import views

app_name = 'discharges'

urlpatterns = [
    path('discharges/', views.History.as_view(), name = 'history'),
]
