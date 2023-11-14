import os

from django.urls import path, include, reverse_lazy
from django.conf.urls.static import static
from django.views.generic.base import TemplateView, RedirectView

from . import settings


urlpatterns = [
    path('robots.txt', TemplateView.as_view(template_name = 'core/robots.txt')),
    path('', include('flags.urls')),
    path('', RedirectView.as_view(  # Dummy view to provide site 'index' name
        url = reverse_lazy('flags:index'),
        permanent = True,
    ), name = 'index'),
]


if settings.DEBUG:
    urlpatterns += static(
        'favicon.ico',
        document_root = os.path.join(settings.BASE_DIR, 'core', 'static', 'favicon.ico'),
    )
    urlpatterns += static(
        'robots.txt',
        document_root = os.path.join(settings.BASE_DIR, 'core', 'static', 'robots.txt'),
    )

