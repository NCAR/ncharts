#!/bin/sh

rm -f db.sqlite3

# python3 manage.py syncdb --noinput
python3 manage.py syncdb
