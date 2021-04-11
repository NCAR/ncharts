#! /bin/bash

# Script suitable for cron to clear sessions from the running django
# ncharts on datavis.

cd /var/django/ncharts
source key.sh
source ../virtualenv/django/bin/activate
# echo $EOL_DATAVIS_SECRET_KEY
./manage.py clearsessions
./manage.py clear_clients
