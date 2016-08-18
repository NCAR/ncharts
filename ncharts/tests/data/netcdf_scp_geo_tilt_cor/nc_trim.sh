#!/bin/sh

vars=station,latitude,longitude,altitude,base_time,time,w_1m,w_w__1m,w_tc__1m,w_2m_C,w_w__2m_C,w_tc__2m_C


for f in *.nc; do

    cnts1=$(ncdump -h $f | fgrep w_1m:counts | sed -r 's/^[^"]+"([^"]+)".*$/\1/')
    cnts2=$(ncdump -h $f | fgrep w_2m_C:counts | sed -r 's/^[^"]+"([^"]+)".*$/\1/')
    ncks -v $vars,$cnts1,$cnts2 -O $f $f
done

