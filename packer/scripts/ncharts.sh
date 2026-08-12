#!/bin/sh -eux

# EPEL, required for npm

rpm -ivh http://download.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

# https://github.com/ncareol/eol-django-datavis/blob/master/README-devel.rst

rpm -ihv http://www.eol.ucar.edu/software/rpms/eol-repo-epel-1-3.noarch.rpm

yum install -y python3 python3-pip python3-memcached \
    memcached python3-mod_wsgi python3-devel netcdf-devel hdf5-devel \
    postgresql-devel

# python3 -m pip install virtualenv
# python3 -m pip install virtualenvwrapper

# tools for managing static files
yum install -y npm
npm install -g bower


# TODO: lock version(s)

# python3 -m pip install --upgrade django
python3 -m pip install "django<1.9"
python3 -m pip install --upgrade numpy
python3 -m pip install --upgrade netCDF4
python3 -m pip install --upgrade pylint_django
python3 -m pip install --upgrade psycopg2

python3 -m pip install django-datetime-widget
python3 -m pip install django-timezone-field

python3 -m pip install python3-memcached
