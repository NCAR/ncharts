#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    export DJANGO_SETTINGS_MODULE=datavis.settings.production
    DJROOT=${DJROOT:-/var/django}
    DJVIRT=${DJVIRT:-$DJROOT/virtualenv/django}
    VAR_LIB_DIR=/var/lib/django

    sudo chmod -R g+w /var/lib/django
    sudo chmod -R g+w /var/log/django
else
    DJVIRT=${DJVIRT:-$HOME/virtualenvs/django}
    VAR_LIB_DIR=$(dirname $0)
fi

[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

db_exists=false
# [ -f $VAR_LIB_DIR/db.sqlite3 ] && db_exists=true
sudo su - postgres -c "psql -lqt | cut -d \| -f 1 | grep -qw ncharts" && db_exists=true

if $db_exists; then

    # Have to specify the ncharts app name in order to make its migrations
    python3 manage.py makemigrations ncharts
    python3 manage.py migrate ncharts

else
    ./create_pgdb.sh $*

    python3 manage.py makemigrations
    python3 manage.py makemigrations ncharts
    # --fake-initial: mark the migration as having been already applied
    python3 manage.py migrate --fake-initial ncharts
fi

if $prod; then
    sudo chgrp apache /var/lib/django/db.sqlite3
fi
