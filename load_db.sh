#!/bin/bash

prod=true
if [ $# -gt 0 -a "$1" == -d ]; then
    prod=false
    shift
fi

if $prod; then
    DJROOT=${DJROOT:-/var/django}
    DJVIRT=${DJVIRT:-$DJROOT/virtualenv/django}
    export DJANGO_SETTINGS_MODULE=datavis.settings.production
else
    DJVIRT=${DJVIRT:-$HOME/virtualenvs/django}
fi

[ $VIRTUAL_ENV ] || source $DJVIRT/bin/activate


# Make sure key is set.
checkkey() {
    if [ -z "$EOL_DATAVIS_SECRET_KEY" ]; then
        . key.sh
    fi
    if [ -z "$EOL_DATAVIS_SECRET_KEY" ]; then
        echo "Could not set secret key."
        exit 1
    fi
}


# This does not usually need to be done, so keep it as a separate operation
# from the actions which do not require sudo.  This is only needed on
# production, and if the permissions do get messed up, it may need to run
# both before and after database modifications.
fixperms() {
    if [ `id -u` -ne 0 ]; then
        echo "Run this command as root with sudo."
        exit 1
    fi
    echo "fixing permissions..."
    set -x

    # make sure git checkout can only be modified by datavis group
    gitd=/var/django/ncharts
    find $gitd -type d -exec chmod g+s {} \;
    find $gitd -type d -exec setfacl -d -m u::rwX,g::rwX,o::rX {} \;
    chmod -R g+w $gitd
    chown -R datavis.datavis $gitd

    # allow datavis group to write and see logs
    logd=/var/log/django
    chown -R datavis.datavis $logd
    chmod -R g+w $logd

    # Set group ID on execution (s) / setgid
    libd=/var/lib/django
    find $libd -type d -exec chmod g+s {} \;
    # Set to inherit group write permissions via setfacl
    find $libd -type d -exec setfacl -d -m u::rwX,g::rwX,o::rX {} \;
    chmod -R g+w $libd
    chown -R datavis.datavis $libd

    set +x
}


loaddata() {
    echo "loading fixtures from json files..."
    for f in timezones.json projects.json platforms.json variables.json; do
        echo $f
        python3 manage.py loaddata $f || exit 1
    done

    for f in ncharts/fixtures/datasets_*.json; do
        ff=${f##*/}
        echo $ff
        python3 manage.py loaddata $ff || exit 1
    done
}

cleandata() {
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
}


printkeys() {
    # Print an ordered list of primary keys from the files on the
    # command-line, usually datasets_*
    if [ $# -eq 0 ]; then
        echo "printkeys requires json files to extract 'pk' fields from."
        exit 1
    fi
    fgrep -h '"pk"' "$@" | cut -d: -f 2 | sort -u -n
}


usage() {
    cat <<EOF
Usage: $0 [-d] [update|full|fixperms|loaddata|cleandata]
 -d   Run for development rather than production.

 update     Load fixture updates and run full_clean on datasets.
 full       Use sudo to fix permissions and update database.
 fixperms   Just fix the permissions.
 loaddata   Just load fixture data.
 cleandata  Run the full_clean on the datasets.
 printkeys file1 [file2 ...]
            Extract and sort all the 'pk' primary keys, eg:
            $0 printkeys datasets_*

Default operation is 'update'.
EOF
}


# The permissions should not need to be fixed, everything is forced to the
# datavis group, so sudo should no longer be needed, and the default
# operation can just be update.

[ -z "$1" ] && set update


case "$1" in

    full)
        if $prod ; then
            # fixperms
            checkkey
        fi
        loaddata
        cleandata
        # fixperms
        ;;

    update)
        # Just update the fixtures, do not fix perms.
        if $prod ; then
            checkkey
        fi
        loaddata
        cleandata
        ;;

    fixperms)
        fixperms
        ;;

    loaddata)
        if $prod ; then
            checkkey
        fi
        loaddata
        ;;

    cleandata)
        if $prod ; then
            checkkey
        fi
        cleandata
        ;;

    printkeys)
        shift
        printkeys "$@"
        ;;

    -h)
        usage
        ;;

    *)
        echo "Unrecognied argument: $1"
        usage
        exit 1
        ;;

esac
