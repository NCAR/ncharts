#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    [ $VIRTUAL_ENV ] || source /var/django/virtualenvs/django/bin/activate
    sudo rm -f /var/lib/django/db.sqlite3
    sudo chmod -R g+w /var/lib/django
    sudo chmod -R g+w /var/log/django
else
    [ $VIRTUAL_ENV ] || source $HOME/virtualenvs/django/bin/activate
    rm -f db.sqlite3
fi

python3 manage.py migrate

python3 manage.py createsuperuser

python3 manage.py makemigrations

if $prod; then
    sudo chown apache.apache /var/lib/django/db.sqlite3
fi
