=====
eoldatasite
=====

Simple django web site, for deploying django apps at EOL NCAR.

Detailed documentation is in the "docs" directory.

Quick start
-----------

1. Install required packages:

    sudo yum install python3-django python3-pip

1.a CentOS7 doesn't have python3 or django :-(

    yum install sqlite-devel openssl-devel readline-devel netcdf-devel hdf5-devel

    wget https://www.python.org/ftp/python/3.4.0/Python-3.4.0.tar.xz
    tar -xvf Python-3.4.0.tar.xz
    cd Python-3.4.0
    ./configure --prefix=/usr --with-ensurepip=install
    make
    sudo make install

    sudo python3 -m ensurepip --upgrade

    sudo python3 -m pip install virtualenvwrapper

    sudo python3 -m pip install django

    sudo python3 -m pip install numpy
    sudo python3 -m pip install netCDF4


1.b
    Need the python3 version of django-datetime-widget.

    sudo python3 -m pip install /scr/tmp/maclean/django-datetime-widget-0.9.2.tar.gz

2. Since the django-ncharts app is undergoing many changes, the simplest way to use it 
   is to clone it from github to a neighboring directory, and create a symbolic link:

    cd ..
    git clone https://github.com/ncareol/django-ncharts.git

    cd django-eoldatasite
    ln -s ../../django-ncharts/ncharts .

    ncharts is listed as an INSTALLED_APPS in eoldatasite/settings.py, as is datetimewidget.

    ncharts is also specified in eoldatasite/urls.py.

3. Initialize the database:
    
    rm -f db.sqlite3
    ./syncdb.sh

4. Update the models

   cd ncharts/fixtures

   edit \*.json

5. Load the models

    ./load.sh


6. Start the development server:
    ./runserver.sh
    

5. Visit http://127.0.0.1:8000/ncharts
