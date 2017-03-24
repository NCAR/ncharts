#
# Docker image for running ncharts Django application w/ gunicorn
#
#
# https://hub.docker.com/_/python/
#
FROM python:3.3.6
MAINTAINER Erik Johnson <ej@ucar.edu>

RUN apt-get update \
    && apt-get install -y libnetcdf-dev libhdf5-serial-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install numpy

RUN pip install "django<1.9"
RUN pip install pylint_django
RUN pip install pytz

RUN pip install netcdf4
RUN pip install psycopg2

RUN pip install django-datetime-widget
RUN pip install django-timezone-field

RUN pip install python3-memcached

RUN pip install gunicorn

RUN mkdir /app
WORKDIR /app
