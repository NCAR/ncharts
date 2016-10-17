#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    export DJANGO_SETTINGS_MODULE=datavis.settings.production
    DJROOT=${DJROOT:-/var/django}
    DJVIRT=${DJVIRT:-$DJROOT/virtualenv/django}
    sudo chmod -R g+w /var/log/django
else
    DJVIRT=${DJVIRT:-$HOME/virtualenvs/django}
fi

[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

chmod -R ug+w static

python3 manage.py findstatic ncharts/jslib/ncharts.js
python3 manage.py collectstatic

chmod -R -w static
