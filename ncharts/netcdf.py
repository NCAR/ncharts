# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Support for reading meta-data and data NetCDF files, primarily
time-series data.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

import os
import sys
import time
from datetime import datetime
import logging
import threading
import operator
import hashlib
import re

from functools import reduce as reduce_

import numpy as np
import netCDF4
import pytz

from ncharts import exceptions as nc_exc
from ncharts import fileset as nc_fileset

# regular expression for extracting a site name from an ISFS variable
_SITE_RE_PROG = re.compile("(\\.[0-9]+\\.?[0-9]*(c?m))?(\\.([^.]+))$")

# for ISFS variables with no short_name attribute, such as a count
# variable. The periods will be replaced by underscores
# _SITE_RE_PROG2 = re.compile("(_[0-9]+_?[0-9]*(c?m))?(_([^_]+))$")

# __name__ is ncharts.netcdf
_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

STATION_DIMENSION_NAME = "station"

def get_file_modtime(path):
    """ Utility to get the modification time of a file. """
    try:
        pstat = os.stat(path)
    except OSError as exc:
        _logger.error(exc)
        raise

    return datetime.fromtimestamp(
        pstat.st_mtime, tz=pytz.utc)

def get_isfs_site(varname):
    """Use regular expression to extract a site name from an ISFS variable name.

    The basic format of an ISFS variable name is
        var[.sensor][.height][.site]
    var: string, with no periods
    sensor: string, with no periods
    height: numeric field with optional decimal point, followed by 'm' or 'cm'
    site: string, with no periods

    Examples:
        'T': site name is ''
        'T.25m.tower': site name is 'tower'
        'T.25m': site name is ''
        'T.acme.25m.tower': site name is 'tower'
        'T.acme.tower': site name is 'tower'
        'T.tower': site name is 'tower' (note the possible confusion with sensor name)
        'T.acme': site name is 'acme' (note the possible confusion with sensor name)
    """

    match = _SITE_RE_PROG.search(varname)
    # if not match:
    #     match = _SITE_RE_PROG2.search(varname)
    if match:
        try:
            # print("site for {}={}".format(varname,match.group(4)))
            return match.group(4) if match.group(4) else ''
        except IndexError:
            pass
    return ''

