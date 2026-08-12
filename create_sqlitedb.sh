#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    export DJANGO_SETTINGS_MODULE=datavis.settings.production
    sudo chmod -R g+w /var/lib/django
    sudo chmod -R g+w /var/log/django
fi

DJROOT=${DJROOT:-/var/django}
DJVIRT=${DJVIRT:-$DJROOT/ncharts/.venv}

[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

rm -rf ncharts/migrations

python3 manage.py migrate --run-syncdb
echo "Create ncharts superuser:"
python3 manage.py createsuperuser

# make production database file group writeable
if $prod; then
    chmod g+w /var/lib/django/db.sqlite3
fi

