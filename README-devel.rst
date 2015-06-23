eol-django-datavis
==================

Data plotting Web application, developed at NCAR EOL.

Setup and Starting a Development NCharts Server
------------------------------------------------------------

The following is for RedHat systems, such as CentOS or Fedora.

1. Install required packages

 Redhat does not (yet!) provide an RPM for python3 in CentOS, even CentOS7.

 RPMs for python3 and python3-devel are available on the EOL yum repo for
 CentOS7, but not CentOS6. See the SEW wiki at http://wiki.eol.ucar.edu/sew/EOL_YUM_Repository.

 To install the required RPMs::

    sudo yum install python3 python3-pip python3-memcached \
        memcached python3-mod_wsgi python3-devel netcdf-devel hdf5-devel

    sudo python3 -m pip install virtualenv

    sudo python3 -m pip install virtualenvwrapper

    # tools for managing static files
    sudo yum install npm
    sudo npm install -g bower

2. Decide where to put the django code and configuration.

 We'll call that $DJROOT.  On a development server you can put it anywhere you want::

    export DJROOT=$HOME/git     # for example
    cd $DJROOT
    git clone /net/cds/git/eol-django-datavis.git

 Since the django-ncharts app is undergoing many changes, rather than
 create a python package out of it, it is simpler to clone it from github
 to a neighboring directory, and create a symbolic link::

    git clone https://github.com/ncareol/django-ncharts.git
    cd eol-django-datavis
    ln -s ../django-ncharts/ncharts .

3. Create virtual environment

 A virtual environment allows you to run specific versions of python packages without effecting other users on the system. These commands will create a django virtual environment in your $HOME directory::

    mkdir $HOME/virtualenvs

    cd $HOME/virtualenvs
    virtualenv -p /usr/bin/python3 django

 On Fedora, had to do::
    virtualenv-3.4 -p /usr/bin/python3 django
 
 Activate that virtual environment::

    source $HOME/virtuanenvs/django/bin/activate

 The activation needs to be done once for each shell. To make it easier, you can create an alias in your $HOME/.bashrc::

    alias djvirt='source $HOME/virtualenvs/django/bin/activate'

 If you have setup a virtual environment as above, the shell scripts described below, such as migrate_db.sh, load_db.sh, get_static_files.sh and runserver.sh will activate the virtual environment as necessary.

4. Add other Python packages to virtual environment::

    source $HOME/virtuanenvs/django/bin/activate

    python3 -m pip install --upgrade django
    python3 -m pip install --upgrade numpy
    python3 -m pip install --upgrade pytz
    python3 -m pip install --upgrade netCDF4
    python3 -m pip install --upgrade pylint_django

 Python3 version of django-datetime-widge and timezone support::

    python3 -m pip install django-datetime-widget
    python3 -m pip install django-timezone-field

    python3 -m pip install python3-memcached

5. Configuration

 Edit datavis/settings.py and set DEBUG = True. Note that this results in the following settings::

    VAR_RUN_DIR = BASE_DIR
    VAR_LIB_DIR = BASE_DIR
    LOG_DIR = os.path.join(BASE_DIR,'log')

 BASE_DIR is set in datavis/settings.py as the parent directory of datavis,
 which, in this configuration is $DJROOT/eol-django-datavis

 The memcached socket is on VAR_RUN_DIR.
 The database is on VAR_LIB_DIR.

 Create the log directory::
    mkdir $DJROOT/eol-django-datavis/log

6. Initialize the database. 

 This runs migrate command, which should also handle the situation of one of the models changes, or is added or deleted::
    
    ./migrate_db.sh -d

 The -d option indicates this is a development server.

 Migrations in django are a bit complicated. If the above script fails you may have to reset the migration history::

    rm db.sqlite3
    rm -rf ncharts/migrations

 Then run the migration script again.

7. Load the models from the .json files in ncharts/fixtures::

    ./load_db.sh -d

 The -d option indicates this is a development server.

8. Fetch the static files::

    cd $DJROOT/django-ncharts
    ./get_static_files.sh

 This script will download from the internet the static files needed by the jquery, highcharts, bootstrap, and the moment javascript packages.  The filies will be written to $DJROOT/django-ncharts/ncharts/static/ncharts.

 On development server, these static filies will be automatically found and served by the django.contrib.staticfiles django application.

9. Memcached:

 The memory caching in django has been configured to use the memcached daemon, and
 a unix socket.  The location of the unix socket is specified as CACHES['LOCATION'] in
 datavis/settings.py::

    'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),

 Often on a development server one doesn't enable caching, so that
 changes are seen without clearing out the cache.
    
 If you want to test caching, enable the CACHES configuration in settings.py
 so that it is enabled even when DEBUG is true. Then start memcached by hand,
 specifying the location of the socket in the runstring.  On a development server,
 VAR_RUN_DIR is the same as BASE_DIR, the directory containing manage.py.

    cd $DJROOT
    memcached -s ./django_memcached.sock -d

10. Start server::

    ./runserver.sh


11. Test!

    http://127.0.0.1:8000/ncharts



