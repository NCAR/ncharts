#!/bin/bash

# Script to work on automating ncharts install on a new server
# Usage: install_ncharts.sh [hostname] where hostname is datavis or datavis-dev

setup()
{
    # install packages:
    sudo yum install -y python3.14 python3.14-pip memcached netcdf-devel hdf5-devel npm yarnpkg

    # set up python environment
    python3.14 -m pip install --user --upgrade pipenv
    cd $NCHARTS_DIR && PIPENV_VENV_IN_PROJECT=1 python3.14 -m pipenv --python /bin/python3.14 install
    # allow group read so datavis user can use venv
    chmod -R g+rx $NCHARTS_DIR/.venv/

    # set up dirs and permissions
    sudo mkdir -p /var/log/django
    sudo chgrp datavis /var/log/django
    sudo chown datavis /var/log/django
    sudo chmod g+sw /var/log/django

    sudo mkdir -p /run/django
    sudo chgrp datavis /run/django
    sudo chown datavis /run/django
    sudo chmod g+sw /run/django

    sudo mkdir -p /var/lib/django
    sudo chgrp datavis /var/lib/django
    sudo chown datavis /var/lib/django
    sudo chmod g+sw /var/lib/django

}

key()
{
    keydir=/etc/systemd/system/gunicorn.service.d
    keyfile=$keydir/datavis-secret-key.conf
    if [ -f $keyfile ]; then
	echo "Key file at $keyfile already exists."
    else
	echo "Key file at $keyfile does not exist. Generating a new key..."
	key=$(python3 -c 'import random; import string; print("".join([random.SystemRandom().choice(string.digits + string.ascii_letters) for i in range(100)]))')
	sudo mkdir -p $keydir
	sudo chmod 755 $keydir
	cat <<EOF | sudo tee $keyfile
[Service]
Environment="EOL_DATAVIS_SECRET_KEY=$key"
EOF
	sudo chmod 644 $keyfile
    fi
}

database()
{
    # source key env variable
    source /var/django/ncharts/key.sh
    # create_sqlitedb needs to be interactive to create ncharts superuser account
    cd $NCHARTS_DIR && ./create_sqlitedb.sh
    cd $NCHARTS_DIR && ./load_db.sh
}

static()
{
    cd $NCHARTS_DIR && ./get_static_files.sh
    cd $NCHARTS_DIR && ./static.sh
}

memcached()
{
    # Configure system to create /run/django on each boot
    sudo cp $NCHARTS_DIR/usr/lib/tmpfiles.d/django.conf /usr/lib/tmpfiles.d
    sudo systemd-tmpfiles --create /usr/lib/tmpfiles.d/django.conf

    sudo cp $NCHARTS_DIR/etc/$HOSTTYPE/systemd/system/memcached_django.service /etc/systemd/system
    sudo systemctl daemon-reload
    sudo systemctl enable memcached_django.service
    sudo systemctl restart memcached_django.service
}

gunicorn()
{
    sudo cp $NCHARTS_DIR/etc/$HOSTTYPE/systemd/system/gunicorn.service /etc/systemd/system
    sudo systemctl daemon-reload
    sudo systemctl enable gunicorn.service
    sudo systemctl restart gunicorn.service
}

httpd()
{
    sudo cp -r $NCHARTS_DIR/etc/$HOSTNAME/httpd/conf/vhosts /etc/httpd/conf

    sudo mkdir -p /etc/systemd/system/httpd.service.d
    cat << EOD > /tmp/umask.conf
[Service]
UMask=0007
EOD

    sudo cp /tmp/umask.conf /etc/systemd/system/httpd.service.d
    sudo systemctl daemon-reload

    sudo systemctl enable httpd.service
    sudo systemctl restart httpd.service

    sudo cp $NCHARTS_DIR/var/$HOSTTYPE/www/html/index.html /var/www/html
}

cron()
{
    sudo -u datavis crontab $NCHARTS_DIR/crontab.datavis
}

NCHARTS_DIR=$(dirname "$0")

if [ "$#" -ne 2 ]; then
    echo "Supply host type (datavis or datavis-dev) and host hame (e.g. eol-datavis-10) as arguments"
    exit 1
fi

HOSTTYPE=$1
HOSTNAME=$2
setup
key
database
static
memcached
gunicorn
httpd
cron
