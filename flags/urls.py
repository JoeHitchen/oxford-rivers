from django.urls import path, include

from . import views

app_name = 'flags'

urlpatterns = [
    path('flags/', include([
        path('<slug:tag>/', views.FlagHistory.as_view(), name = 'flag_history'),
    ])),
    path('', include([
        path('<slug:tag>/', views.AdvisoryHistory.as_view(), name = 'advisory_history'),
    ])),
    path('', views.Index.as_view(), name = 'index'),
]
