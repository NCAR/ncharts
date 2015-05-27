#!/bin/sh

[ $VIRTUAL_ENV ] || source $HOME/virtualenvs/django/bin/activate

rm -f db.sqlite3

python3 manage.py migrate

python3 manage.py createsuperuser

python3 manage.py makemigrations