class NetCDFDataset(object):
    """A dataset consisting of NetCDF files, within a period of time.

    This is similar to netCDF4.MFDataset, but gets around some of its
    limitations.

    Supports reading a list of time-series variables from a
    collection of files concatenating the results over the
    time-dimension of the variables. If a variable is missing in
    a file, the values for those times will be NaN filled.

    Also handles other situations that may arise, such as if the
    non-time dimensions for a variable change from file to file, in
    which case the result will have the largest non-time dimensions,
    with the extra values filled in.

    Also attempts to handle the situation when the type of a variable
    is not consistant over the collection of files.

    Attributes:
        path: directory path and file name format
        fileset: The nc_fileset.FileSet encapsulating a set of files.
        start_time: start time of the dataset
        end_time: end time of the dataset
        cache_hash: a hash string, created from the path, start_time
            and end_time. The cache of NetCDF attributes is
            stored in the class under this hash code.

    These attributes of NetCDFDataset are cached:
        variables: Dict of dicts for all time-series variables found in
            dataset by their "exported" variable name:
                { 'shape': tuple of integer dimensions of the variable,
                  'dimnames': tuple of str dimension names for variable,
                  'units': str value of "units" attribute if found,
                  'long_name': str value of "long_name" attribute if found,
                  'dtype': numpy.dtype of the variable
                  'site': site suffix of a non-station variable
               }.
        base_time: str name of base_time variable if found in the dataset.
        time_dim:  str name of the time dimension in this dataset.
        time_name: str name of time variable.
        nstations: int length of NetCDF "station" dimension in this dataset,
            if found.
        station_dim:  str name of NetCDF "station" dimension, currently always
            "station".
        station_names: If a NetCDF character variable called "station"
            is found, and one or more variables have a station dimension,
            a list of str values of the variable.
        has_station_variables: if any variable has a station dimension
        sites: dictionary of site long_name names by the site short names
            for every site short name found in variable names
            without a station dimension
    """
    # pylint thinks this class is too big.
    # pylint: disable=too-many-instance-attributes

    MAX_NUM_FILES_TO_PRESCAN = 50

    __cache_lock = threading.Lock()

    # dictionary of attributes of a NetCDFDataset.
    __cached_dataset_info = {}

    def __init__(self, path, start_time, end_time):
        """Constructs NetCDFDataset with a path to a filesetFileset.

        Raises:
            none
        """
        self.path = path
        self.fileset = nc_fileset.Fileset.get(path)
        self.start_time = start_time
        self.end_time = end_time

        hasher = hashlib.md5()
        hasher.update(bytes(path, 'utf-8'))
        hasher.update(bytes(str(start_time), 'utf-8'))
        hasher.update(bytes(str(end_time), 'utf-8'))

        self.cache_hash = hasher.digest()

    def get_dataset_info(self):
        """Fetch a copy of the cache of info for this dataset.
        """
        with NetCDFDataset.__cache_lock:
            if self.cache_hash in NetCDFDataset.__cached_dataset_info:
                return NetCDFDataset.__cached_dataset_info[self.cache_hash].copy()
        dsinfo = {
            'file_mod_times': {},
            'base_time': None,
            'time_dim_name': None,
            'time_name': None,
            'nstations': None,
            'station_dim': None,
            'station_names': None,
            'has_station_variables': False,
            'sites': {},
            'variables': {},
        }
        return dsinfo

    def save_dataset_info(self, dsinfo):
        """Save a the info for this dataset.
        """
        with NetCDFDataset.__cache_lock:
            NetCDFDataset.__cached_dataset_info[self.cache_hash] = dsinfo

    def __str__(self):
        return "NetCDFDataset, path=" + str(self.path)

    def get_files(
            self,
            start_time=pytz.utc.localize(datetime.min),
            end_time=pytz.utc.localize(datetime.max)):
        """Return the fileset.File objects matching a time period.

        Args:
            start_time: datetime.datetime of start of fileset scan.
            end_time: end of fileset scan.

        Returns:
            List of file path names matching the time period.

        Raises:
            OSError
        """
        return self.fileset.scan(start_time, end_time)

    def get_filepaths(
            self,
            start_time=pytz.utc.localize(datetime.min),
            end_time=pytz.utc.localize(datetime.max)):
        """Return the file path names matching the time period.
        Args:
            start_time: datetime.datetime of start of fileset scan.
            end_time: end of fileset scan.

        Returns:
            List of file path names matching the time period.

        Raises:
            OSError
        """
        return [f.path for f in self.get_files(start_time, end_time)]

    def scan_files(
            self,
            time_names=('time', 'Time', 'time_offset')):
        """ Scan the set of files, accumulating information about the dataset in a dict,
        with the following keys:
            file_mod_times: dictionary of file modification times by file name, of each
                file just before it was last scanned.
            base_time: name of base_time variable
            time_dim_name: name of time dimension
            time_name: name of time variable
            nstations: size of the station dimension
            station_dim: name of the station dimension
            station_names: names of the stations
            sites: dictionary of names of sites long names by the site short
                names extracted from the exported names
                of those variables not associated with a numbered station
            variables: dictionary of information for each variable.

        If an element in file_mod_times exists for a file, that file is not scanned if
        its current modification time has not been updated.

        The names of the variables in the dataset are converted to an exported
        form. If a variable has a 'short_name' attribute, it is used for the
        variable name, otherwise the exported name is set to the NetCDF variable
        name.

        Note, we don't read every file.  May want to have
        MAX_NUM_FILES_TO_PRESCAN be an attribute of the dataset.

        Args:
            time_names: List of allowed names for time variable.

        Raises:
            OSError
            nc_exc.NoDataException
        """

        dsinfo = self.get_dataset_info()

        # Note: dsinfo_vars is a reference. Modificatons to it
        # are also modifications to dsinfo.
        dsinfo_vars = dsinfo['variables']

        sitedict = dsinfo['sites']

        files = self.get_files(
            start_time=self.start_time,
            end_time=self.end_time)

        # typically get_files() also returns the file before start_time
        # We may want that in reading a period of data, but not
        # in assembling the variables for the dataset
        filepaths = [f.path for f in files if f.time >= self.start_time and f.time < self.end_time]

        skip = 1
        if len(filepaths) > NetCDFDataset.MAX_NUM_FILES_TO_PRESCAN:
            skip = len(filepaths) / NetCDFDataset.MAX_NUM_FILES_TO_PRESCAN

        # Read at most MAX_NUM_FILES_TO_PRESCAN, including latest file.
        # Files are scanned in a backwards sequence
        pindex = len(filepaths) - 1

        n_files_read = 0

        while pindex >= 0:
            ncpath = filepaths[int(pindex)]
            pindex -= skip

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
            skip_file = False
            exc = None

            siteset = set()
            site_sn = []
            site_ln = []

            for itry in range(0, 3):
                try:
                    curr_mod_time = get_file_modtime(ncpath)
                    if ncpath in dsinfo['file_mod_times']:
                        prev_mod_time = dsinfo['file_mod_times'][ncpath]
                        if curr_mod_time <= prev_mod_time:
                            skip_file = True
                            fileok = True
                            break
                    dsinfo['file_mod_times'][ncpath] = curr_mod_time
                    # _logger.debug("ncpath=%s",ncpath)
                    ncfile = netCDF4.Dataset(ncpath)
                    fileok = True
                    break
                except (OSError, RuntimeError) as excx:
                    exc = excx
                    time.sleep(itry)

            if not fileok:
                _logger.error("%s: %s", ncpath, exc)
                continue

            n_files_read += 1

            if skip_file:
                continue

            try:
                if not dsinfo['base_time'] and 'base_time' in ncfile.variables:
                    dsinfo['base_time'] = 'base_time'

                tdim = None
                # look for a time dimension
                for tname in ['time', 'Time']:
                    if tname in ncfile.dimensions:
                        tdim = ncfile.dimensions[tname]
                        break
                if not tdim:
                    continue

                # check for tdim.is_unlimited?
                if not dsinfo['time_dim_name']:
                    dsinfo['time_dim_name'] = tdim.name

                if STATION_DIMENSION_NAME in ncfile.dimensions:
                    if dsinfo['nstations'] is None:
                        dsinfo['nstations'] = len(ncfile.dimensions[STATION_DIMENSION_NAME])
                        dsinfo['station_dim'] = STATION_DIMENSION_NAME
                        if STATION_DIMENSION_NAME in ncfile.variables:
                            dsinfo['station_names'] = []
                            var = ncfile.variables[STATION_DIMENSION_NAME]
                            if var.datatype == np.dtype('S1'):

                                snms = [str(netCDF4.chartostring(v)) for v in var]
                                dsinfo['station_names'].extend(snms)
                    elif not dsinfo['nstations'] == \
                            len(ncfile.dimensions[STATION_DIMENSION_NAME]):
                        _logger.warning(
                            "%s: station dimension (%d) is "
                            "different than that of other files (%d)",
                            ncpath,
                            len(ncfile.dimensions[STATION_DIMENSION_NAME]),
                            dsinfo['nstations'])


                # look for a time variable
                if not dsinfo['time_name']:
                    for tname in time_names:
                        if tname in ncfile.variables:
                            if tdim.name in ncfile.variables[tname].dimensions:
                                dsinfo['time_name'] = tname
                                break

                if not dsinfo['time_name'] or \
                    not dsinfo['time_name'] in ncfile.variables:
                    # time variable not yet found or not in this file
                    continue

                if not tdim.name in ncfile.variables[dsinfo['time_name']].dimensions:
                    # time variable in this file doesn't have a time dimension
                    continue

                # pylint: disable=no-member
                for (nc_vname, var) in ncfile.variables.items():

                    if nc_vname == "site_long_name" and \
                        var.datatype == np.dtype('S1'):
                        site_ln = [str(netCDF4.chartostring(v)) for v in var]

                    if nc_vname == "sites" and \
                        var.datatype == np.dtype('S1'):
                        site_sn = [str(netCDF4.chartostring(v)) for v in var]

                    # looking for time series variables
                    if not dsinfo['time_dim_name'] in var.dimensions:
                        continue

                    # time variable
                    if nc_vname == dsinfo['time_name']:
                        continue

                    # exported variable name
                    if hasattr(var, 'short_name'):
                        exp_vname = getattr(var, 'short_name')
                    else:
                        exp_vname = nc_vname

                    # var.dimensions is a tuple of dimension names
                    time_index = var.dimensions.index(dsinfo['time_dim_name'])

                    # Check if we have found this variable in a earlier file
                    if not exp_vname in dsinfo_vars:

                        # New variable
                        varinfo = {}
                        varinfo['netcdf_name'] = nc_vname
                        varinfo['shape'] = var.shape
                        varinfo['dimnames'] = var.dimensions
                        varinfo['dtype'] = var.dtype
                        varinfo['time_index'] = time_index

                        # Grab certain attributes
                        for att in ['units', 'long_name']:
                            if hasattr(var, att):
                                varinfo[att] = getattr(var, att)

                        # Set default units to ''
                        if 'units' not in varinfo:
                            varinfo['units'] = ''

                        # For non-station variables, parse the name to
                        # determine the possible site
                        if not dsinfo['station_dim'] or \
                            not dsinfo['station_dim'] in var.dimensions:
                            site = get_isfs_site(exp_vname)
                            if site:
                                varinfo['site'] = site
                                siteset.add(site)
                                # dsinfo['sites'].add(site)
                        else:
                            dsinfo['has_station_variables'] = True

                        dsinfo_vars[exp_vname] = varinfo
                        continue

                    varinfo = dsinfo_vars[exp_vname]

                    # variable has been found in an earlier ncfile
                    # check for consistancy across files
                    if varinfo['shape'][1:] != var.shape[1:]:
                        # the above check works even if either shape
                        # has length 1
                        if len(varinfo['shape']) != \
                                len(var.shape):
                            # changing number of dimensions, punt
                            _logger.error(
                                "%s: %s: number of "
                                "dimensions is not consistent: %d and %d. "
                                "Skipping this variable.",
                                ncpath, nc_vname, len(var.shape),
                                len(varinfo['shape']))
                            del dsinfo_vars[exp_vname]
                            continue
                        # here we know that shapes have same length and
                        # they must have len > 1. Allow final dimension
                        # to change.
                        ndim = len(var.shape)
                        if (varinfo['shape'][1:(ndim-1)] !=
                                var.shape[1:(ndim-1)]):
                            _logger.error(
                                "%s: %s: incompatible shapes: "
                                "%s and %s. Skipping this variable.",
                                ncpath, nc_vname, repr(var.shape),
                                repr(varinfo['shape']))
                            del dsinfo_vars[exp_vname]
                            continue
                        # set shape to max shape (leaving the problem
                        # for later...)
                        varinfo['shape'] = tuple(
                            [max(i, j) for (i, j) in zip(
                                varinfo['shape'], var.shape)])

                    if varinfo['dtype'] != var.dtype:
                        _logger.error(
                            "%s: %s: type=%s is different than "
                            "in other files",
                            ncpath, nc_vname, repr(var.dtype))

                    if varinfo['time_index'] != time_index:
                        _logger.error(
                            "%s: %s: time_index=%d is different than "
                            "in other files. Skipping this variable.",
                            ncpath, nc_vname, time_index)
                        del dsinfo_vars[exp_vname]

                    for att in ['units', 'long_name']:
                        if hasattr(var, att) and att in varinfo:
                            if getattr(var, att) != varinfo[att]:
                                _logger.info(
                                    "%s: %s: %s=%s is different than previous value=%s",
                                    ncpath, nc_vname, att, getattr(var, att),
                                    varinfo[att])
                                varinfo[att] = getattr(var, att)

            finally:
                for site in siteset:
                    try:
                        i = site_sn.index(site)
                        if i < len(site_ln):
                            sitedict[site] = site_ln[i]
                    except ValueError:
                        pass

                    if site not in sitedict:
                        sitedict[site] = ''
                ncfile.close()

        if not n_files_read:
            msg = "No variables found"
            raise nc_exc.NoDataException(msg)

        # Remove the station names if no variables have a station dimension
        if not dsinfo['has_station_variables']:
            dsinfo['station_names'] = []
        else:
            # create station names if a "station" variable is not found
            # in NetCDF files. Names are S1, S2, etc for dimension index 0, 1
            if dsinfo['nstations'] and not dsinfo['station_names']:
                dsinfo['station_names'].extend(\
                    ['S{}'.format(i+1) for i in range(dsinfo['nstations'])])

        # cache dsinfo
        self.save_dataset_info(dsinfo)

    def get_variables(self, time_names=('time', 'Time', 'time_offset')):
        """Get the time series variables in a dataset.

        Returns:
            A dict of variables, keyed by the exported variable name.
            Each value is a dict, containing the following keys:
                shape: tuple containing the shape of the variable
                netcdf_name: name of variable in NetCDF file
                dimnames: list of dimension names
                dtype: NetCDF data type
                time_index: index of the time dimension
                units: units attribute of the NetCDF variable
                long_name: long_name attribute of the NetCDF variable
                site(optional): site name, possibly an empty string,
                    if a variable does not have a station dimension
        Raises:
            OSError
            nc_exc.NoDataException
        """

        # scan the dataset every time in case a file has been modified
        self.scan_files(time_names=time_names)
        dsinfo = self.get_dataset_info()
        return dsinfo['variables'].copy()

    def get_station_names(
            self):

        """ return the station names of this dataset.

        Args:

        Returns:
            A list of names, for stations 1:N.
        Raises:
            OSError
            nc_exc.NoDataException
        """

        dsinfo = self.get_dataset_info()
        if not dsinfo['variables']:
            self.scan_files()
            dsinfo = self.get_dataset_info()

        return dsinfo['station_names'].copy()

    def get_sites(
            self):

        """ return the site names of this dataset.

        Args:

        Returns:
            A dictionary of site long_names, indexed by the site short names
        Raises:
            OSError
            nc_exc.NoDataException
        """

        dsinfo = self.get_dataset_info()
        if not dsinfo['variables']:
            self.scan_files()
            dsinfo = self.get_dataset_info()

        return dsinfo['sites'].copy()

    def resolve_variable_shapes(self, variables, selectdim):
        """Determine the shape of variables in this dataset.

        Args:
            variables: List of variable names.
            selectdim: A dict containing by dimension name,
                the indices of the dimension to be read, for
                variables with that dimension.
                For example: {"station":[3,4,5]} to read indices 3,4 and 5
                (indexed from 0) of the station dimension for variables
                which have that dimension.

        Returns:
            Dict of resultant variable shapes, which may be different
            than the non-time dimensions of the variable in a file if
            the user has specified selectdim to sub-select over a dimension.
        """
        dsinfo = self.get_dataset_info()
        if len(dsinfo['variables']) == 0:
            self.scan_files()
            dsinfo = self.get_dataset_info()

        dsinfo_vars = dsinfo['variables']

        vshapes = {}
        for exp_vname in variables:
            if exp_vname in dsinfo_vars:
                # maximum shape of this variable in all files

                vshape = list(dsinfo_vars[exp_vname]["shape"])
                time_index = dsinfo_vars[exp_vname]["time_index"]
                vdims = dsinfo_vars[exp_vname]["dimnames"]

                # determine selected shape for variable
                for idim, dim in enumerate(vdims):
                    if dim == dsinfo['time_dim_name']:
                        pass
                    elif dim == "sample":
                        # high rate files with a sample dimension
                        # Add support for this eventually. For now
                        # just grab first value
                        vshape[idim] = 1
                    elif dim in selectdim:
                        # variable has a selected dimension
                        # if len(selectdim[dim]) == 0:
                        #     continue
                        idx = [i for i in selectdim[dim]]
                        vshape[idim] = len(idx)

                # remove non-time shape values of 1
                vshape = [dim for (idim, dim) in enumerate(vshape) \
                        if idim != time_index or dim > 1]
                vshapes[exp_vname] = vshape

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
            times: A list of UTC timestamps, the times read are
                appended to this list.
            size_limit: Raise an exception if size exceeds this value

        Returns:
            A built-in slice object, giving the start and stop indices of the
            requested time period in the file. The times list argument is
            also extended with the times read from the file.

        Raises:
            TODO: what exceptions can be raised when slicing a netcdf4 variable?
            nc_exc.TooMuchDataException
        """

        debug = False

        dsinfo = self.get_dataset_info()

        base_time = None

        if dsinfo['base_time'] and \
                dsinfo['base_time'] in ncfile.variables and \
                len(ncfile.variables[dsinfo['base_time']].dimensions) == 0:
            base_time = ncfile.variables[dsinfo['base_time']].getValue()
            # _logger.debug("base_time=%d",base_time)

        if dsinfo['time_name'] in ncfile.variables:
            var = ncfile.variables[dsinfo['time_name']]

            if len(var) == 0:
                return slice(0)

            if hasattr(var, "units") and 'since' in var.units:
                try:
                    # times from netCDF4.num2date are timezone naive.
                    # Use replace(tzinfo=pytz.UTC) to assign a timezone.
                    tvals = [
                        d.replace(tzinfo=pytz.UTC).timestamp() for d in
                        netCDF4.num2date(var[:], var.units, 'standard')]

                except IndexError as exc:
                    # most likely has a dimension of 0
                    _logger.error(
                        "%s: %s: %s %s",
                        ncpath, dsinfo['time_name'], type(exc).__name__,
                        exc)
                    return slice(0)
                except TypeError as exc:
                    if base_time:
                        _logger.warning(
                            "%s: %s: %s %s, units=%s "
                            "Using base_time instead",
                            ncpath, dsinfo['time_name'], type(exc).__name__,
                            exc, var.units)
                        tvals = [base_time + val for val in var[:]]
                    else:
                        _logger.error(
                            "%s: %s: %s %s, units=%s",
                            ncpath, dsinfo['time_name'], type(exc).__name__,
                            exc, var.units)
                        tvals = [val for val in var[:]]
                except (ValueError, OverflowError) as exc:
                    # saw this error happen once, perhaps
                    # on a file that was being updated.
                    # Give up rather than trying to salvage with:
                    #   tvals = [base_time + val for val in var[:]]
                    _logger.error(
                            "%s: %s: %s %s",
                        ncpath, dsinfo['time_name'], type(exc).__name__, exc)
                    return slice(0)
            else:
                try:
                    tvals = [base_time + val for val in var[:]]
                except IndexError as exc:
                    # most likely has a dimension of 0
                    _logger.error(
                        "%s: %s: cannot index variable %s",
                        ncpath, exc, dsinfo['time_name'])
                    return slice(0)

            # pylint: disable=pointless-string-statement
            """
            tvals = [
                d.timestamp() for d in
                netCDF4.num2date(var[:], var.units, 'standard')]
            """

            if len(tvals) == 0:
                return slice(0)

            try:
                istart = next(idx for idx, tval in enumerate(tvals) \
                        if tval >= start_time.timestamp())
                # _logger.debug("start_time=%s, file=%s,istart=%d",
                #         start_time,ncpath,istart)
                iend = next(idx for idx, tval in enumerate(reversed(tvals)) \
                        if tval < end_time.timestamp())
                iend = len(tvals) - iend
                # _logger.debug("end_time=%s, file=%s,iend=%d",
                #         end_time,ncpath,iend)
            except StopIteration:
                return slice(0)

            if iend - istart == 0:
                return slice(0)
            elif iend - istart < 0:
                _logger.warning(
                    "%s: times in file are not ordered, start_time=%s,"
                    "end_time=%s, file times=%s - %s, istart=%d, iend=%d",
                    ncpath, start_time.isoformat(), end_time.isoformat(),
                    datetime.fromtimestamp(tvals[0], tz=pytz.utc).isoformat(),
                    datetime.fromtimestamp(tvals[-1], tz=pytz.utc).isoformat(),
                    istart, iend)
                return slice(0)
            elif debug:
                _logger.debug(
                    "%s: tvals[%d]=%s, tvals[%d]=%s, "
                    "start_time=%s, end_time=%s",
                    ncpath, istart,
                    datetime.fromtimestamp(
                        tvals[istart], tz=pytz.utc).isoformat(),
                    iend,
                    datetime.fromtimestamp(
                        tvals[iend-1], tz=pytz.utc).isoformat(),
                    start_time.isoformat(),
                    end_time.isoformat())

            time_slice = slice(istart, iend, 1)
            tvals = tvals[time_slice]

            tsize = sys.getsizeof(tvals)
            if tsize > size_limit:
                raise nc_exc.TooMuchDataException(
                    "too many time values requested, size={0} MB".\
                            format(tsize/(1000 * 1000)))

            times.extend(tvals)
            return time_slice

    def read_time_series_data(
            self, ncfile, ncpath, exp_vname, time_slice, vshape,
            selectdim, dim2, stnnames):
        """ Read values of a time-series variable from a netCDF4 dataset.

        Args:
            ncfile: An opened netCFD4.Dataset.
            ncpath: Path to the dataset. netCDF4.Dataset.filepath() is only
                supported in netcdf version >= 4.1.2.
            exp_vname: Exported name of variable to read.
            time_slice: The slice() of time indices to read.
            vshape: Shape of the variable, which is used to create a
                filled array of missing values if the variable is not
                found in the file.
            selectdim: A dict containing for each dimension name of type
                string, the indices of the dimension to read.
                For example: {"station":[3,4,5]} to read indices 3,4 and 5
                (indexed from 0) of the station dimension for variables
                which have that dimension.
            dim2: Values for second dimension of the variable, such as height.
                Returned.
            stnnames: A list of the station names of the variable. Returned.
                A list of length one containing an empty string indicates
                the variable does not have a station dimension.

        Returns:
            A numpy.ma.array containing the data read.
        """

        dsinfo = self.get_dataset_info()
        dsinfo_vars = dsinfo['variables']

        debug = False

        # which dimension is time?
        time_index = dsinfo_vars[exp_vname]["time_index"]

        vdtype = dsinfo_vars[exp_vname]["dtype"]

        nc_vname = dsinfo_vars[exp_vname]['netcdf_name']

        if nc_vname in ncfile.variables:

            var = ncfile.variables[nc_vname]

            skip = False

            # indices of variable to be read
            idx = ()
            stnnums = []   # station numbers
            for idim, dim in enumerate(var.dimensions):
                if dim == dsinfo['time_dim_name']:
                    idx += (time_slice,)
                elif dim == "sample":
                    # high rate files with a sample dimension
                    # Add support for this eventually. For now
                    # just grab first value
                    idx += (0,)
                elif dim in selectdim:
                    # variable has a selected dimension
                    mdim = tuple(i for i in selectdim[dim])
                    # print("mdim=%s" % (str(mdim)))
                    if len(mdim) == 0:
                        skip = True
                        continue
                    idx += (tuple(mdim),)
                    if dim == STATION_DIMENSION_NAME:
                        stnnums = [i for i in mdim]
                else:
                    sized = len(ncfile.dimensions[dim])
                    idx += (slice(0, sized), )
                    if dim == STATION_DIMENSION_NAME:
                        stnnums = [i for i in range(0, sized)]
                    elif not dim2:
                        # dsinfo_vars[exp_vname]['shape'][idim] will
                        # be the largest value for this dimension
                        # in the set of files.
                        sized = dsinfo_vars[exp_vname]['shape'][idim]
                        dim2['data'] = [i for i in range(sized)]
                        dim2['name'] = dim
                        dim2['units'] = ''

            if skip:
                # print("skipping %s" % (nc_vname))
                return None

            if debug and time_slice.stop - time_slice.start > 0:
                _logger.debug(
                    "%s: %s: time_slice.start,"
                    "time_slice.stop=%d,%d, idx[1:]=%s",
                    ncpath, nc_vname,
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
                # _logger.debug("vshape[1:]=%d, vdata.shape[1:]=%d",
                #     vshape[1:], vdata.shape[1:])
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

            if not stnnums:
                stnnames.append('')
            else:
                dsinfo_stns = dsinfo['station_names']
                stnnames.extend([dsinfo_stns[i] for i in stnnums])

        else:
            # variable is not in file, create NaN filled array
            # Determine shape of variable. Change the first, time dimension
            # to match the selected period.  The remaining dimension
            # in dsinfo_vars[exp_vname]['shape'] is the largest of those
            # seen in the selected files.
            shape = list(vshape)
            shape[time_index] = time_slice.stop - time_slice.start

            vdtype = dsinfo_vars[exp_vname]["dtype"]
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
            start_time=pytz.utc.localize(datetime.min),
            end_time=pytz.utc.localize(datetime.max),
            selectdim=None,
            size_limit=1000 * 1000 * 1000,
            series=None,
            series_name_fmt=None):
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
            series: A list of series to be read by name. For soundings
                a series name is something like "Aug23_0000Z", as
                created by series_fmt from the time associated with
                a file.  In this way the data read can be split into
                named series.  If series_fmt is None, the series name
                should be a list of one empty string, [''],
                and all data are concatenated together in time order.
            series_fmt: a datetime.strftime format to create a
                series name for the data found in each file, based
                on the time associated with the file.
                If series_name_fmt is None, all data is put in a dictionary
                element named ''.

        Returns:
            A dict containing, by series name:
                'time' : list of UTC timestamps,
                'data': list of numpy.ndarray containing the data for
                    each variable,
                'vmap': dict by variable name,
                    containing the index into the series data for the variable,
                'dim2': dict by variable name, of values for second dimension
                    of the data, such as height,
                'stnnames': dict by variable name, of the list of the
                    station names for the variable that were read,
                    as selected by selectdim. A list of length 1 containing
                    an empty string indicates the variable does not have
                    a station dimension.

        Raises:
            OSError
            nc_exc.NoDataException

        The 'data' element in the returned dict is a list of numpy arrays,
        and not a dict by variable name. The 'vmap' element provides the
        mapping from a variable name to an index into 'data'. The data object
        is typically JSON-ified and sent to a browser. If it were a dict,
        the variable names may contain characters which cause headaches with
        JSON and javascript in django templates. For example, the JSON-ified
        string is typically passed to javascript in a django template by
        surrounding it with single quotes:
            var data = jQuery.parseJSON('{{ data }}');
        A single quote within the data JSON string causes grief, and we want
        to support single quotes in variable names. The only work around I
        know of is to convert the single quotes within the string to '\u0027'.
        This is, of course, a time-consuming step we want to avoid when
        JSON-ifying a large chunk of data.  It is less time-consuming to
        replace the quotes in the smaller vmap.

        The series names will not contain single quotes.

        """

        debug = False

        dsinfo = self.get_dataset_info()

        if not dsinfo['time_name']:
            self.scan_files()
            dsinfo = self.get_dataset_info()

        dsinfo_vars = dsinfo['variables']

        if not selectdim:
            selectdim = {}

        vshapes = self.resolve_variable_shapes(variables, selectdim)

        res_data = {}

        total_size = 0
        ntimes = 0

        files = self.get_files(start_time, end_time)
        if debug:
            _logger.debug(
                "len(files)=%d, series_name_fmt=%s",
                len(files), series_name_fmt)

        if series_name_fmt:
            file_tuples = [(f.time.strftime(series_name_fmt), f.path) \
                for f in files]
        else:
            file_tuples = [("", f.path) for f in files]

        for (series_name, ncpath) in file_tuples:

            if series and not series_name in series:
                continue

            if debug:
                _logger.debug("series=%s", str(series))
                _logger.debug("series_name=%s ,ncpath=%s", series_name, ncpath)

            # the files might be in the process of being moved, deleted, etc
            fileok = False
            exc = None
            for itry in range(0, 3):
                try:
                    ncfile = netCDF4.Dataset(ncpath)
                    fileok = True
                    break
                except (OSError, RuntimeError) as excx:
                    exc = excx
                    time.sleep(itry)

            if not fileok:
                _logger.error("%s: %s", ncpath, exc)
                continue

            if not series_name in res_data:
                res_data[series_name] = {
                    'time': [],
                    'data': [],
                    'vmap': {},
                    'dim2': {},
                    'stnnames': {},
                }

            otime = res_data[series_name]['time']
            odata = res_data[series_name]['data']
            ovmap = res_data[series_name]['vmap']
            odim2 = res_data[series_name]['dim2']
            ostns = res_data[series_name]['stnnames']

            try:
                size1 = sys.getsizeof(otime)

                # times are apended to otime
                time_slice = self.read_times(
                    ncfile, ncpath, start_time, end_time, otime,
                    size_limit - total_size)

                # time_slice.start is None if nothing to read
                if time_slice.start is None or \
                    time_slice.stop <= time_slice.start:
                    continue

                total_size += sys.getsizeof(otime) - size1

                for exp_vname in variables:

                    # skip if variable is not a time series or
                    # doesn't have a selected dimension
                    if not exp_vname in dsinfo_vars or not exp_vname in vshapes:
                        continue

                    # selected shape of this variable
                    vshape = vshapes[exp_vname]
                    vsize = reduce_(
                        operator.mul, vshape, 1) * \
                        dsinfo_vars[exp_vname]["dtype"].itemsize

                    if not vsize:
                        continue

                    if total_size + vsize > size_limit:
                        raise nc_exc.TooMuchDataException(
                            "too much data requested, will exceed {} mbytes".
                            format(size_limit/(1000 * 1000)))

                    dim2 = {}
                    stnnames = []
                    vdata = self.read_time_series_data(
                        ncfile, ncpath, exp_vname, time_slice, vshape,
                        selectdim, dim2, stnnames)

                    if vdata is None:
                        continue

                    # dim2 will be empty if variable is not found in file
                    if dim2 and not exp_vname in odim2:
                        odim2[exp_vname] = dim2

                    # stnnames will be empty if variable is not found in file
                    if stnnames and not exp_vname in ostns:
                        ostns[exp_vname] = stnnames

                    if not exp_vname in ovmap:
                        size1 = 0
                        vindex = len(odata)
                        odata.append(vdata)
                        ovmap[exp_vname] = vindex
                    else:
                        if debug:
                            _logger.debug(
                                "odata[%s].shape=%s, vdata.shape=%s",
                                exp_vname, odata[vindex].shape, vdata.shape)

                        vindex = ovmap[exp_vname]
                        size1 = sys.getsizeof(odata[vindex])

                        time_index = dsinfo_vars[exp_vname]["time_index"]
                        odata[vindex] = np.append(
                            odata[vindex], vdata, axis=time_index)

                    total_size += sys.getsizeof(odata[vindex]) - size1

            finally:
                ncfile.close()

            ntimes += len(otime)

        if ntimes == 0:
            exc = nc_exc.NoDataException(
                "No data between {} and {}".
                format(
                    start_time.isoformat(),
                    end_time.isoformat()))
            # _logger.warning("%s: %s", str(self), repr(exc))
            raise exc

        if debug:
            for series_name in res_data:
                for exp_vname in res_data[series_name]['vmap']:
                    var_index = res_data[series_name]['vmap'][exp_vname]
                    _logger.debug(
                        "res_data[%s]['data'][%d].shape=%s, exp_vname=%s",
                        series_name, var_index,
                        repr(res_data[series_name]['data'][var_index].shape),
                        exp_vname)
            _logger.debug(
                "total_size=%d", total_size)

        return res_data
