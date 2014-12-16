#!/bin/sh

dest=$(dirname $0)

dest=$(readlink -f $dest)

dest=$dest/ncharts/static/ncharts

[ -d $dest ] || mkdir -p $dest

echo "Downloading and copying static files to $dest"

tmpdir=$(mktemp -d /tmp/ncharts_static_XXXXXX)
trap "{ rm -rf $tmpdir; }" EXIT

cd $tmpdir
bower install jquery
bower install bootstrap

rsync -av bower_components/jquery/dist/ $dest/js
rsync -av bower_components/bootstrap/dist/ $dest

# Highcharts. These bower commands don't get what we want.
# bower install https://github.com/highslide-software/highcharts.com.git
# bower install https://github.com/highslide-software/highstock-release.git

# instead download zip files
# www.highcharts/com/download
wget code.highcharts.com/zips/Highcharts-4.0.4.zip
wget code.highcharts.com/zips/Highstock-2.0.4.zip

# only difference between Highcharts and Highstock:
# Only in highcharts/js: highcharts-all.js
# Only in highcharts/js: highcharts.js
# Only in highcharts/js: highcharts.src.js
# Only in highstock/js: highstock.js
# Only in highstock/js: highstock.src.js

mkdir highcharts
cd highcharts

unzip ../Highcharts-*.zip > /dev/null
rsync -av js $dest

cd -

mkdir highstock
cd highstock

unzip ../Highstock-*.zip > /dev/null
rsync -av js/highstock*.js $dest/js

cd -
