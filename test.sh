#!/bin/sh

DJROOT=${DJROOT:-/var/django}
DJVIRT=${DJVIRT:-$DJROOT/ncharts/.venv}
[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

python3 manage.py test ncharts/tests
