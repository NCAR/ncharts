#!/bin/sh

python3 manage.py loaddata projects.json 
python3 manage.py loaddata platforms.json 

for f in ncharts/fixtures/datasets_*.json; do
    ff=${f##*/}
    python3 manage.py loaddata $ff
done

echo "running full_clean on Datasets"

python3 manage.py shell << EOD
from ncharts.models import Dataset
from django.core.exceptions import ValidationError

for d in Dataset.objects.all():
    try:
        d.full_clean()
    except ValidationError as e:
        print(e)
        exit(1)

exit(0)
EOD
