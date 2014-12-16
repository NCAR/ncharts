#!/bin/bash

# nohup python manage.py runserver 0.0.0.0:8000 >& /tmp/django.log &

# sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.4

source $HOME/virtualenvs/django/bin/activate

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
