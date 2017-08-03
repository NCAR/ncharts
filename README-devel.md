# ncharts

Data plotting Web application, developed at NCAR EOL.

## Setup and Starting a Development NCharts Server

The following is for RedHat systems, such as CentOS or Fedora.

1. Install required packages

   As of Aug 2017, python34 is available from the EPEL repositories for
   RHEL7 systems.

  To install the required RPMs:

  On RHEL7:
  ```sh
  sudo yum install python34 python34-libs python34-setuptools python34-devel
        memcached netcdf-devel hdf5-devel postgresql-devel
  sudo easy_install-3.4 pip
```

  On Fedora:

  ```sh
  sudo yum install python3 python3-pip python3-memcached \
        memcached python3-mod_wsgi python3-devel netcdf-devel hdf5-devel \
        postgresql-devel
```

  ```sh
  sudo python3 -m pip install virtualenv

  sudo python3 -m pip install virtualenvwrapper

  # tools for managing static files
  sudo yum install npm
  sudo npm install -g bower
```

2. Decide where to put the django code and configuration.

  We'll call that `$DJROOT`.  On a development server you can put it anywhere you want:

  ```sh
  export DJROOT=$HOME/git     # for example
  cd $DJROOT
  git clone https://github.com/ncareol/ncharts.git
  ```

3. Create virtual environment

  A virtual environment allows you to run specific versions of python packages without affecting other users on the system. These commands will create a django virtual environment in your `$HOME` directory:

  ```sh
  mkdir $HOME/virtualenvs
  cd $HOME/virtualenvs
  virtualenv -p /usr/bin/python3 django
```

  On Fedora, had to do:

  ```sh
  virtualenv-3.4 -p /usr/bin/python3 django
```

   Activate that virtual environment:

  ```sh
  source $HOME/virtualenvs/django/bin/activate
```
  The activation needs to be done once for each shell. To make it easier, you can create an alias in your `$HOME/.bashrc`:

  ```sh
  alias djvirt='source $HOME/virtualenvs/django/bin/activate'
```

  If you have setup a virtual environment as above, the shell scripts described below, such as migrate_db.sh, load_db.sh, get_static_files.sh and runserver.sh will activate the virtual environment as necessary.

4. Add other Python packages to virtual environment:

  ```sh
   source $HOME/virtualenvs/django/bin/activate

   python3 -m pip install --upgrade django
   python3 -m pip install --upgrade mod_wsgi
   python3 -m pip install --upgrade numpy
   python3 -m pip install --upgrade pytz
   python3 -m pip install --upgrade netCDF4
   python3 -m pip install --upgrade pylint_django
   python3 -m pip install --upgrade psycopg2
```

   Python3 version of django-datetime-widge and timezone support:

  ```sh
  python3 -m pip install django-datetime-widget
  python3 -m pip install django-timezone-field
  python3 -m pip install python3-memcached
```

  Display django version:
  ```sh
  python3 manage.py version
```

5. Configuration

  Edit `datavis/settings.py` and set `DEBUG = True`. Note that this results in the following settings:

  ```sh
  VAR_RUN_DIR = BASE_DIR
  VAR_LIB_DIR = BASE_DIR
  LOG_DIR = os.path.join(BASE_DIR,'log')
```

  `BASE_DIR` is set in `datavis/settings.py` as the parent directory of datavis, which, in this configuration is `$DJROOT/ncharts`

  The memcached socket is on `VAR_RUN_DIR`.
  The database is on `VAR_LIB_DIR`.

  Create the log directory:

  ```sh
  mkdir $DJROOT/ncharts/log
```

6. Initialize the database.

  This runs migrate command, which should also handle the situation of one of the models changes, or is added or deleted:

  ```sh
  ./migrate_db.sh -d
```

  The -d option indicates this is a development server.  If the db.sqlite3 database has not been created yet, you will be prompted to enter an administrator's user name, email and password. You can use your own user name and email address. The security of the password is not critical for a development server if it is not exposed to the internet. I'd suggest not using your UCAS or EOL server password.

  Migrations in django are a bit complicated. If the above script fails you may have to reset the migration history:

  ```sh
  rm db.sqlite3
  rm -rf ncharts/migrations
```

  Then run the migration script again.

7. Load the models from the .json files in ncharts/fixtures:

  ```sh
  ./load_db.sh -d
```

  The `-d` option indicates this is a development server.

8. Fetch the static files

  To fetch the static files of the supporting software such as jquery, bootstrap and highcharts do:

  ```sh
  ./get_static_files.sh
```

  The files will be written to `$DJROOT/ncharts/static/ncharts`.

  To see what static files are needed for ncharts, see the `<script>` tags in `ncharts/templates/ncharts/base.html`.

  On development server, these static filies will be automatically found and served by the django.contrib.staticfiles django application.

9. Memcached:

  The memory caching in django has been configured to use the memcached daemon, and a unix socket.  The location of the unix socket is specified as `CACHES['LOCATION']` in `datavis/settings.py`:

  ```python
  'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),
```

  Often on a development server one doesn't enable caching, so that  changes are seen without clearing out the cache.

  If you want to test caching, enable the `CACHES` configuration in `settings.py` so that it is enabled even when `DEBUG` is `true`. Then start memcached by hand, specifying the location of the socket in the runstring.  On a development server, `VAR_RUN_DIR` is the same as `BASE_DIR`, the directory containing `manage.py`.

  ```sh
  cd $DJROOT
  memcached -s ./django_memcached.sock -d
```

10. Start server:

  ```sh
  ./runserver.sh
```

11. Test!

  <http://127.0.0.1:8000/ncharts>

12. To run your development environment in production mode, set two environment variable: `DJANGO_SETTINGS_MODULE` and `EOL_DATAVIS_SECRET_KEY`. `DJANGO_SETTINGS_MODULE` should be set to `datavis.settings.production`, while `EOL_DATAVIS_SECRET_KEY` can be set to anything. You can set these on the same line as `runserver.sh` invocation:

  ```sh
EOL_DATAVIS_SECRET_KEY=1 DJANGO_SETTINGS_MODULE=datavis.settings.production ./runserver.sh
```

  or `export` them prior to invocation:

  ```sh
export EOL_DATAVIS_SECRET_KEY=1
export DJANGO_SETTINGS_MODULE=datavis.settings.production
./runserver.sh
```
