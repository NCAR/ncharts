=====
eoldjango-datavis
=====

Software for a django web service at EOL NCAR.

Detailed documentation is in the "docs" directory.

Setup and Starting
-----------

The following is for RedHat systems, such as CentOS or Fedora.

1. Install required packages:

   Redhat does not (yet!) provide an RPM for python3 in CentOS, even CentOS7.

   RPMs for python3 and python3-devel are available on the EOL yum repo for
   CentOS7, but not CentOS6. See the SEW wiki at http://wiki.eol.ucar.edu/sew/EOL_YUM_Repository

    sudo yum install python3 python3-pip python3-memcached \
        memcached python3-mod_wsgi python3-devel

    sudo python3 -m pip install virtualenv

    sudo python3 -m pip install virtualenvwrapper


2. Create virtual environment

   A virtual environment allows you to run specific versions of python
   packages without effecting other users on the system.

   Once the virtual environment has been created, it must be activated for each
   shell where you run python django commands from.
   
   In the following sections you will see this command:

    source $DJVIRT/bin/activate

   It only needs to be done once for each shell.  If you see "(django)" in your
   shell prompt, it is not necessary to activate it again.

2.a Development server

    mkdir $HOME/virtualenvs

    cd $HOME/virtualenvs
    virtualenv -p /usr/bin/python3 django

    DJVIRT=$HOME/virtualenvs/django
    source $DJVIRT/bin/activate

2.b Production Server (apache)

    sudo mkdir /var/django
    sudo chown www.www /var/django
    cd /var/django
    mkdir virtualenv
    cd virtualenv
    virtualenv -p /usr/bin/python3 django

    DJVIRT=/var/django/virtualenv/django
    source $DJVIRT/bin/activate

3. Add other Python packages to virtual environment

    source $DJVIRT/bin/activate

    python3 -m pip install django
    python3 -m pip install numpy
    python3 -m pip install netCDF4

   Python3 version of django-datetime-widget.

    python3 -m pip install ~maclean/git/django-datetime-widget/dist/django-datetime-widget-0.9.2.tar.gz

    python3 -m pip install python3-memcached

3. For a production server, install mod_wsgi

   This RPM for CentOS7 is on the EOL repo.

    sudo yum install httpd python3-mod_wsgi


4. Since the django-ncharts app is undergoing many changes, the simplest way to use it 
   is to clone it from github to a neighboring directory, and create a symbolic link:

    cd ..
    git clone https://github.com/ncareol/django-ncharts.git

    cd eol-django-datavis
    ln -s ../../django-ncharts/ncharts .

    ncharts is listed in INSTALLED_APPS in datavis/settings.py, as is datetimewidget.

    ncharts is also specified in datavis/settings.py.

5. Configuration

5.a Development server
    Edit datavis/settings.py and set DEBUG = True. Note that this results in
    following other settings:
         VAR_RUN_DIR = BASE_DIR
         LOG_DIR = os.path.join(BASE_DIR,'log')

    BASE_DIR is the name of the directory containing manage.py.

    The database and memcached socket are kept on VAR_RUN_DIR.

    Create the log directory:
        mkdir log

5.a Production server

    Set DEBUG = False in datavis/settings.py, which results in:

        LOG_DIR = '/var/log/django'
        VAR_RUN_DIR = '/var/run/django'

    Create and set permissions on LOG_DIR and VAR_RUN_DIR:

        mkdir /var/log/django
        sudo chown apache.apache /var/run/django
        mkdir /var/run/django
        sudo chown apache.apache /var/log/django


6. Initialize the database. You may want to delete it if the structure of the
   models changes. Need to look into migration.
    
        source $DJVIRT/bin/activate
        ./syncdb.sh

7. Load the models from the .json files in ncharts/fixtures:

        source $DJVIRT/bin/activate
        ./load.sh

8. Static files:

8.a
   Development server: nothing to do.
8.b
   Production server, datavis/settings.py:
       STATIC_ROOT = os.path.join('/var/django','static')

        source $DJVIRT/bin/activate
        python3 manage.py collectstatic

9. Start Memcached:
   The memory caching in django has been configured to use the memcached daemon, and
   a unix socket.  The location of the unix socket is specified as CACHES['LOCATION'] in
   datavis/settings.py:
        'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),

9.a Development server:
    
    Start memcached, specifying the location of the socket in the runstring.
    On a development server, VAR_RUN_DIR is the same as BASE_DIR, the directory
    containing manage.py. Assuming that is your current directory:

        memcached -s ./django_memcached.sock -d

9.b Production server:
    
    See above for creating and setting permissions on VAR_RUN_DIR.

        sudo cp etc/systemd/system/memcached_django.service /etc/systemd/system
        sudo systemctl daemon.reload
        sudo systemctl enable memcached_django.service
        sudo systemctl start memcached_django.service

10 Configure and start httpd server


10.a Development server:

        ./runserver.sh

10.b Production server:
    Install the httpd configuration files.

        sudo mv /etc/httpd /etc/httpd.orig
        sudo cp -r etc/httpd /etc

    See above for creating and setting permissions on LOG_DIR.

        sudo systemctl enable httpd.service
        sudo systemctl start httpd.service

    
11. Test!
    On development server:
        http://127.0.0.1:8000/ncharts

    Production server:
        http://127.0.0.1/ncharts


