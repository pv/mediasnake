import os
import django.conf.global_settings as DEFAULT_SETTINGS
from mediasnake.iniconfig import ini

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.abspath(os.path.join(PROJECT_DIR, '..', ini['data_dir']))

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = os.path.join(DATA_DIR, 'media')
STATIC_ROOT = os.path.join(DATA_DIR, 'static')
SENDFILE_ROOT = os.path.join(DATA_DIR, 'streaming')

if ini['file_serving'] == 'nginx':
    SENDFILE_BACKEND = 'mediasnake_sendfile.backends.nginx'
else:
    SENDFILE_BACKEND = 'mediasnake_sendfile.backends.simple'

URL_PREFIX = ini['url_prefix']
MEDIA_URL = ini['url_prefix'].rstrip('/') + '/media/'
STATIC_URL = ini['url_prefix'].rstrip('/') + '/static/'
LOGIN_URL = ini['url_prefix'].rstrip('/') + '/login/'
LOGIN_REDIRECT_URL = ini['url_prefix'].rstrip('/') + '/'
SENDFILE_URL = ini['url_prefix'].rstrip('/') + '/streaming/'
MEDIASNAKEFILES_DIRS = ini['video_dirs']

SECRET_KEY = ini['secret_key']
ALLOWED_HOSTS = ini['hostnames']

MEDIASNAKEFILE_HTTP_ADDRESS = ini['http_streaming_address'].strip()
if MEDIASNAKEFILE_HTTP_ADDRESS:
    SESSION_COOKIE_SECURE = True

DEBUG = ini['debug']
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',           # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(DATA_DIR, 'mediasnake.db'),  # Or path to database file if using sqlite3.
        'USER': '',                                       # Not used with sqlite3.
        'PASSWORD': '',                                   # Not used with sqlite3.
        'HOST': '',                                       # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                                       # Set to empty string for default. Not used with sqlite3.
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(ini['data_dir'], 'django_cache'),
    }
}

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

if MEDIASNAKEFILE_HTTP_ADDRESS:
    MIDDLEWARE_CLASSES += ('mediasnake.middleware.SSLEnforcer',)

ROOT_URLCONF = 'mediasnake.urls'

WSGI_APPLICATION = 'mediasnake.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates')
)

TEMPLATE_CONTEXT_PROCESSORS = DEFAULT_SETTINGS.TEMPLATE_CONTEXT_PROCESSORS + (
    'mediasnake.context_processors.global_template_variables',
    'django.core.context_processors.request',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'mediasnake_sendfile',
    'mediasnakefiles',
    'south',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s [%(module)s %(process)d %(thread)d] %(message)s'
        },
        'simple': {
            'format': '%(levelname)s [%(asctime)s] %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(DATA_DIR, 'mediasnake.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
        'mediasnake': {
            'handlers': ['mail_admins', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        }
    }
}

MEDIASNAKEFILES_MIMETYPES = (
    "video/*",
)
MEDIASNAKEFILES_TICKET_LIFETIME_HOURS = 3
MEDIASNAKEFILES_FFMPEGTHUMBNAILER = "ffmpegthumbnailer"
