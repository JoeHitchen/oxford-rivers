import os
import json


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'ThisMustBeReplaced')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG').lower() == 'true' if 'DJANGO_DEBUG' in os.environ else False

ALLOWED_HOSTS = os.environ.get('DJANGO_HOSTS').split(',') if 'DJANGO_HOSTS' in os.environ else []


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mcp_server',
    'flags',
    'jameson',
    'automation',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'core', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
        'HOST': os.environ.get('DATABASE_HOST', ''),
        'PORT': os.environ.get('DATABASE_PORT', ''),
        'USER': os.environ.get('DATABASE_USER', ''),
        'PASSWORD': os.environ.get('DATABASE_PASS'),
        'NAME': os.environ.get('DATABASE_NAME', 'database.sqlite3'),
        'TEST': {
            'NAME': os.environ.get('DATABASE_NAME_TEST', 'test.sqlite3'),
        },
    },
    'jameson': {
        'ENGINE': os.environ.get('JAMESON_ENGINE', 'django.db.backends.sqlite3'),
        'HOST': os.environ.get('JAMESON_HOST', ''),
        'PORT': os.environ.get('JAMESON_PORT', ''),
        'USER': os.environ.get('JAMESON_USER', ''),
        'PASSWORD': os.environ.get('JAMESON_PASS'),
        'NAME': os.environ.get('JAMESON_NAME', 'database.sqlite3'),
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalisation and localisation

USE_I18N = False
LANGUAGE_CODE = 'en-gb'

USE_TZ = True
TIME_ZONE = 'Europe/London'


# Static files (CSS, JavaScript, Images)

STATIC_BACKEND = os.environ.get(
    'STATIC_BACKEND',
    'django.contrib.staticfiles.storage.StaticFilesStorage',
)
STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR, 'static'))
STATIC_OPTIONS = json.loads(os.environ.get('STATIC_OPTIONS', '{}'))
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'core', 'static')]

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': STATIC_BACKEND, 'OPTIONS': STATIC_OPTIONS},
}

if STATIC_BACKEND.split('.')[0] == 'storages':
    INSTALLED_APPS.append('storages')


# Async tasks
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULTS')

CELERY_BROKER_TRANSPORT_OPTIONS = json.loads(os.environ.get('CELERY_BROKER_OPTIONS', '{}'))
CELERY_WORKER_LOG_FORMAT = '%(processName)-17s %(levelname)-8s %(message)s'


# Emails
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASS', '')
EMAIL_USE_TLS = EMAIL_HOST != 'localhost'
DEFAULT_FROM_EMAIL = 'no-reply@mail.fantasybumps.org.uk'

AUTOFLAG_NOTIFICATION_RECIPIENTS = os.environ.get('AUTOFLAG_NOTIFICATION_RECIPIENTS', '').split(',')  # noqa: E501


# MCP server
DJANGO_MCP_GLOBAL_SERVER_CONFIG = {
    'stateless': True,  # No container/session state to share between requests.
    'instructions': (
        'Oxford Rivers reports the state of the River Thames around Oxford for rowers: '
        'OURCs flags (Isis and Godstow reaches), Jameson stream differentials, EA stream '
        'advisory boards, which transits are permitted, and sun times. '
        'Call get_river_conditions() for exact, current values. '
        'Everything exposed here is read-only and already public on the website.'
    ),
}


# Other
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '%(name)-12s %(levelname)-8s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

