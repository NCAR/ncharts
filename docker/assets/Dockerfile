#
# manage ncharts assets w/ bower
#
# https://hub.docker.com/r/mhart/alpine-node/
#
FROM mhart/alpine-node
MAINTAINER Erik Johnson <ej@ucar.edu>

RUN apk add --no-cache curl rsync git
RUN npm install -g bower

RUN mkdir /app
WORKDIR /app
