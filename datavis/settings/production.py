#
# datavis.settings.production
#   Django production settings

from .default import *

DEBUG = False

os.environ.setdefault("VAR_DIR", "/var")
VAR_DIR = os.environ.get('VAR_DIR')

DEFAULT_LOG_DIR = LOG_DIR

LOG_DIR = os.path.join(VAR_DIR, 'log/django')
PROD_LOG_LEVEL = 'WARNING'

#VAR_RUN_DIR = os.path.join(VAR_DIR, 'run/django')
VAR_RUN_DIR = "/run/django"
VAR_LIB_DIR = os.path.join(VAR_DIR, 'lib/django')

# Update path to database if sqlite is used
if 'sqlite' in DATABASES['default']['ENGINE']:
    DATABASES['default']['NAME'] = os.path.join(VAR_LIB_DIR, 'db.sqlite3')

SECRET_KEY = os.environ.get('EOL_DATAVIS_SECRET_KEY')

if SECRET_KEY is None:
    raise ValueError('EOL_DATAVIS_SECRET_KEY environment variable must be set when running with datavis.settings.production')

#
# django may generate log messages such as:
#   Invalid HTTP_HOST header: 'www.baidu.com'.
#   You may need to add 'www.baidu.com' to ALLOWED_HOSTS.
#
# However, don't follow that advice to add those external host
# names to ALLOWED_HOSTS!
# Hacked sites may have a link to this site, but as I understand it,
# the redirect may contain an HTTP packet with an altered HTTP_HOST
# and SERVER_NAME, hoping that a dumb server, thinking HTTP_HOST
# is itself, will use it in its own redirects and <script> statemtents.
# The latter could result in an import of hacker code on a
# client's browser. Setting ALLOWED_HOSTS to the various names for datavis will
# result in packets being ignored if they contain other than the following:
#
ALLOWED_HOSTS = ['datavis', 'datavis.eol.ucar.edu', 'datavis-dev.eol.ucar.edu', 'localhost', '128.117.82.210']

# People who should receive emails of ERRORs
ADMINS = (
    ('Isabel Suhr', 'isabels@ucar.edu'),
    ('Gary Granger', 'granger@ucar.edu'),
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR, 'django_memcached.sock'),
        # 'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 300, # 300 seconds is the default
    }
}

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = ''

if LOG_DIR != DEFAULT_LOG_DIR:
    #
    # iterate over LOGGING['handlers'] and update filenames w/ new LOG_DIR
    # and set level to PROD_LOG_LEVEL, except for mail_admins handler
    #
    for key, value in LOGGING['handlers'].items():
        if 'filename' in value:
            value['filename'] = value['filename'].replace(DEFAULT_LOG_DIR, LOG_DIR)

        if key != 'mail_admins' and key != 'requests' and 'level' in value:
            value['level'] = PROD_LOG_LEVEL

    for key, value in LOGGING['loggers'].items():

        if key != 'ncharts.views.requests' and 'level' in value:
            value['level'] = PROD_LOG_LEVEL
