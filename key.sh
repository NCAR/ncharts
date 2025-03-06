# Set the secret key environment variable from the production file.
keyfile=/etc/systemd/system/gunicorn.service.d/datavis-secret-key.conf
export DJANGO_SETTINGS_MODULE=datavis.settings.production
eval export `grep EOL_DATAVIS_SECRET_KEY $keyfile | sed -e 's/^.*\"EOL/EOL/' -e 's/\"$//'`

