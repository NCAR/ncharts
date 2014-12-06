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

   RPM for python3 and python3-devel are available on the EOL yum repo for
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

    ncharts is listed in INSTALLED_APPS in datavis.py, as is datetimewidget.

    ncharts is also specified in datavis.py.


5. Configure for local installation:

5.a Development server
    Edit datavis.py, and set LOG_DIR and the CACHES location to
    somehere you have write permission. You could use BASE_DIR:

        LOG_DIR = BASE_DIR
        VAR_RUN_DIR = BASE_DIR
        ...
        DATABASES = {
                    'NAME': os.path.join(VAR_RUN_DIR, 'db.sqlite3'),
        }
        CACHES = {
            'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock')
        }

5.a Production server

        LOG_DIR = '/var/log/django'
        VAR_RUN_DIR = '/var/run/django'
        ...
        DATABASES = {
                    'NAME': os.path.join(VAR_RUN_DIR, 'db.sqlite3'),
        }
        CACHES = {
            'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),
        }


6. Initialize the database. You may want to delete it if the structure of the
   models changes.
    
    source $DJVIRT/bin/activate
    ./syncdb.sh

7. Load the models from the .json files in ncharts/fixtures:

    source $DJVIRT/bin/activate
    ./load.sh

8. Gather static files:

    source $DJVIRT/bin/activate
    python3 manage.py collectstatic

9. Start Memcached:

9.a Development server:
    The location of django_memcached.sock should correspond to
    the path set in datavis.py.

    memcached -s ./django_memcached.sock -d

9.b Production server:
    
    sudo mkdir /var/run/django
    sudo chown apache.apache /var/run/django

    sudo cp etc/systemd/system/memcached_django.service /etc/systemd/system
    sudo systemctl daemon.reload
    sudo systemctl enable memcached_django.service
    sudo systemctl start memcached_django.service


10 Configure and start httpd server

10.a Production server:

    sudo mv /etc/httpd /etc/httpd.orig
    sudo cp -r etc/httpd /etc

    mkdir /var/log/django
    sudo chown apache.apache /var/log/django

    sudo systemctl enable httpd.service
    sudo systemctl start httpd.service

10.b Development server:
    ./runserver.sh
    
11. Test!
    On development server:
        http://127.0.0.1:8000/ncharts

    Production server:
        http://127.0.0.1/ncharts


