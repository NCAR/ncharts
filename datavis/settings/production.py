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
