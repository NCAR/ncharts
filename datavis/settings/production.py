#
# datavis.settings.production
#   Django production settings

from .default import *

DEBUG = False

DEFAULT_LOG_DIR = LOG_DIR

LOG_DIR     = os.getenv('DATAVIS_LOG_DIR',     '/var/log/django')
LOG_LEVEL   = os.getenv('DATAVIS_LOG_LEVEL',   'WARNING')

VAR_RUN_DIR = os.getenv('DATAVIS_VAR_RUN_DIR', '/var/run/django')

DB_DIR      = os.getenv('DATAVIS_DB_DIR',      BASE_DIR)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DB_DIR, 'db.sqlite3'),
        'OPTIONS': {'timeout': 20,},
    }
}

SECRET_KEY = os.environ.get('EOL_DATAVIS_SECRET_KEY')

if SECRET_KEY == None:
  raise ValueError('EOL_DATAVIS_SECRET_KEY environment variable must be set when running with datavis.settings.production')

#
# Don't add those external host names to ALLOWED_HOSTS!
# Hacked sites may have a link to this site, but as I understand it, the redirect
# may contain an HTTP packet with an altered HTTP_HOST and SERVER_NAME, hoping that
# a dumb server, thinking HTTP_HOST is itself, will use it in its own redirects and
# <script> statemtents.  The latter could result in an import of hacker code on a
# client's browser. Setting ALLOWED_HOSTS to the various names for datavis will
# result in packets being ignored if they contain other than the following:
#
ALLOWED_HOSTS = ['datavis', 'datavis.eol.ucar.edu', 'datavis-dev.eol.ucar.edu', 'localhost', 'local.docker', '128.117.82.210']

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR, 'django_memcached.sock'),
        # 'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 300, # 300 seconds is the default
    }
}

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = ''

#
# iterate over LOGGING['handlers'] and update filenames w/ new LOG_DIR and
# LOG_LEVEL, as needed
#

for key, value in LOGGING['handlers'].items():
  if 'filename' in value and LOG_DIR != DEFAULT_LOG_DIR:
    value['filename'] = value['filename'].replace(DEFAULT_LOG_DIR, LOG_DIR)

  if 'level' in value:
    value['level'] = LOG_LEVEL
