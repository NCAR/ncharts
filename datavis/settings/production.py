#
# datavis.settings.production
#   Django production settings

from .default import *

DEBUG = False

LOG_DIR     = '/var/log/django'
VAR_RUN_DIR = '/var/run/django'
VAR_LIB_DIR = '/var/lib/django'
