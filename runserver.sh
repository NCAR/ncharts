#!/bin/bash

# cd to dir containing this script - needed when running from user systemd
dir=$(dirname $0)
cd $dir

# nohup python manage.py runserver 0.0.0.0:8000 >& /tmp/django.log &

# sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.4

DJVIRT=${DJVIRT:-$HOME/virtualenvs/django}
[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate

if false; then

    while :; do
        pgrep -f "memcached -s $PWD/django_memcached.sock" || break
        pkill -f -TERM "memcached -s $PWD/django_memcached.sock"
        sleep 1
    done

    if ! pgrep -f "memcached -s $PWD/django_memcached.sock" > /dev/null; then
        echo "starting memcached"
        memcached -s $PWD/django_memcached.sock -d
    fi
fi

python3 manage.py runserver 0.0.0.0:8000
