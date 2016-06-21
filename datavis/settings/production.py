#
# datavis.settings.production
#   Django production settings

from .default import *

DEBUG = False

LOG_DIR     = '/var/log/django'
VAR_RUN_DIR = '/var/run/django'
VAR_LIB_DIR = '/var/lib/django'

SECRET_KEY = os.environ.get('EOL_DATAVIS_SECRET_KEY')

if SECRET_KEY == None:
  raise ValueError('EOL_DATAVIS_SECRET_KEY environment variable must be set when running with datavis.settings.production')

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
