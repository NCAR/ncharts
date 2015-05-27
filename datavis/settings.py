"""
Django settings for datavis project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '6-u3&i0wz1lgpwlq3apf1)&o%niv4gql4iv_ibr2^^e2y#=_=6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True
TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

if DEBUG:
    VAR_RUN_DIR = BASE_DIR
    VAR_LIB_DIR = BASE_DIR
    LOG_DIR = os.path.join(BASE_DIR,'log')
else:
    LOG_DIR = '/var/log/django'
    VAR_RUN_DIR = '/var/run/django'
    VAR_LIB_DIR = '/var/lib/django'

ALLOWED_HOSTS = [ 'datavis', 'datavis.eol.ucar.edu', 'localhost', '128.117.82.210' ]

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.formtools',
    'datetimewidget',
    'ncharts',
)

MIDDLEWARE_CLASSES = (
    # https://docs.djangoproject.com/en/1.7/topics/cache/#order-of-middleware-classes
    # UpdateCacheMiddleware must appear before SessionMiddleware,
    # and LocaleMiddleware FetchFromCacheMiddleware must occur after them.
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'datavis.middleware.InternalUseOnlyMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'datavis.urls'

WSGI_APPLICATION = 'datavis.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(VAR_LIB_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Mountain'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

# URL to use when referring to static files located in STATIC_ROOT
STATIC_URL = '/static/'

# STATIC_ROOT is where "pythyon3 manage.py collectstatic" puts
# the static files it finds.
# See /etc/httpd/conf/vhosts/datavis.conf:
#	Alias /static/ /var/django/eol-django-datavis/static/
STATIC_ROOT = os.path.join(BASE_DIR,'static')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'django_debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'django_debug.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 10, 'utc': False,
            'formatter': 'verbose'
        },
        'django': {
            'level': 'WARNING',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'django.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 10, 'utc': False,
            'formatter': 'verbose'
        },
        'datavis_debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'datavis_debug.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 10, 'utc': False,
            'formatter': 'verbose'
        },
        'datavis': {
            'level': 'WARNING',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'datavis.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 10, 'utc': False,
            'formatter': 'verbose'
        },
        'ncharts': {
            'level': 'WARNING',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'ncharts.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 10, 'utc': False,
            'formatter': 'verbose'
        },
        'ncharts_debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'ncharts_debug.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 10, 'utc': False,
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers':['django','django_debug'],
            'propagate': True,
            'level':'DEBUG',
        },
        'datavis': {
            'handlers':['datavis','datavis_debug'],
            'level':'DEBUG',
        },
        'ncharts': {
            'handlers': ['ncharts_debug','ncharts'],
            'level': 'DEBUG',
        },
    }
}

if not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),
            # 'LOCATION': '127.0.0.1:11211',
            'TIMEOUT': 300, # 300 seconds is the default
        }
    }
    CACME_MIDDLEWARE_ALIAS = 'default'
    CACHE_MIDDLEWARE_SECONDS = 300
    CACHE_MIDDLEWARE_KEY_PREFIX = ''

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

INTERNAL_IPS = ['128.117']

