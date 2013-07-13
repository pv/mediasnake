from .common import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',           # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(DATA_DIR, 'production.db'),  # Or path to database file if using sqlite3.
        'USER': '',                                       # Not used with sqlite3.
        'PASSWORD': '',                                   # Not used with sqlite3.
        'HOST': '',                                       # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                                       # Set to empty string for default. Not used with sqlite3.
    }
}

SECRET_KEY = ''

ALLOWED_HOSTS = []
