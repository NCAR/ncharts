#!/bin/sh

prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    PGUSER=apache
else
    PGUSER=$USER
fi

sudo su - postgres -c "psql -c 'DROP DATABASE IF EXISTS ncharts;'"

