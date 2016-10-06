# ncareol/python3-django-datavis

## About

**Docker** image for running [ncharts](https://github.com/ncareol/ncharts/) Django application.

## Tags

- [`0.0.3`](https://github.com/ncareol/ncharts/commit/258bb30)
  - based on [Official Python Docker image](https://hub.docker.com/_/python/), [`3.3.6`](https://github.com/docker-library/python/blob/855b85c8309e925814dfa97d61310080dcd08db6/3.3/Dockerfile)
  - add [`gunicorn`](http://gunicorn.org/) Python package

- [`0.0.2`](https://github.com/ncareol/docker-library/releases/tag/python3-django-datavis-0.0.2)
  - based on official [**CentOS**](https://hub.docker.com/_/centos/) **Docker** image.
  - install `npm`, `git` and `bower` for managing static files

- [`0.0.1`](https://github.com/ncareol/docker-library/releases/tag/python3-django-datavis-0.0.1)
  - based on official [**CentOS**](https://hub.docker.com/_/centos/) **Docker** image.
  - remove `memcached` and `mod_wsgi` dependencies, for smaller image, `614.5 MB`

- [`0.0.0`](https://github.com/ncareol/docker-library/releases/tag/python3-django-datavis-0.0.0)
  - based on official [**CentOS**](https://hub.docker.com/_/centos/) **Docker** image.
  - initial, working functionality
  - minimized image size
