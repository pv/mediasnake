from .common import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATA_DIR, 'develop.db'),
    }
}

SECRET_KEY = 'f_estp&amp;wj#_#d0b@(z=d6&amp;6_ayeb6%_065d*q1lj&amp;bldzv-2n^'

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

try:
    from .local_settings import *
except ImportError:
    pass
