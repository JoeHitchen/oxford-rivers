from django.urls import path, include, reverse_lazy
from django.views.generic.base import RedirectView

from . import views

app_name = 'flags'

urlpatterns = [
    path('flags/', include([
        path('<slug:tag>/', views.FlagHistory.as_view(), name = 'flag_history'),
    ])),
    path('', include([
        path('<slug:tag>/', views.AdvisoryHistory.as_view(), name = 'advisory_history'),
        path('', views.advisory_overview, name = 'advisory_overview'),
    ])),
    path('', RedirectView.as_view(  # Dummy view to provide flags 'index' name
        url = reverse_lazy('flags:advisory_overview'),
        permanent = True,
    ), name = 'index'),
]
