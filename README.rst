eol-django-datavis
==================

Data plotting Web application, developed at NCAR EOL.

Setup and Starting a Development or Production Server
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

 We'll call that $DJROOT.

 2.a Development server:  anywhere you want::

        export DJROOT=$HOME/git     # for example

        cd $DJROOT
        git clone /net/cds/git/eol-django-datavis.git

 Since the django-ncharts app is undergoing many changes, rather than
 create a python package out of it, it is simpler to clone it from github
 to a neighboring directory, and create a symbolic link::

    git clone https://github.com/ncareol/django-ncharts.git
    cd eol-django-datavis
    ln -s ../django-ncharts/ncharts .

 2.b Production server.  /var/django seems like a good place::

    export DJROOT=/var/django
    sudo mkdir $DJROOT
    sudo chgrp apache $DJROOT
    sudo chmod g+sw $DJROOT

 Add yourself to the apache group on the server machine.  Once you've done that, the sequence is the same as on a development server::

        cd $DJROOT
        git clone /net/cds/git/eol-django-datavis.git
        git clone https://github.com/ncareol/django-ncharts.git
        cd eol-django-datavis
        ln -s ../django-ncharts/ncharts .

3. Create virtual environment

 A virtual environment allows you to run specific versions of python packages without effecting other users on the system.

 Once the virtual environment has been created, it must be activated for each shell where you run python django commands from.
   
 In the following sections you will see this command::

        source $DJVIRT/bin/activate

 It only needs to be done once for each shell.  If you see "(django)" in your shell prompt, it is not necessary to activate it again.

 3.a Development server::

        mkdir $HOME/virtualenvs

        cd $HOME/virtualenvs
        virtualenv -p /usr/bin/python3 django

        On Fedora, had to:
        virtualenv-3.4 -p /usr/bin/python3 django

        DJVIRT=$HOME/virtualenvs/django
        source $DJVIRT/bin/activate

 3.b Production Server (apache)::

        cd $DJROOT
        mkdir virtualenv
        cd virtualenv
        virtualenv -p /usr/bin/python3 django

        DJVIRT=$DJROOT/virtualenv/django
        source $DJVIRT/bin/activate


4. Add other Python packages to virtual environment::

        source $DJVIRT/bin/activate

        python3 -m pip install --upgrade django
        python3 -m pip install --upgrade numpy
        python3 -m pip install --upgrade pytz
        python3 -m pip install --upgrade netCDF4
        python3 -m pip install --upgrade pylint_django

 Python3 version of django-datetime-widget::

        python3 -m pip install django-datetime-widget
        python3 -m pip install django-timezone-field

        python3 -m pip install python3-memcached

 4.a For a production server, install mod_wsgi

  This RPM for CentOS7 is on the EOL repo::

        sudo yum install httpd python3-mod_wsgi

5. Configuration

 5.a Development server
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

 5.b Production server

  Important!  Set DEBUG = False in datavis/settings.py. The django docs
  warn in several places that using DEBUG = True on a production
  server exposed to the WWW is a security hole.
    
  In settings.py, DEBUG = False, results in::

        LOG_DIR = '/var/log/django'
        VAR_RUN_DIR = '/var/run/django'
        VAR_LIB_DIR = '/var/run/django'

 Create and set permissions on LOG_DIR, VAR_RUN_DIR and VAR_LIB_DIR::

        mkdir /var/log/django
        sudo chgrp apache /var/log/django
        sudo chmod g+sw /var/log/django

        mkdir /var/run/django
        sudo chgrp apache /var/run/django
        sudo chmod g+sw /var/run/django

        mkdir /var/lib/django
        sudo chgrp apache /var/lib/django
        sudo chmod g+sw /var/lib/django

6. Initialize the database. 

 This runs migrate command, which should also handle the situation of one of the models changes, or is added or deleted::
    
        ./migrate_db.sh

7. Load the models from the .json files in ncharts/fixtures::

        ./load_db.sh

8. Fetch the static files::

        cd $DJROOT/django-ncharts
        ./get_static_files.sh

 This script will download from the internet the static files needed by the jquery, highcharts, bootstrap, and the moment javascript packages.  The filies will be written to $DJROOT/django-ncharts/ncharts/static/ncharts.

 8.a
  On development server, these static filies will be automatically found and served by the django.contrib.staticfiles django application.

 8.b
  In a production server, the root files go in BASE_DIR/static,
  which is the same as $DJROOT/static. See datavis/settings.py::

       STATIC_ROOT = os.path.join(BASE_DIR,'static')

  This collectstatic command finds the static files in the ncharts directory,
  as well as static files in python site-packages. For example, it finds
  the static files in:
  virtualenvs/django/lib/python3.3/site-packages/datetimewidget/

  It must be run every time django-ncharts/ncharts/static/ncharts/jslib/ncharts.js is changed on the server::

        ./static.sh

9. Memcached:

 The memory caching in django has been configured to use the memcached daemon, and
 a unix socket.  The location of the unix socket is specified as CACHES['LOCATION'] in
 datavis/settings.py::

    'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),

 9.a Development server:
    
  Often on a development server one doesn't enable caching, so that
  changes are seen without nuking the cache.
    
  If you want to test caching, enable the CACHES configuration in settings.py
  so that it is enabled even when DEBUG is true. Then start memcached by hand,
  specifying the location of the socket in the runstring.  On a development server,
  VAR_RUN_DIR is the same as BASE_DIR, the directory containing manage.py.

        cd $DJROOT
        memcached -s ./django_memcached.sock -d

 9.b Production server:
    
  See above for creating and setting permissions on VAR_RUN_DIR.  To setup memcached, do::

        # Configure system to creates /var/run/django on each boot
        sudo cp usr/lib/tmpfiles.d/django.conf /usr/lib/tmpfiles.d
        systemd-tmpfiles --create /usr/lib/tmpfiles.d/django.conf

        sudo cp etc/systemd/system/memcached_django.service /etc/systemd/system
        sudo systemctl daemon.reload
        sudo systemctl enable memcached_django.service
        sudo systemctl start memcached_django.service

        sudo cp etc/systemd/system/memcached_django.service /etc/systemd/system
        sudo systemctl daemon.reload
        sudo systemctl enable memcached_django.service
        sudo systemctl start memcached_django.service

10. Configure and start httpd server


 10.a Development server::

        ./runserver.sh

 10.b Production server:

  If you're paranoid, and want to generate a new SECRET_KEY::

        python -c 'import random; import string; print "".join([random.SystemRandom().choice(string.digits + string.letters + string.punctuation) for i in range(100)])'

  Enter that key in datavis.settings.py.

  Install the httpd configuration files::

        sudo mv /etc/httpd /etc/httpd.orig
        sudo cp -r etc/httpd /etc

  See above for creating and setting permissions on LOG_DIR::

        sudo systemctl enable httpd.service
        sudo systemctl start httpd.service

11. Test!

 On development server:

        http://127.0.0.1:8000/ncharts

 Production server:
        http://127.0.0.1/ncharts


