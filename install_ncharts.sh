#!/bin/bash

# Script to work on automating ncharts install on a new server

NCHARTS_DIR=$(dirname "$0")


setup()
{
    # install packages:
    sudo yum install -y python3.12 memcached netcdf-devel hdf5-devel npm yarnpkg

    # set up python environment
    python -m pip install --user --upgrade pipenv
    cd $NCHARTS_DIR && PIPENV_VENV_IN_PROJECT=1 pipenv --python /bin/python3.12 install
    # allow group read so datavis user can use venv
    chmod -R g+rx $NCHARTS_DIR/.venv/

    # set up dirs and permissions
    sudo mkdir /var/log/django
    sudo chgrp datavis /var/log/django
    sudo chmod g+sw /var/log/django

    sudo mkdir /run/django
    sudo chgrp datavis /run/django
    sudo chmod g+sw /run/django

    sudo mkdir /var/lib/django
    sudo chgrp datavis /var/lib/django
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
	key=$(python3 -c 'import random; import string; print("".join([random.SystemRandom().choice(string.digits + string.ascii_letters + string.punctuation) for i in range(100)]))')
	sudo mkdir -p $keydir
	sudo chmod 755 $keydir
	cat <<EOF | sudo tee $keyfile
[Service]
Environment="EOL_DATAVIS_SECRET_KEY=$key"

EOF
    fi
}

setup
key

