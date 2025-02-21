#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    export DJANGO_SETTINGS_MODULE=datavis.settings.production
    sudo chmod -R g+w /var/lib/django
    sudo chmod -R g+w /var/log/django
fi

DJROOT=${DJROOT:-/var/django}
DJVIRT=${DJVIRT:-$DJROOT/ncharts/.venv}

[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate


sudo su - postgres -c "createdb ncharts"
sudo su - postgres -c "psql -c 'CREATE USER $USER; GRANT ALL PRIVILEGES ON DATABASE ncharts to $USER;'"

if $prod; then
    PGUSER=datavis
    sudo su - postgres -c "psql -c 'CREATE USER $PGUSER; GRANT ALL PRIVILEGES ON DATABASE ncharts to $PGUSER;'"

fi

rm -rf ncharts/migrations

sudo su - datavis -c "${DJVIRT}/bin/python /var/django/ncharts/manage.py migrate --run-syncdb"

# add permissions to tables for current user
sudo su - postgres -c "psql --dbname=ncharts -c 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $USER;'"

echo "Create ncharts superuser:"
python3 manage.py createsuperuser

