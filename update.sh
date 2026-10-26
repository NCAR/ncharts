#! /bin/bash
# Update ncharts repo, update pipenv environment, and restart gunicorn. Mostly for deploying dependabot updates.

git pull
PIPENV_VENV_IN_PROJECT=1 pipenv install
chmod -R g+r .venv # fix permissions in virtual environment
sudo systemctl restart gunicorn
