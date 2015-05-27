#!/bin/sh


prod=true
[ $# -gt 0 -a "$1" == -d ] && prod=false

if $prod; then
    [ $VIRTUAL_ENV ] || source /var/django/virtualenvs/django/bin/activate
    # sudo chown maclean.eol /var/lib/django/db.sqlite3
    # sudo chmod 0755 /var/lib/django
    # sudo chmod 0600 /var/lib/django/db.sqlite3
    # sudo chown maclean.eol /var/log/django/django.log
    # sudo chown maclean.eol /var/log/django/django_debug.log
    # sudo chown maclean.eol /var/log/django/datavis.log
    # sudo chown maclean.eol /var/log/django/datavis_debug.log
    # sudo chown maclean.eol /var/log/django/ncharts.log
    # sudo chown maclean.eol /var/log/django/ncharts_debug.log
else
    [ $VIRTUAL_ENV ] || source $HOME/virtualenvs/django/bin/activate
fi

python3 manage.py loaddata projects.json 
python3 manage.py loaddata platforms.json 
python3 manage.py loaddata variables.json 

for f in ncharts/fixtures/datasets_*.json; do
    ff=${f##*/}
    python3 manage.py loaddata $ff
done

echo "running full_clean on Datasets"

python3 manage.py shell << EOD
from ncharts.models import Dataset, FileDataset
from django.core.exceptions import ValidationError

print("{0} datasets".format(len(FileDataset.objects.all())))

for d in FileDataset.objects.all():
    print("d.name=",d.name)
    try:
        d.full_clean()
    except ValidationError as e:
        print(e)
        exit(1)

exit(0)
EOD

if $prod; then
    :
    # sudo chown apache.apache /var/lib/django/db.sqlite3
    # sudo chmod 0755 /var/lib/django
    # sudo chmod 0600 /var/lib/django/db.sqlite3
    # sudo chown apache.apache /var/log/django/django.log
    # sudo chown apache.apache /var/log/django/django_debug.log
    # sudo chown apache.apache /var/log/django/datavis.log
    # sudo chown apache.apache /var/log/django/datavis_debug.log
    # sudo chown apache.apache /var/log/django/ncharts.log
    # sudo chown apache.apache /var/log/django/ncharts_debug.log
fi
