#!/bin/bash

# Script to work on automating ncharts install on a new server

# install packages:
sudo yum install -y python3.12 memcached netcdf-devel hdf5-devel npm yarnpkg

# set up python environment
python -m pip install --user --upgrade pipenv
PIPENV_VENV_IN_PROJECT=1 pipenv --python /bin/python3.12 install
# allow group read so datavis user can use venv
chmod -R g+rx .venv/
