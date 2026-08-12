#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    export DJANGO_SETTINGS_MODULE=datavis.settings.production
    sudo chmod -R g+w /var/log/django
fi

DJROOT=${DJROOT:-/var/django}
DJVIRT=${DJVIRT:-$DJROOT/ncharts/.venv}
[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

[ -d static ] || mkdir static
chmod -R ug+w static

python3 manage.py findstatic ncharts/jslib/ncharts.js
python3 manage.py collectstatic

chmod -R a-w static
