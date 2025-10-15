# Update ncharts repo, update pipenv environment, and restart gunicorn. Mostly for deploying dependabot updates.
#! /bin/bash

git pull
pipenv install
chmod -R g+r .venv # fix permissions in virtual environment
sudo systemctl restart gunicorn