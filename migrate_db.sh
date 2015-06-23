#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    DJROOT=${DJROOT:-/var/django}
    DJVIRT=${DJVIRT:-$DJROOT/virtualenv/django}

    sudo chmod -R g+w /var/lib/django
    sudo chmod -R g+w /var/log/django
else
    DJVIRT=${DJVIRT:-$HOME/virtualenvs/django}
fi

[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

python3 manage.py migrate

# python3 manage.py createsuperuser

python3 manage.py makemigrations

if $prod; then
    sudo chgrp apache /var/lib/django/db.sqlite3
fi
