#!/bin/sh

python3 manage.py dumpdata --format=json --indent=4 --exclude admin --exclude auth --exclude sessions --exclude contenttypes > /tmp/ncharts.json

