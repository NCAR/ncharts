#!/bin/sh

dest=$(dirname $0)

dest=$(readlink -f $dest)

dest=$dest/ncharts/static/ncharts

[ -d $dest ] || mkdir -p $dest
[ -d $dest/js ] || mkdir -p $dest/js
[ -d $dest/js/modules ] || mkdir -p $dest/js/modules

echo "Downloading and copying static files to $dest"

# 'yarn install' downloads all dependencies from package.json to node_modules/
yarn install

rsync -rv node_modules/jquery/dist/ $dest/js || exit 1
rsync -rv node_modules/bootstrap/dist/ $dest || exit 1
rsync -rv node_modules/moment/min/moment.min.js $dest/js || exit 1
rsync -rv node_modules/moment-timezone/builds/moment-timezone-with-data.min.js $dest/js || exit 1

# Either can get the full highcharts zip files, or get just what we want.
# For now, just get what we want.
do_zip=false
if $do_zip; then

    # download zip files
    # www.highcharts/com/download
    curl -O code.highcharts.com/zips/Highcharts.zip || exit 1
    curl -O code.highcharts.com/zips/Highstock.zip || exit 1
    mkdir highcharts
    cd highcharts

    unzip ../Highcharts.zip > /dev/null
    rsync -rv js $dest || exit 1

    cd -

    mkdir highstock
    cd highstock

    unzip ../Highstock.zip > /dev/null
    rsync -rv js/highstock*.js $dest/js || exit 1
    cd -
else
    rsync -rv node_modules/highcharts/highstock.js $dest/js || exit 1
    rsync -rv node_modules/highcharts/modules/exporting.js $dest/js/modules || exit 1
    rsync -rv node_modules/highcharts/modules/heatmap.js $dest/js/modules || exit 1
fi

echo "On a production server, you should run the static.sh script, which basically does python3 manage.py collectstatic
"
