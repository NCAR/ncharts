# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014 Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

import os, sys
import netCDF4
from datetime import datetime
import pytz
import numpy
import logging
import operator
from functools import reduce

from ncharts import exceptions

# __name__ is ncharts.netcdf
logger = logging.getLogger(__name__)

class NetCDFDataset:
    ''' alternative to netCDF4.MFDataset, allowing for a variable to be missing in
    one or more files.
    '''

    def __init__(self, paths, time_names=['time','Time','time_offset']):
        """
        """

        self.paths = paths
        self.variables = {}


        for path in self.paths:
            try:
                # logger.debug("path=%s",path)
                ds = netCDF4.Dataset(path)

                if not hasattr(self,"base_time") and "base_time" in ds.variables:
                    self.base_time = "base_time"

                tdim = None
                for tname in ['time','Time']:
                    if tname in ds.dimensions:
                        tdim = ds.dimensions[tname]
                        # tdim.is_unlimited
                        if not hasattr(self,"time_dim"):
                            self.time_dim = tname
                if not tdim:
                    continue

                if "station" in ds.dimensions:
                    if not hasattr(self,"nstations"):
                        self.nstations = len(ds.dimensions["station"])
                        self.station_dim = "station"
                    elif not self.nstations == len(ds.dimensions["station"]):
                        logger.warning("%s: station dimension (%d) is different than that of other files (%d)",
                                path,len(ds.dimensions["station"]),self.nstations)

                    if not "station_names" in self and "station" in ds.variables:
                        var = ds.variables["station"]
                        if var.datatype == numpy.dtype('S1'):
                            self.station_names = [str(netCDF4.chartostring(v)) for v in var]

                if not hasattr(self,"time_name"):
                    for (n,v) in ds.variables.items():
                        if n in time_names and tdim._name in v.dimensions:
                            self.time_name = n
                            break
                    if not hasattr(self,"time_name"):   # time variable not found in file
                        continue

                for (n,v) in ds.variables.items():
                    if tdim._name in v.dimensions:
                        if not n in self.variables:
                            if n != self.time_name:
                                self.variables[n] = {}
                                self.variables[n]["shape"] = v.shape
                                # don't need _FillValue
                                for a in ["units","long_name","short_name"]:
                                    if hasattr(v,a):
                                        self.variables[n][a] = getattr(v,a)
                        elif self.variables[n]["shape"][1:] != v.shape[1:]:
                            # the above check works even if either shape has length 1
                            if len(self.variables[n]["shape"]) != len(v.shape):
                                # changing number of dimensions, punt
                                logger.error("%s: %s: changing number of dimensions: %d and %d. Skipping this variable.",
                                    path,n,len(v.shape),len(self.variables[n]["shape"]))
                                del(self.variables[n])
                                continue
                            # here we know that shapes have same length and they must have len > 1
                            # allow final dimension to change.
                            ld = len(v.shape)
                            if self.variables[n]["shape"][1:(ld-1)] != v.shape[1:(ld-1)]:
                                logger.error("%s: %s: incompatible shapes: %s and %s. Skipping this variable.",
                                    path,n,repr(v.shape),repr(self.variables[n]["shape"]))
                                del(self.variables[n])
                                continue
                            # set shape to max shape (leaving the problem for later...)
                            self.variables[n]["shape"] = tuple([max(i,j) for (i,j) in zip(self.variables[n]["shape"],v.shape)])

            finally:
                ds.close()

    def read(self,variables=[],start_time=datetime.min,end_time=datetime.max,
            selectdim={},size_limit=1000 * 1000 * 1000):
        """ Read a list of variables from this fileset.
        """

        data = {}
        times = []
        total_size = 0
        for path in self.paths:
            # logger.debug("path=%s",path)
            try:
                ds = netCDF4.Dataset(path)

                dsdata = {}

                base_time = None

                if hasattr(self,"base_time") and self.base_time in ds.variables and len(ds.variables[self.base_time].dimensions) == 0:
                    base_time = ds.variables[self.base_time].getValue()
                    # print("base_time=",base_time)

                if not hasattr(self,"time_name"):
                    continue

                if self.time_name in ds.variables:
                    var = ds.variables[self.time_name]
                    if hasattr(var,"units") and 'since' in var.units:
                        try:
                            # tv = [d for d in netCDF4.num2date(var[:],var.units,'standard')]
                            # if tv[0].tzinfo == None or tv[0].tzinfo.utcoffset() == None:
                            #     print("tz[0] is naive")
                            # times from netCDF4.num2date are naive.
                            tv = [d.replace(tzinfo=pytz.UTC) for d in netCDF4.num2date(var[:],var.units,'standard')]
                        except TypeError:
                            if base_time:
                                logger.error("%s: %s: cannot parse units: %s, using base_time instead",
                                        os.path.split(path)[1],self.time_name,var.units)
                                tv = [ datetime.fromtimestamp(base_time + val,tz=pytz.utc) for val in var[:] ]
                            else:
                                logger.error("%s: %s: cannot parse units: %s",
                                        os.path.split(path)[1],self.time_name,var.units)
                                tv = [ datetime.fromtimestamp(val,tz=pytz.utc) for val in var[:] ]
                    else:
                        tv = [ datetime.fromtimestamp(base_time + val,tz=pytz.utc) for val in var[:] ]

                    # tv = [d.timestamp() for d in netCDF4.num2date(var[:],var.units,'standard')]

                    tindex = [ i for i,t in enumerate(tv) if t >= start_time and t < end_time]
                    if len(tindex) == 0:
                        logger.warning("%s: no times found, start_time=%s, end_time=%s, file times=%s - %s",

                            os.path.split(path)[1],
                            start_time.isoformat(), end_time.isoformat(),
                            tv[0].isoformat(),tv[-1].isoformat())

                    else:
                        logger.debug("%s: tv[min(tindex)=%d]=%d ,tv[max(tindex)=%d]=%d, start_time=%s, end_time=%s",
                            os.path.split(path)[1],min(tindex),tv[min(tindex)].timestamp(),
                            max(tindex),tv[max(tindex)].timestamp(),
                            start_time,end_time)


                    times.extend([tv[i] for i in tindex])
                    total_size += len(tindex) * sys.getsizeof(tv[0])
                    if total_size > size_limit:
                        raise exceptions.TooMuchDataException("too much data requested, will exceed {} mbytes".format(size_limit/(1000 * 1000)))
                else:
                    continue

                time_index = None
                for vname in variables:
                    if vname in self.variables and vname in ds.variables:
                        # maximum shape of this variable in all files
                        vshape = self.variables[vname]["shape"]
                        var = ds.variables[vname]

                        # if var.shape[1:] != vshape[1:]:
                        #     continue

                        # if len(var.dimensions) < 1 or not var.dimensions[0] == self.time_dim:
                        #     continue

                        # user has asked for variables with a certain dimension
                        for d in selectdim:
                            if not d in var.dimensions:
                                # desired dimension is not in this variable
                                if type(selectdim[d]) == type([]):
                                    # if selectdim[d] is a list, check for any negative values
                                    # in it, where -1 indicates all values.
                                    # For example, station=[-1,0,2] indicates that variables
                                    # without a station dimension, as well as stations 0 and 2 re 
                                    # wanted.
                                    if not any(i < 0 for i in selectdim[d]):
                                        continue
                        idx = ()
                        for d in var.dimensions:
                            if d == self.time_dim:
                                time_index = len(idx)
                                idx += (tindex,)
                            elif d == "sample":
                                # deal with this later...
                                idx += (0,)
                            elif d in selectdim:
                                if type(selectdim[d]) == type([]):
                                    idx += (sort([i for i in selectdim[d] if i >= 0]))
                                else:
                                    idx += (selectdim[d],)
                            else:
                                # idx += (6,)
                                idx += (slice(0,len(ds.dimensions[d])),)

                        if (len(tindex) > 0):
                            logger.debug("%s: %s: min(tindex),max(tindex)=%d,%d, idx[1:]=%s",
                                    os.path.split(path)[1],vname,min(tindex),max(tindex),
                                repr(idx[1:]))

                        # dsdata[vname] = var[:].filled(fill_value=float('nan'))[idx]

                        var = var[idx]
                        if isinstance(var,numpy.ma.core.MaskedArray):
                            dsdata[vname] = var.filled(fill_value=float('nan'))
                        else:
                            dsdata[vname] = var

                        if (len(tindex) > 0):
                            total_size += reduce(operator.mul,dsdata[vname].shape,1) * sys.getsizeof(dsdata[vname][tuple([0 for i in dsdata[vname].shape])])
                            if total_size > size_limit:
                                raise exceptions.TooMuchDataException("too much data requested, will exceed {} mbytes".format(size_limit/(1000 * 1000)))
            finally:
                ds.close()

            dim2 = []
            for vname in variables:

                # shape of variable after selecting times
                shape = list(self.variables[vname]['shape'])
                shape[time_index] = len(tindex)
                shape = tuple(shape)

                if len(shape) > 1:
                    dim2 = [ i for i in range(shape[1])]

                if not vname in dsdata:
                    total_size += reduce(operator.mul,shape,1) * sys.getsizeof(numpy.float())
                    if total_size > size_limit:
                        raise exceptions.TooMuchDataException("too much data requested, will exceed {} mbytes".format(size_limit/(1000 * 1000)))

                    dfill = numpy.ma.array(data=numpy.empty(
                            shape=shape,dtype=float),
                            mask=True,fill_value=float('nan')).filled()
                    if not vname in data:
                        data[vname] = dfill
                    else:
                        data[vname] = numpy.append(data[vname],dfill,axis=time_index)
                else:
                    if shape[1:] != dsdata[vname].shape[1:]: 
                        # changing shape. Add support for final dimension increasing
                        ashape = list(shape)
                        last = len(ashape) - 1
                        # how much to grow it by
                        ashape[last] = ashape[last] - dsdata[vname].shape[last]
                        dsdata[vname] = numpy.append(dsdata[vname],
                            numpy.ma.array(data=numpy.empty(
                                shape=ashape,dtype=float),
                                mask=True,fill_value=float('nan')).filled(),axis=last)

                    if not vname in data:
                        data[vname] = dsdata[vname]
                    else:
                        data[vname] = numpy.append(data[vname], dsdata[vname],axis=time_index)

        for vname in data.keys():
            logger.debug("data[%s].shape=%s",vname,repr(data[vname].shape))
        logger.debug("total_size=%d",total_size)

        return {"time" : times, "data": data, "dim2": dim2 }


