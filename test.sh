#!/bin/sh

DJVIRT=${DJVIRT:$HOME/virtualenvs/django}
[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

python3 manage.py test ncharts/tests
