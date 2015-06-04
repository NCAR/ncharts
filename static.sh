#!/bin/sh

if $prod; then
    [ $VIRTUAL_ENV ] || source /var/django/virtualenvs/django/bin/activate
    sudo chmod -R g+w /var/log/django
else
    [ $VIRTUAL_ENV ] || source $HOME/virtualenvs/django/bin/activate
fi

python3 manage.py findstatic ncharts/jslib/ncharts.js
python3 manage.py collectstatic
