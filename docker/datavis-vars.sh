#
# ABOUT
#   env vars for datavis.eol.ucar.edu and datavis-dev
#
# USAGE
#   source this file:
#     $ . docker/datavis-vars.sh

export DJANGO_SETTINGS_MODULE=datavis.settings.production
export NCHARTS_LOG_DIR=/var/log/django
export NCHARTS_DB_DIR=/var/lib/django
