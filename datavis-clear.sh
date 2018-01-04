#! /bin/sh

# Script suitable for cron to clear sessions from the running django
# ncharts on datavis.
keyfile=/etc/systemd/system/httpd.service.d/datavis-secret-key.conf 
cd /var/django/ncharts
source ../virtualenv/django/bin/activate
export DJANGO_SETTINGS_MODULE=datavis.settings.production
eval export `grep EOL_DATAVIS_SECRET_KEY $keyfile | sed -e 's/^.*\"EOL/EOL/' -e 's/\"$//'`
# echo $EOL_DATAVIS_SECRET_KEY
./manage.py clearsessions
./manage.py clear_clients
