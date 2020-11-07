import os

from django.urls import path, include
from django.conf.urls.static import static

from . import settings


urlpatterns = [
    path('', include('flags.urls')),
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

