eol-django-datavis
==================

Data plotting Web application, developed at NCAR EOL.

Setup and Starting a Production Server
------------------------------------------------------------

The following is for RedHat systems, such as CentOS or Fedora.

1. Install required packages

 This is the same as step one of in setting up a development server. See README-devel.

2. Decide where to put the django code and configuration.

 We'll call that $DJROOT.  Files for production server at EOL have been put on /var/django::

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

 A virtual environment allows you to run specific versions of python packages without effecting other users on the system.  These commands will create a django virtual environment in $DJROOT::

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
    python3 -m pip install --upgrade psycopg2

    python3 -m pip install django-datetime-widget
    python3 -m pip install django-timezone-field

    python3 -m pip install python3-memcached

 Install mod_wsgi.  This RPM for CentOS7 is on the EOL repo::

    sudo yum install httpd python3-mod_wsgi

5. Configuration

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

6. Initialize the database

 This runs the django migrations commands, which should also handle the situation of one of the models changes, or is added or deleted::
    
    ./migrate_db.sh

 If the db.sqlite3 database has not been created yet, you will be prompted to enter an administrator's user name, email and password. You can use your own user name and email address. If the server will be exposed to the internet, you should enter a secure password, but to be paranoid, I'd suggest not using your UCAS or EOL server password.

 Migrations in django are a bit complicated. If the above script fails you may have to reset the migration history for ncharts::

    rm /var/lib/django/db.sqlite3
    rm -rf ncharts/migrations

 Then run the migration script again.

7. Load the models from the .json files in ncharts/fixtures::

    ./load_db.sh

8. Fetch the static files

 To fetch the static files of the supporting software used by ncharts, such as jquery, bootstrap and highcharts do::

    cd $DJROOT/django-ncharts
    ./get_static_files.sh

 The filies will be written to $DJROOT/django-ncharts/ncharts/static/ncharts.

 Then on a production server, execute the static.sh shell script::
 
    ./static.sh

 This shell script executes the django *collectstatic* command to find the static files in the ncharts directory, as well as static files in python site-packages, and copies them to BASE_DIR/static.

 On a production server, the root files go in BASE_DIR/static, which is the same as $DJROOT/static. See datavis/settings.py::

    STATIC_ROOT = os.path.join(BASE_DIR,'static')

 On a production server, static.sh must be run every time django-ncharts/ncharts/static/ncharts/jslib/ncharts.js is changed on the server.

 To see what static files are needed for ncharts, see the <script> tags in django-ncharts/ncharts/templates/ncharts/base.html.

9. Memcached:

 The memory caching in django has been configured to use the memcached daemon, and
 a unix socket.  The location of the unix socket is specified as CACHES['LOCATION'] in
 datavis/settings.py::

    'LOCATION': 'unix:' + os.path.join(VAR_RUN_DIR,'django_memcached.sock'),

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

 If you're paranoid, and want to generate a new SECRET_KEY::

     python -c 'import random; import string; print "".join([random.SystemRandom().choice(string.digits + string.letters + string.punctuation) for i in range(100)])'

 Enter that key in datavis.settings.py.

 Install the httpd configuration files::

    sudo mv /etc/httpd /etc/httpd.orig
    sudo cp -r etc/httpd /etc

Tweak the umask of the systemd service, so that apache group members can read/write the log files::
    sudo mkdir /etc/systemd/system/httpd.service.d
    cat << EOD > /tmp/umask.conf
    [Service]
    UMask=0007
    EOD

    sudo cp /tmp/umask.conf /etc/systemd/system/httpd.service.d
    sudo systemctl daemon-reload

 See above for creating and setting permissions on LOG_DIR::

    sudo systemctl enable httpd.service
    sudo systemctl start httpd.service

11. Test!

    http://localhost/ncharts

12. Clearing expired sessions and unattached ClientState objects

 This is done from a crontab on the server::
    crontab -l
    MAILTO=maclean@ucar.edu
    #
    # On Sundays, clear expired sessions and then the unattached clients
    0 0 * * 0 cd /var/django/eol-django-datavis; source ../virtualenv/django/bin/activate; ./manage.py clearsessions; ./manage.py clear_clients

