#!/bin/sh


prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    [ $VIRTUAL_ENV ] || source /var/django/virtualenvs/django/bin/activate
    sudo rm -f /var/lib/django/db.sqlite3
    sudo chmod 0777 /var/lib/django
else
    [ $VIRTUAL_ENV ] || source $HOME/virtualenvs/django/bin/activate
fi

python3 manage.py migrate

python3 manage.py createsuperuser

python3 manage.py makemigrations
