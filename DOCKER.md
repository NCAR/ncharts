# Using ncharts w/ Docker

## Install Docker and Docker Compose

### RHEL

```sh
$ sudo yum install docker
$ curl -L https://github.com/docker/compose/releases/download/1.8.0/$ docker-compose-`uname -s`-`uname -m` > /tmp/docker-compose
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

Start `ncharts` services w/ **Docker Compose**:

```
$ EOL_DATAVIS_SECRET_KEY=abc123 docker-compose up
```

### Ops

Use an existing `override` file, or create and link to your own:

```sh
$ ln -s docker/docker-compose-ops.override.yml docker-compose.override.yml
```

Start `ncharts` services w/ **Docker Compose**:

```sh
$ docker-compose up
```

### Assets

To perform operations for updating **JavaScript** and **CSS** assets, use the `assets` service provided `docker/docker-compose-assets.yml`, *e.g.*:

```sh
$ docker-compose -f docker/docker-compose-assets.yml run assets get_static_files.sh
```
