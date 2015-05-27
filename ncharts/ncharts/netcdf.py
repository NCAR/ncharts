# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Support for reading meta-data and data NetCDF files, primarily
time-series data.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

import os, sys, time
import netCDF4
from datetime import datetime
import pytz
import numpy as np
import logging
import operator

from functools import reduce as reduce_

from ncharts import exceptions
from ncharts import fileset as nc_fileset

# __name__ is ncharts.netcdf
_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

class NetCDFDataset(object):
    """ Alternative class to netCDF4.MFDataset.

    Supports reading a list of time-series variables from a
    collection of files concatenating the results over the
    time-dimension of the variables.

    Also handles other situations that may arise, such as if the
    non-time dimensions for a variable change from file to file, in
    which case the result will have the largest non-time dimensions,
    with the extra values filled in.

    Also attempts to handle the situation when the type of a variable
    is not consistant over the collection of files.

    Attributes:
        fileset: The nc_fileset.FileSet encapsulating a set of files.
        variables: Dict of dicts for all time-series variables found in
            dataset by variable name:
                { 'shape': tuple of integer dimensions of the variable,
                  'dimnames': tuple of str dimension names for variable,
                  'units': str value of "units" attribute if found,
                  'long_name': str value of "long_name" attribute if found,
                  'short_name': str value of "short_name" attribute if found,
                  'dtype': numpy.dtype of the variable
               }.
        base_time: str name of base_time variable if found in the dataset.
        time_dim:  str name of the time dimension in this dataset.
        time_name: str name of time variable.
        nstations: int length of NetCDF "station" dimension in this dataset,
            if found.
        station_dim:  str name of NetCDF "station" dimension, currently always
            "station".
        station_names: If a NetCDF character variable called "station"
            is found, a list of str values of the variable.
    """
    # pylint thinks this class is too big.
    # pylint: disable=too-many-instance-attributes

    def __init__(self, path):
        """Constructs NetCDFDataset with a path to a filesetFileset.

        """

        self.fileset = nc_fileset.Fileset.get(path)
        self.variables = {}
        self.base_time = None
        self.time_dim = None
        self.time_name = None
        self.nstations = None
        self.station_dim = None
        self.station_names = None

    def get_filepaths(self, start_time, end_time):
        """Return the file path names matching the time period.
        Args:
            start_time: datetime.datetime of start of fileset scan.
            end_time: end of fileset scan.
        """
        return [f.path for f in self.fileset.scan(start_time, end_time)]

    def get_variables(
            self,
            start_time=pytz.utc.localize(datetime.min),
            end_time=pytz.utc.localize(datetime.max),
            time_names=('time', 'Time', 'time_offset')):
        """ Scan the set of files for time series variables.

        Args:
            start_time: datetime.datetime of start of fileset scan.
            end_time: end of fileset scan.
            time_names: List of allowed names for time variable.
        """

        filepaths = self.get_filepaths(start_time, end_time)

        for ncpath in filepaths:

            # The files might be in the process of being moved, deleted, etc,
            # so if we get an exception in this open, try a few more times.

            # Testing indicates that with a truncated file (artificially
            # truncated with dd), the underlying C code will cause a crash
            # of python from an assert() rather than raising an exception
            # that could be caught.

            # If the netcdf library is compiled with -DNDEBUG, then the
            # the open and parse of the truncated header succeeds, but
            # still no exception.

            # If the file is artificially corrupted by removing an
            # initial portion of the file:
            #   dd if=test.nc of=bad.nc bs=1014 count=100 skip=1
            # then an exception is raised (this was with -DNDEBUG):
            # RuntimeError bad.nc: NetCDF: Unknown file format

            # To make this robust, it would be good to run a king's
            # taster process on each file first to reduce the possibility
            # of a server death. The king's taster would not use NDEBUG,
            # but perhaps the python server would.  Complicated.

            fileok = False
            for itry in range(0, 3):
                try:
                    # _logger.debug("ncpath=%s",ncpath)
                    ncfile = netCDF4.Dataset(ncpath)
                    fileok = True
                    break
                except IOError as exc:
                    _logger.error("%s: %s", ncpath, exc)
                    time.sleep(itry)
                except RuntimeError as exc:
                    _logger.error("%s: %s", ncpath, exc)
                    time.sleep(itry)

            if not fileok:
                continue

            try:
                if not self.base_time and \
                    "base_time" in ncfile.variables:
                    self.base_time = "base_time"

                tdim = None
                # look for a time dimension
                for tname in ['time', 'Time']:
                    if tname in ncfile.dimensions:
                        tdim = ncfile.dimensions[tname]
                        break
                if not tdim:
                    continue

                # check for tdim.is_unlimited?
                if not self.time_dim:
                    self.time_dim = tdim.name

                if "station" in ncfile.dimensions:
                    if not self.nstations:
                        self.nstations = len(ncfile.dimensions["station"])
                        self.station_dim = "station"
                    elif not self.nstations == \
                            len(ncfile.dimensions["station"]):
                        _logger.warning(
                            "%s: station dimension (%d) is "
                            "different than that of other files (%d)",
                            ncpath,
                            len(ncfile.dimensions["station"]),
                            self.nstations)

                    if not self.station_names and "station" in ncfile.variables:
                        var = ncfile.variables["station"]
                        if var.datatype == np.dtype('S1'):
                            self.station_names = [str(netCDF4.chartostring(v))
                                                  for v in var]

                if not self.time_name:
                    # pylint doesn't think ncfile.variables has an items()
                    # pylint: disable=no-member
                    for (vname, var) in ncfile.variables.items():
                        if vname in time_names and tdim.name in var.dimensions:
                            self.time_name = vname
                            break
                    if not self.time_name:
                        # time variable not found in file
                        continue

                # pylint: disable=no-member
                for (vname, var) in ncfile.variables.items():

                    # looking for time series variables
                    if not self.time_dim in var.dimensions:
                        continue

                    # time variable
                    if vname == self.time_name:
                        continue

                    # var.dimensions is a tuple the dimension names
                    time_index = var.dimensions.index(self.time_dim)

                    # Check if we have found this variable in a earlier file
                    if not vname in self.variables:
                        self.variables[vname] = {}
                        self.variables[vname]["shape"] = var.shape
                        self.variables[
                            vname]["dimnames"] = var.dimensions
                        self.variables[vname]["dtype"] = var.dtype
                        self.variables[vname]["time_index"] = time_index
                        # don't need _FillValue
                        for att in ["units", "long_name", "short_name"]:
                            if hasattr(var, att):
                                self.variables[
                                    vname][att] = getattr(var, att)
                            else:
                                self.variables[vname][att] = ""
                        continue

                    # variable has been found in an earlier ncfile
                    # check for consistancy across files
                    if self.variables[vname]["shape"][1:] != var.shape[1:]:
                        # the above check works even if either shape
                        # has length 1
                        if len(self.variables[vname]["shape"]) != \
                                len(var.shape):
                            # changing number of dimensions, punt
                            _logger.error(
                                "%s: %s: number of "
                                "dimensions: %d and %d changes. "
                                "Skipping this variable.",
                                ncpath, vname, len(var.shape),
                                len(self.variables[vname]["shape"]))
                            del self.variables[vname]
                            continue
                        # here we know that shapes have same length and
                        # they must have len > 1. Allow final dimension
                        # to change.
                        ndim = len(var.shape)
                        if (self.variables[vname]["shape"][1:(ndim-1)] !=
                                var.shape[1:(ndim-1)]):
                            _logger.error(
                                "%s: %s: incompatible shapes: "
                                "%s and %s. Skipping this variable.",
                                ncpath, vname, repr(var.shape),
                                repr(self.variables[vname]["shape"]))
                            del self.variables[vname]
                            continue
                        # set shape to max shape (leaving the problem
                        # for later...)
                        self.variables[vname]["shape"] = tuple(
                            [max(i, j) for (i, j) in zip(
                                self.variables[vname]["shape"], var.shape)])

                    if self.variables[vname]["dtype"] != var.dtype:
                        _logger.error(
                            "%s: %s: type=%s is different than "
                            "in other files",
                            ncpath, vname, repr(var.dtype))

                    if self.variables[vname]["time_index"] != time_index:
                        _logger.error(
                            "%s: %s: time_index=%d is different than "
                            "in other files. Skipping this variable.",
                            ncpath, vname, time_index)
                        del self.variables[vname]

            finally:
                ncfile.close()

        return self.variables

    def resolve_variable_shapes(self, variables, selectdim):
        """Determine the shape of variables in this dataset.

        Args:
            variables: List of variable names.
            selectdim: A dict containing by dimension name,
                the indices of the dimension to be read.
                For example: {"station":[3,4,5]} to read indices 3,4 and 5
                (indexed from 0) of the station dimension for variables
                which have that dimension. A index of -1 indicates that
                variables which don't have the dimension are still to be read.

        Returns:
            Dict of resultant variable shapes, which may be different
            than the non-time dimensions of the variable in a file if
            the user has specified selectdim to sub-select over a dimension.
        """
        vshapes = {}
        for vname in variables:
            if vname in self.variables:
                # maximum shape of this variable in all files

                vshape = list(self.variables[vname]["shape"])
                time_index = self.variables[vname]["time_index"]
                vdims = self.variables[vname]["dimnames"]

                dmatch = True
                for dim in selectdim:
                    # some dimensions selected
                    if not dim in vdims:
                        # This variable does not have the selected dimension
                        # If all selected indices for the dimension are >= 0
                        # then don't return any values for this variable.
                        # -1 for a selected dimension means return values
                        # for the variable even if it doesn't have the dimension
                        try:
                            if all(i >= 0 for i in selectdim[dim]):
                                dmatch = False
                        except TypeError:   # not iterable
                            if selectdim[dim] >= 0:
                                dmatch = False
                if not dmatch:
                    continue

                # determine selected shape for variable
                for idim, dim in enumerate(vdims):
                    if dim == self.time_dim:
                        pass
                    elif dim == "sample":
                        # high rate files with a sample dimension
                        # Add support for this eventually. For now
                        # just grab first value
                        vshape[idim] = 1
                    elif dim in selectdim:
                        # variable has a selected dimension
                        try:
                            if not all(i < 0 for i in selectdim[dim]):
                                idx = [i for i in selectdim[dim] if i >= 0]
                                vshape[idim] = len(idx)
                        except TypeError:   # not iterable
                            if selectdim[dim] >= 0:
                                vshape[idim] = 1

                # remove non-time shape values of 1
                vshape = [dim for (idim, dim) in enumerate(vshape) \
                        if idim != time_index or dim > 1]
                vshapes[vname] = vshape

        return vshapes

    def read_times(self, ncfile, ncpath, start_time, end_time, times,
                   size_limit):
        """Read values of the time variable from a NetCDF dataset.

        Args:
            ncfile: An opened netCFD4.Dataset.
            ncpath: Path to the dataset. netCDF4.Dataset.filepath() is only
                supported in netcdf version >= 4.1.2.
            start_time: A datetime.datetme. Times greater than or equal
                to start_time are read.
            end_time: A datetime.datetme. Times less than end_time are read.
            times: A list of datetime.datetimes, the times read are
                appended to this list.
            total_size: Add the total size of times read to this value.
            size_limit: Raise an exception if the total_size exceeds size_limit.

        Raises:
            exceptions.TooMuchDataException
        """

        base_time = None

        if self.base_time and \
                self.base_time in ncfile.variables and \
                len(ncfile.variables[self.base_time].dimensions) == 0:
            base_time = ncfile.variables[self.base_time].getValue()
            # print("base_time=",base_time)

        if self.time_name in ncfile.variables:
            var = ncfile.variables[self.time_name]

            if len(var) == 0:
                return slice(0)

            if hasattr(var, "units") and 'since' in var.units:
                try:
                    # pylint: disable=pointless-string-statement
                    """
                    tvals = [dim for dim in netCDF4.num2date(var[:],
                        var.units,'standard')]
                    if tvals[0].tzinfo == None or
                            tvals[0].tzinfo.utcoffset() == None:
                        print("tz[0] is naive")
                    """
                    # times from netCDF4.num2date are naive.

                    tvals = [
                        d.replace(tzinfo=pytz.UTC) for d in
                        netCDF4.num2date(
                            var[:], var.units,
                            'standard')]
                except IndexError as exc:
                    # most likely has a dimension of 0
                    _logger.error(
                        "%s: %s: cannot index variable %s",
                        os.path.split(ncpath)[1],
                        exc, self.time_name)
                    return slice(0)
                except TypeError:
                    if base_time:
                        _logger.error(
                            "%s: %s: cannot parse units: %s, "
                            "using base_time instead",
                            os.path.split(ncpath)[1],
                            self.time_name, var.units)
                        tvals = [
                            datetime.fromtimestamp(
                                base_time +
                                val, tz=pytz.utc) for val in var[:]]
                    else:
                        _logger.error(
                            "%s: %s: cannot parse units: %s",
                            os.path.split(ncpath)[1],
                            self.time_name, var.units)
                        tvals = [
                            datetime.fromtimestamp(val, tz=pytz.utc)
                            for val in var[:]]
            else:
                try:
                    tvals = [
                        datetime.fromtimestamp(
                            base_time + val,
                            tz=pytz.utc) for val in var[:]]
                except IndexError as exc:
                    # most likely has a dimension of 0
                    _logger.error(
                        "%s: %s: cannot index variable %s",
                        os.path.split(ncpath)[1],
                        exc, self.time_name)
                    return slice(0)

            # pylint: disable=pointless-string-statement
            """
            tvals = [
                d.timestamp() for d in
                netCDF4.num2date(var[:], var.units, 'standard')]
            """

            if len(tvals) == 0:
                return slice(0)

            istart = 0
            for istart, tval in enumerate(tvals):
                if tval >= start_time:
                    break

            iend = 0
            for iend, tval in enumerate(reversed(tvals)):
                if tval < end_time:
                    break
            iend = len(tvals) - iend

            if iend - istart <= 0:
                _logger.warning(
                    "%s: no times found, start_time=%s,"
                    "end_time=%s, file times=%s - %s",
                    os.path.split(ncpath)[1],
                    start_time.isoformat(), end_time.isoformat(),
                    tvals[0].isoformat(), tvals[-1].isoformat())
                return slice(0)
            else:
                _logger.debug(
                    "%s: tvals[%d]=%d ,"
                    "tvals[%d]=%d, "
                    "start_time=%s, end_time=%s",
                    os.path.split(ncpath)[1],
                    istart, tvals[istart].timestamp(),
                    iend, tvals[iend-1].timestamp(),
                    start_time, end_time)

            time_slice = slice(istart, iend, 1)

            tsize = (time_slice.stop - time_slice.start) * \
                    sys.getsizeof(tvals[0])
            if tsize > size_limit:
                raise exceptions.TooMuchDataException(
                    "too many time values requested, size={0} MB".\
                            format(tsize/(1000 * 1000)))

            times.extend(tvals[time_slice])
            return time_slice

    def read_time_series_data(
            self, ncfile, ncpath, vname, time_slice, vshape,
            selectdim, dim2):
        """ Read values of a time-series variable from a netCDF4 dataset.

        Args:
            ncfile: An opened netCFD4.Dataset.
            ncpath: Path to the dataset. netCDF4.Dataset.filepath() is only
                supported in netcdf version >= 4.1.2.
            vname: Name of variable to read.
            time_slice: The slice() of time indices to read.
            vshape: Shape of the variable in case it isn't in the file
                an a filled array should be returned.
            selectdim: A dict containing for each dimension name of type
                string, the indices of the dimension to read.
                For example: {"station":[3,4,5]} to read indices 3,4 and 5
                (indexed from 0) of the station dimension for variables
                which have that dimension.
            dim2: Values for second dimension of the variable, such as height.

        Returns:
            A np.ma.array containing the data read.
        """

        # which dimension is time?
        time_index = self.variables[vname]["time_index"]

        vdtype = self.variables[vname]["dtype"]

        if vname in ncfile.variables:

            var = ncfile.variables[vname]

            # indices of variable to be read
            idx = ()
            for idim, dim in enumerate(var.dimensions):
                if dim == self.time_dim:
                    idx += (time_slice,)
                elif dim == "sample":
                    # high rate files with a sample dimension
                    # Add support for this eventually. For now
                    # just grab first value
                    idx += (0,)
                elif dim in selectdim:
                    # variable has a selected dimension
                    try:
                        if all(i < 0 for i in selectdim[dim]):
                            sized = len(ncfile.dimensions[dim])
                            idx += (slice(0, sized), )
                        else:
                            idx += \
                                (tuple([i for i in selectdim[dim] if i >= 0]),)
                    except TypeError:   # not iterable
                        if selectdim[dim] >= 0:
                            idx = (selectdim[dim],)
                        else:
                            sized = len(ncfile.dimensions[dim])
                            idx += (slice(0, sized), )
                else:
                    sized = len(ncfile.dimensions[dim])
                    idx += (slice(0, sized), )
                    if not dim2:
                        # self.variables[vname]['shape'][idim] will
                        # be the largest value for this dimension
                        # in the set of files.
                        sized = self.variables[vname]['shape'][idim]
                        dim2['data'] = [i for i in range(sized)]
                        dim2['name'] = dim
                        dim2['units'] = ''

            if time_slice.stop - time_slice.start > 0:
                _logger.debug(
                    "%s: %s: time_slice.start,"
                    "time_slice.stop=%d,%d, idx[1:]=%s",
                    os.path.split(ncpath)[1], vname,
                    time_slice.start, time_slice.stop,
                    repr(idx[1:]))

            # extract the data from var
            vdata = var[idx]
            fill_val = (
                0 if vdata.dtype.kind == 'i' or
                vdata.dtype.kind == 'u' else float('nan'))

            if isinstance(vdata, np.ma.core.MaskedArray):
                vdata = vdata.filled(fill_value=fill_val)

            if vdata.dtype != vdtype:
                vdata = np.ndarray.astype(vdtype)

            if len(vshape) > 0 and tuple(vshape[1:]) != vdata.shape[1:]:
                print("vshape[1:]={0}, vdata.shape[1:]={1}".format(
                    vshape[1:], vdata.shape[1:]))
                # changing shape. Add support for final dimension
                # increasing. vshape should be the largest expected shape
                shape = list(vdata.shape)
                # how much to grow it by
                shape[-1] = vshape[-1] - vdata.shape[-1]
                vdata = np.append(
                    vdata, np.ma.array(
                        data=np.empty(
                            shape=shape, dtype=vdata.dtype),
                        mask=True, fill_value=fill_val).filled(),
                    axis=-1)

        else:
            # variable is not in file, create NaN filled array
            # Determine shape of variable. Change the first, time dimension
            # to match the selected period.  The remaininng dimension
            # in self.variables[vname]['shape'] is the largest of those
            # seen in the selected files.
            shape = vshape
            shape[time_index] = time_slice.stop - time_slice.start
            shape = tuple(shape)

            vdtype = self.variables[vname]["dtype"]
            fill_val = (
                0 if vdtype.kind == 'i' or
                vdtype.kind == 'u' else float('nan'))

            vdata = np.ma.array(
                data=np.empty(
                    shape=shape, dtype=vdtype),
                mask=True, fill_value=fill_val).filled()

        return vdata

    def read_time_series(
            self,
            variables=(),
            start_time=datetime.min,
            end_time=datetime.max,
            selectdim=None,
            size_limit=1000 * 1000 * 1000):
        """ Read a list of time-series variables from this fileset.

        Args:
            variables: A list of strs containing time series variable
                names to be read.
            start_time: A datetime, which is timezone aware, of the start
                time of the series to read.
            end_time: A datetime, timezone aware, end time of series to read.
            selectdim: A dict containing for each dimension name of type
                string, the indices of the dimension to read.
                For example: {"station":[3,4,5]} to read indices 3,4 and 5
                (indexed from 0) of the station dimension for variables
                which have that dimension.
            size_limit: Limit on the total size in bytes to read, used to
                screen huge requests.

        Returns:
            A dict containing: {
                'time' : list of datetime.datetime objects, which are aware
                    of time zone and DST,
                'data': dict, by variable name of numpy.ndarray containing
                    the data for each variable,
                'dim2': values for second dimension of the data, such as height,
            }.

        """

        if not self.time_name:
            self.get_variables(start_time, end_time)

        if not selectdim:
            selectdim = {}

        vshapes = self.resolve_variable_shapes(variables, selectdim)

        datadict = {}
        times = []
        dim2 = {}
        total_size = 0

        filepaths = self.get_filepaths(start_time, end_time)

        for ncpath in filepaths:
            # _logger.debug("ncpath=%s",ncpath)

            # the files might be in the process of being moved, deleted, etc
            fileok = False
            for itry in range(0, 3):
                try:
                    ncfile = netCDF4.Dataset(ncpath)
                    fileok = True
                    break
                except IOError as exc:
                    _logger.error("%s: %s", ncpath, exc)
                    time.sleep(itry)
                except RuntimeError as exc:
                    _logger.error("%s: %s", ncpath, exc)
                    time.sleep(itry)

            if not fileok:
                continue

            try:
                time_slice = self.read_times(
                    ncfile, ncpath, start_time, end_time, times,
                    size_limit - total_size)

                if len(times) > 0:
                    total_size += (time_slice.stop - time_slice.start) * \
                        sys.getsizeof(times[0])

                for vname in variables:

                    # skip if variable is not a time series or
                    # doesn't have a selected dimension
                    if not vname in self.variables or not vname in vshapes:
                        continue

                    # selected shape of this variable
                    vshape = vshapes[vname]
                    total_size += reduce_(
                        operator.mul, vshape, 1) * \
                        self.variables[vname]["dtype"].itemsize

                    if total_size > size_limit:
                        raise exceptions.TooMuchDataException(
                            "too much data requested, will exceed {} mbytes".
                            format(size_limit/(1000 * 1000)))

                    vdata = self.read_time_series_data(
                        ncfile, ncpath, vname, time_slice, vshape,
                        selectdim, dim2)

                    if not vname in datadict:
                        datadict[vname] = vdata
                    else:
                        _logger.debug(
                            "datadict[vname].shape=%s, vdata.shape=%s",
                                datadict[vname].shape, vdata.shape)
                        time_index = self.variables[vname]["time_index"]
                        datadict[vname] = np.append(
                            datadict[vname], vdata, axis=time_index)

            finally:
                ncfile.close()

        if len(times) == 0:
            exc = exceptions.NoDataException(
                "no data found between {} and {}".
                format(start_time.isoformat(), end_time.isoformat()))
            _logger.warning(repr(exc))
            raise exc

        for vname in datadict.keys():
            _logger.debug(
                "datadict[%s].shape=%s",
                vname, repr(datadict[vname].shape))
        _logger.debug(
            "total_size=%d", total_size)

        return {"time" : times, "data": datadict, "dim2": dim2}

