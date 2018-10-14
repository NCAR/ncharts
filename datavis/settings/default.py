"""
Django settings for datavis project.

Default / development settings. For production settings, use production.py

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# formerly datavis/settings.py

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import socket
import getpass

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'abc-123-this-value-is-totally-insecure'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

VAR_RUN_DIR = BASE_DIR
VAR_LIB_DIR = BASE_DIR
LOG_DIR = os.path.join(BASE_DIR, 'log')

# ALLOWED_HOSTS are the server's IP names, NOT the names of allowed client hosts
# (seems like an unfortunate variable name).
# You may see log errors such as:
# Invalid HTTP_HOST header: 'www.baidu.com'. You may need to add 'www.baidu.com' to ALLOWED_HOSTS.
#
# Don't add those external host names to ALLOWED_HOSTS!
# Hacked sites may have a link to this site, but as I understand it, the redirect
# may contain an HTTP packet with an altered HTTP_HOST and SERVER_NAME, hoping that
# a dumb server, thinking HTTP_HOST is itself, will use it in its own redirects and
# <script> statemtents.  The latter could result in an import of hacker code on a
# client's browser. Setting ALLOWED_HOSTS to the various names for datavis will
# result in packets being ignored if they contain other than the following:

#
# don't restrict hosts in default settings / development environment
# restrict hosts in production.py
#
ALLOWED_HOSTS = ['*']

# Application definition

# In django, an app is: "a Python package that is specifically intended
# for use in a Django project".
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.formtools',
    'datetimewidget',
    'timezone_field',
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

# TEMPLATE_DEBUG = True
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'datavis', 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ROOT_URLCONF = 'datavis.urls'

WSGI_APPLICATION = 'datavis.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(VAR_LIB_DIR, 'db.sqlite3'),
        'OPTIONS': {'timeout': 60,},
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
#	Alias /static/ /var/django/ncharts/static/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# People who should receive emails of ERRORs
ADMINS = (
    # ('Gordon Maclean', 'maclean@ucar.edu'),
)
EMAIL_HOST = "smtp.eol.ucar.edu"
# Email address they appear to come from
SERVER_EMAIL = getpass.getuser() + '@' + socket.getfqdn()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%Y-%m-%d %H:%M:%S"
        },
        'request': {
            'format': '%(asctime)s, %(message)s',
            'datefmt' : "%Y-%m-%d %H:%M:%S"
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',   # changed in production.py
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'django.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 10, 'utc': False,
            'formatter': 'verbose'
        },
        'requests': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'nchart_reqests.log'),
            'when': 'W6', 'interval': 1, 'backupCount': 0, 'utc': False,
            'formatter': 'request'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        # django logger mails error events to admins when DEBUG=False
        # and propagate=True here. We'll set propagate=False
        # and configure it ourselves.
        'django': {
            'handlers':['file', 'mail_admins'],
            'level':'DEBUG',   # changed in production.py
            'propagate': False,
        },
        'datavis': {
            'handlers':['file', 'mail_admins'],
            'level':'DEBUG',   # changed in production.py
        },
        'ncharts': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',   # changed in production.py
        },
        'ncharts.views.requests': {
            'handlers': [ 'requests' ],
            'level': 'INFO',
            'propagate': False, # don't pass on to ncharts logger
        },
        # django correctly prevents DisallowedHost accesses.
        # Just put them in the log file, don't email
        # Don't propagate to 'django' logger
        'django.security.DisallowedHost': {
            'handlers': ['file'],
            'level': 'DEBUG',   # changed in production.py
            'propagate': False, # don't pass on to django logger
        },
        # Put CSRF errors in log file, don't email. When nessus
        # is run, many CSRF errors are generated.
        # django versions < 1.11 log CSRF failures to django.request
        'django.security.csrf': {
            'handlers': ['file'],
            'level': 'DEBUG',   # changed in production.py
            'propagate': False, # don't pass on to django logger
        },
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

INTERNAL_IPS = ['128.117']
