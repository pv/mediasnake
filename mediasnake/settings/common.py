import os
import django.conf.global_settings as DEFAULT_SETTINGS
from mediasnake.iniconfig import ini

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', ini['data_dir'])
PROJECT_DIR = os.path.join(os.path.dirname(__file__), '..')

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = os.path.join(DATA_DIR, 'media')
STATIC_ROOT = os.path.join(DATA_DIR, 'static')
SENDFILE_ROOT = os.path.join(DATA_DIR, 'streaming')

SENDFILE_BACKEND = 'mediasnake_sendfile.backends.simple'

MEDIA_URL = ini['url_prefix'].rstrip('/') + '/media/'
STATIC_URL = ini['url_prefix'].rstrip('/') + '/static/'
LOGIN_URL = ini['url_prefix'].rstrip('/') + '/login/'
LOGIN_REDIRECT_URL = ini['url_prefix'].rstrip('/') + '/'
SENDFILE_URL = ini['url_prefix'].rstrip('/') + '/streaming/'
MEDIASNAKEFILES_DIRS = ini['video_dirs']

SECRET_KEY = ini['secret_key']
ALLOWED_HOSTS = ini['hostnames']

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
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

MEDIASNAKEFILES_MIMETYPES = (
    "video/*",
)
MEDIASNAKEFILES_TICKET_LIFETIME_HOURS = 3
MEDIASNAKEFILES_FFMPEGTHUMBNAILER = "ffmpegthumbnailer"
