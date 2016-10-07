# ncharts Docker

This directory, `docker/`, contains files for building and configuring **Docker** images that are used by `ncharts` **Docker Compose** services, which are defined in `docker-compose*.yml` in the root directory of this project.

## Services

`app`: Image for running `ncharts` **Python** **Django** application via `gunicorn` w/ dependencies installed.

`assets`: Image for managing **JavaScript** and **CSS** assets w/ `bower`

`web`: Config for `nginx` web front-end. **Docker Compose** service mounts `default.conf` to `nginx`'s `conf.d` directory.

## Images

Images are typically built by `cd`'ing to the service's respective directory and running:

```sh
$ docker build .
```
