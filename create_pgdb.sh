#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    DJROOT=${DJROOT:-/var/django}
    DJVIRT=${DJVIRT:-$DJROOT/virtualenv/django}
    export DJANGO_SETTINGS_MODULE=datavis.settings.production
    sudo chmod -R g+w /var/lib/django
    sudo chmod -R g+w /var/log/django
else
    DJVIRT=${DJVIRT:-$HOME/virtualenvs/django}
fi

[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate


sudo su - postgres -c "createdb -O $PGUSER ncharts"
sudo su - postgres -c "psql -c 'CREATE USER $USER; GRANT ALL PRIVILEGES ON DATABASE ncharts to $PGUSER;'"

if $prod; then
    PGUSER=apache
    sudo su - postgres -c "psql -c 'CREATE USER $PGUSER; GRANT ALL PRIVILEGES ON DATABASE ncharts to $PGUSER;'"
fi

rm -rf ncharts/migrations

python3 manage.py migrate --run-syncdb
python3 manage.py createsuperuser

