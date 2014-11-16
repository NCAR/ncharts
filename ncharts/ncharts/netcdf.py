# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014 Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

import os
import netCDF4
from datetime import datetime
import pytz
import numpy
import logging

logger = logging.getLogger(__name__)

class NetCDFDataset:
    ''' alternative to netCDF4.MFDataset, allowing for a variable to be missing in
    one or more files.
    '''

    def __init__(self, files, time_names=['time','time_offset']):
        """
        """

        self.files = files
        self.variables = {}

        for file in self.files:
            try:
                # logger.debug("file=%s",file)
                ds = netCDF4.Dataset(file)

                if not hasattr(self,"base_time") and "base_time" in ds.variables:
                    self.base_time = "base_time"

                if not hasattr(self,"time_dim") and "time" in ds.dimensions:
                    tdim = ds.dimensions["time"]
                    # tdim.is_unlimited
                    self.time_dim = "time"
                else:
                    continue

                if "station" in ds.dimensions:
                    if not hasattr(self,"nstations"):
                        self.nstations = len(ds.dimensions["station"])
                        self.station_dim = "station"
                    elif not self.nstations == len(ds.dimensions["station"]):
                        logger.warning("%s: station dimension (%d) is different than that of other files (%d)",
                                file,len(ds.dimensions["station"]),self.nstations)

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
                            if not n == self.time_name:
                                self.variables[n] = {}
                                self.variables[n]["shape"] = v.shape
                                # don't need _FillValue
                                for a in ["units","long_name","short_name"]:
                                    if hasattr(v,a):
                                        self.variables[n][a] = getattr(v,a)
                        elif not self.variables[n]["shape"][1:] == v.shape[1:]:
                            logger.warning("%s: %s: shape (%s) is different than in other files (%s). Skipping this variable.",
                                file,n,repr(v.shape),repr(self.variables[n]["shape"]))
                            del(self.variables[n])
                            continue

            finally:
                ds.close()

    def read(self,variables=[],start_time=datetime.min,end_time=datetime.max,
            selectdim={}):
        """ Read a list of variables from this fileset.
        """

        data = {}
        times = []
        for file in self.files:
            # logger.debug("file=%s",file)
            try:
                ds = netCDF4.Dataset(file)

                dsdata = {}

                base_time = 0

                if hasattr(self,"base_time") and self.base_time in ds.variables and len(ds.variables[self.base_time].dimensions) == 0:
                    base_time = ds.variables[self.base_time].getValue()

                if not hasattr(self,"time_name"):
                    continue

                if self.time_name in ds.variables:
                    var = ds.variables[self.time_name]
                    if hasattr(self,"units") and 'since' in var.units:
                        tv = [d.replace(tzinfo=pytz.UTC) for d in netCDF4.num2date(var[:],var.units,'standard')]
                        # tv = [d.timestamp() for d in netCDF4.num2date(var[:],var.units,'standard')]
                    else:
                        tv = [ datetime.fromtimestamp(base_time + val,tz=pytz.utc) for val in var[:] ]
                    tindex = [ i for i,t in enumerate(tv) if t >= start_time and t < end_time]
                    times.extend([tv[i] for i in tindex])
                else:
                    continue

                time_index = None
                for vname in variables:
                    if vname in self.variables and vname in ds.variables:
                        vshape = self.variables[vname]["shape"]
                        var = ds.variables[vname]

                        if var.shape[1:] != vshape[1:]:
                            continue

                        # if len(var.dimensions) < 1 or not var.dimensions[0] == self.time_dim:
                        #     continue

                        # user has asked for variables with a certain dimension
                        for d in selectdim:
                            if not d in var.dimensions:
                                if type(selectdim[d]) == type([]):
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

                        logger.debug("%s: %s: idx=%s",os.path.split(file)[1],vname,repr(idx))

                        # dsdata[vname] = var[:].filled(fill_value=float('nan'))[idx]

                        var = var[idx]
                        if isinstance(var,numpy.ma.core.MaskedArray):
                            dsdata[vname] = var.filled(fill_value=float('nan'))
                        else:
                            dsdata[vname] = var
            finally:
                ds.close()

            for vname in variables:

                # change length of time dimension in variable shape.
                shape = list(self.variables[vname]['shape'])
                shape[time_index] = len(tindex)
                shape = tuple(shape)

                if not vname in dsdata:
                    if not vname in data:
                        data[vname] = numpy.ma.array(data=numpy.empty(
                            shape=shape,dtype=float),
                            mask=True,fill_value=float('nan')).filled()
                    else:
                        data[vname] = numpy.append(data[vname],
                                numpy.ma.array(data=numpy.empty(
                                    shape=shape,dtype=float),
                                    mask=True,fill_value=float('nan')).filled(),axis=time_index)
                else:
                    if not vname in data:
                        data[vname] = dsdata[vname]
                    else:
                        data[vname] = numpy.append(data[vname], dsdata[vname],axis=time_index)

        for vname in data.keys():
            logger.debug("data[%s].shape=%s",vname,repr(data[vname].shape))


        return {"time" : times, "data": data }


