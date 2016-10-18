# Using ncharts w/ Docker

[Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) are used to containerize and orchestrate services required by **ncharts**:

- `app`: **Python3** for running the **ncharts** **Django** application
- `web`: **Nginx** front end for serving static assets and proxying dynamic requests to `app` backend
- `cache`: **memcached** application cache
- `assets`: **bower** for managing static assets

## Install Docker and Docker Compose

### RHEL

```sh
$ sudo yum install docker
$ curl -L https://github.com/docker/compose/releases/download/1.8.0/docker-compose-`uname -s`-`uname -m` > /tmp/docker-compose
$ chmod +x /tmp/docker-compose
$ sudo mv /tmp/docker-compose /usr/local/bin/
```

Enable **Docker** in `systemd` and start:

```sh
$ sudo systemctl enable docker
$ sudo systemctl start docker
```

Group:

```sh
$ sudo groupadd docker
$ sudo usermod -aG docker `whoami`
$ newgrp docker
```

## Running

The following workflow makes use of **Docker Compose's** support of `override` files. For more information, see the documentation:

<https://docs.docker.com/compose/extends/>

```sh
$ ln -s docker/docker-compose-base.yml docker-compose.yml
```

### Dev

Use an existing `override` file, or create and link to your own:

```sh
$ ln -s docker/docker-compose-dev.override.yml docker-compose.override.yml
```

Start **ncharts** services w/ **Docker Compose**:

```
$ docker-compose up
```

### Ops

Use an existing `override` file, or create and link to your own:

```sh
$ ln -s docker/docker-compose-ops.override.yml docker-compose.override.yml
```

Start **ncharts** services w/ **Docker Compose**:

```sh
$ NCHARTS_SECRET_KEY=abc123 docker-compose up
```

### Assets

To perform operations for updating **JavaScript** and **CSS** assets, use the `assets` service provided `docker/docker-compose-assets.yml`, *e.g.*:

```sh
$ docker-compose -f docker/docker-compose-assets.yml run assets get_static_files.sh
```

### Systemd

Copy the host-specific `docker-compose-ncharts.service` file to `/etc/systemd/system`. *E.g.* for `datavis`:

```sh
$ cp etc/vagrant/systemd/system/docker-compose-ncharts.service /etc/systemd/system
```

Then enable and start the service:

```sh
$ systemctl enable /etc/systemd/system/docker-compose-ncharts.service
$ systemctl start docker-compose-ncharts.service
```

If you make any changes to the `service` file, you'll need to load the changes into `systemd`:

```sh
$ systemctl reload docker-compose-ncharts.service
```
