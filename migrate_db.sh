#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
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
[ -f $VAR_LIB_DIR/db.sqlite3 ] && db_exists=true

migs_exist=false
[ -d ncharts/migrations ] && migs_exist=true

if $db_exists; then
    $migs_exist && python3 manage.py migrate ncharts || exit 1

    # Not really sure whether this is necessary.
    # Note that migrations for other apps are written to the
    # virtual environment directory. Not sure when this occurs.
    # find /home/maclean/virtualenvs/django -name migrations  -print
    python3 manage.py makemigrations

    # Have to specify the ncharts app name in order to make its migrations
    python3 manage.py makemigrations ncharts
else
    rm -rf ncharts/migrations
    # creates initial database
    python3 manage.py migrate
    python3 manage.py createsuperuser

    python3 manage.py makemigrations
    python3 manage.py makemigrations ncharts
    # --fake-initial: mark the migration as having been already applied
    python3 manage.py migrate --fake-initial ncharts
fi

if $prod; then
    sudo chgrp apache /var/lib/django/db.sqlite3
fi
