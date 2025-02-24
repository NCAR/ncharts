# ncharts

Data plotting Web application, developed at NCAR EOL.

## Setup and Starting a Production Server

The following is for RedHat systems, such as CentOS or Fedora.

### Install required packages

  This is the same as step one in setting up a development server. See `README-devel.md`.

### Decide where to put the django code and configuration.

  We'll call that `$DJROOT`.  Files for production server at EOL have been put on `/var/django`:

  ```sh
  export DJROOT=/var/django
  sudo mkdir $DJROOT
  sudo chgrp apache $DJROOT
  sudo chmod g+sw $DJROOT
```

  Add yourself to the apache group on the server machine.  Once you've done that, the sequence is the same as on a development server:

  ```sh
  cd $DJROOT
  git clone https://github.com/ncareol/ncharts.git
  cd ncharts
```

### Create virtual environment

See `README-devel.md` for instructions on setting up a pipenv virtual environment with the appropriate packages installed.

On RHEL:
  ```sh
  sudo mod_wsgi-express install-module
  sudo sh -c "cat > /etc/httpd/conf.modules.d/10-wsgi-python3.conf"
# NOTE: mod_wsgi_python3 can not coexist in the same apache process as
# mod_wsgi (python2).  Only load if mod_wsgi is not already loaded.

<IfModule !wsgi_module>
    LoadModule wsgi_module modules/mod_wsgi-py34.cpython-34m.so
</IfModule>
```

### Setup postgres server
  This is the same as in setting up a development server. See `README-devel.md`, if postgres is needed for the RAF database backend.

### Configuration

  Production settings are set and managed in `datavis/settings/production.py`. `DEBUG` should be set to `False`, as the Django docs warn in several places that using `DEBUG = True` on a production server exposed to the WWW is a security hole.

  Create and set permissions on `LOG_DIR`, `VAR_RUN_DIR` and `VAR_LIB_DIR`, per their values set in `datavis/settings/production.py`:

  ```sh
  sudo mkdir /var/log/django
  sudo chgrp apache /var/log/django
  sudo chmod g+sw /var/log/django

  sudo mkdir /run/django
  sudo chgrp apache /run/django
  sudo chmod g+sw /run/django

  sudo mkdir /var/lib/django
  sudo chgrp apache /var/lib/django
  sudo chmod g+sw /var/lib/django
  ```

  Configure the DATABASES in `datavis/settings/default.py` as discussed in `README-devel.md`.

### Create the key
  A Django `SECRET_KEY` must be assigned via the `EOL_DATAVIS_SECRET_KEY` environment variable. To generate a new `SECRET_KEY`:

  ```sh
  key=$(python3 -c 'import random; import string; print("".join([random.SystemRandom().choice(string.digits + string.ascii_letters + string.punctuation) for i in range(100)]))')
  export EOL_DATAVIS_SECRET_KEY=$key
```
The key can be passed to Apache from `systemd` by adding a `.conf` service file to `/etc/systemd/system/httpd.service.d/`, *e.g.* `datavis-secret-key.conf`:

  ```
[Service]
Environment="EOL_DATAVIS_SECRET_KEY=abc-123-CHANGE-ME"
```
  After updating the `.conf` service file, `systemd` will need to have its daemon reloaded and **Apache** will need to be restarted:

  ```sh
  sudo systemctl daemon-reload
  sudo systemctl restart httpd
```
### Initialize the database

  This also runs the django migration command, which should also handle the situation when one of the models changes, or is added or deleted:

  ```sh
  cd $DJROOT/ncharts
  ./create_sqlitedb.sh
```

  You will be prompted to enter an administrator's user name, email and password. You can use your own user name and email address. If the server will be exposed to the internet, you should enter a secure password, which should not match other passwords.

  Migrations in django are a bit complicated. If the above script fails you may have to reset the migration history for ncharts:

  ```sh
  rm db.sqlite3
  rm -rf ncharts/migrations
```

  Then run the create script again.

   > If using a postgres databse, you will need to run `create_pgdb.sh` instead of `create_sqlitedb.sh` to create a database, and run `delete_pgdb.sh` instead of deleting the sqlite file.

