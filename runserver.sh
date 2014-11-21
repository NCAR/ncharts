#!/bin/bash

# nohup python manage.py runserver 0.0.0.0:8000 >& /tmp/django.log &

if ! pgrep -f "memcached -s /tmp/django_memcached.sock" > /dev/null; then
    memcached -s /tmp/django_memcached.sock -d
fi

python3 manage.py runserver 0.0.0.0:8000
