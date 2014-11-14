#!/bin/sh

python3 manage.py loaddata projects.json 
python3 manage.py loaddata platforms.json 

for f in ncharts/fixtures/datasets_*.json; do
    ff=${f##*/}
    python3 manage.py loaddata $ff
done