### Load the models from the `.json` files in `ncharts/fixtures`:

  ```sh
  ./load_db.sh
```

### Fetch the static files

  To fetch the static files of the supporting software used by ncharts, such as jquery, bootstrap and highcharts do:

  ```sh
  ./get_static_files.sh
```

  The files will be written to `$DJROOT/ncharts/static/ncharts`.

  Then on a production server, execute the static.sh shell script:

  ```sh
  ./static.sh
```

  This shell script executes the django *collectstatic* command to find the static files in the ncharts directory, as well as static files in python site-packages, and copies them to BASE_DIR/static.

  On a production server, the root files go in BASE_DIR/static, which is the same as $DJROOT/static. `See datavis/settings/default.py`:

  ```python
  STATIC_ROOT = os.path.join(BASE_DIR,'static')
```

  On a production server, `static.sh` must be run every time `ncharts/static/ncharts/jslib/ncharts.js` is changed on the server.

  To see what static files are needed for ncharts, see the `<script>` tags in `ncharts/templates/ncharts/base.html`.

### Memcached:

  The memory caching in django has been configured to use the memcached daemon, and a unix socket. The location of the unix socket is specified as `CACHES['LOCATION']` in `datavis/settings/production.py`:

  ```python
  'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),
```

  See above for creating and setting permissions on `VAR_RUN_DIR`.  To setup memcached, do:

  ```sh
  # Configure system to create /run/django on each boot
  sudo cp usr/lib/tmpfiles.d/django.conf /usr/lib/tmpfiles.d
  systemd-tmpfiles --create /usr/lib/tmpfiles.d/django.conf

  sudo cp etc/[datavis-dev or datavis]/systemd/system/memcached_django.service /etc/systemd/system
  sudo systemctl daemon-reload
  sudo systemctl enable memcached_django.service
  sudo systemctl start memcached_django.service
```

### Configure and start gunicorn server
We are using [gunicorn](https://gunicorn.org/) to serve ncharts, so the Apache server will just forward requests to gunicorn. Gunicorn has been installed into the virtual environment when it was created. Add the service and socket files to systemd and start them:
```sh
sudo cp etc/[datavis-dev or datavis]/systemd/system/gunicorn.* /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable gunicorn.socket
sudo systemctl enable gunicorn.service
sudo systemctl start gunicorn.service
```
You will have to add the secret key .conf file  to `/etc/systemd/system/gunicorn.service.d` the same way as is done in httpd.conf.d above.

### Configure and start httpd server

  Install the httpd configuration files:

  ```sh
  sudo mv /etc/httpd /etc/httpd.orig
  sudo cp -r etc/datavis/httpd /etc
```

  The httpd configuration file that sets up the wsgi python module for django is `etc/datavis/httpd/conf/vhosts/datavis.conf`, which is installed to `/etc/httpd/conf/vhosts`. The `WSGIScriptAlias` statement in this file tells httpd to run `/var/django/ncharts/datavis/wsgi.py` for all URLs. In this way a production server runs `wsgi.py` instead of `manage.py`, with `DJANGO_SETTINGS_MODULE` set to `datavis.settings.production`.  For information on wsgi, see the django documentation for the current version, for example: `https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/`.

  Tweak the umask of the systemd service, so that apache group members can read/write the log files:

  ```sh
  sudo mkdir /etc/systemd/system/httpd.service.d
  cat << EOD > /tmp/umask.conf
  [Service]
  UMask=0007
  EOD

  sudo cp /tmp/umask.conf /etc/systemd/system/httpd.service.d
  sudo systemctl daemon-reload
```

  See above for creating and setting permissions on `LOG_DIR`.

  Enable and start httpd:

  ```sh
  sudo systemctl enable httpd.service
  sudo systemctl start httpd.service
```

### Test!

   <http://localhost/ncharts>

### Clearing expired sessions and unattached ClientState objects

  This is done from a crontab on the server:

  ```sh
  crontab -l
  MAILTO=user@some.domain       # change to a real email address
  #
  # On Sundays, clear expired sessions and then the unattached clients
  0 0 * * 0 cd /var/django/ncharts; ./datavis-clear.sh
```
