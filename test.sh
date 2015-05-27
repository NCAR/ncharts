#!/bin/sh

[ $VIRTUAL_ENV ] || source $HOME/virtualenvs/django/bin/activate

python3 manage.py test ncharts/tests
