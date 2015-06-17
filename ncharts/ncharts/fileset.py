# -*- mode: python; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Support for handling a set of files with with time-stamps in their names.

2014, Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

import os, glob, stat, re, sys, threading, logging
# from stat import *
import datetime
from pytz import utc
import sre_constants

_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

def globify_time_descriptors(path):
    """Convert strftime time descriptors to a glob-compatible expression.

    For example, convert,'%Y' to '[12][0-9][0-9][0-9]'. Then the
    glob expression can be used to match path names containing
    a four digit year.
    """

    path = path.replace('%Y', '[12][0-9][0-9][0-9]')
    path = path.replace('%y', '[0-9][0-9]')
    path = path.replace('%m', '[01][0-9]')
    path = path.replace('%d', '[0-3][0-9]')
    path = path.replace('%H', '[0-2][0-9]')
    path = path.replace('%M', '[0-5][0-9]')
    path = path.replace('%S', '[0-5][0-9]')
    return path

def pathsplit(path):
    """Like os.path.split, but the first value returned is the leading
    portion of the path.

    For 'a/b/c/d.txt' pathsplit returns ('a','b/c/d.txt"), whereas
    os.path.split() returns ('a/b/c','d.txt').  For 'a',
    pathsplit returns ('a','')
    """

    # python.org says do not use os.sep to split path names, use
    # os.path.split()
    tail = ''
    rem = ''
    while len(path) > 0 and not path == os.sep:
        if len(rem) > 0:
            rem = os.path.join(tail, rem)
        else:
            rem = tail
        (path, tail) = os.path.split(path)
    return (tail, rem)

# pylint: disable=too-few-public-methods
class File(object):
    """A file path, the path expression containing time descriptors that
    was used to find the file, and the associated time parsed from the
    path.

    Attribute:
        path: A str containing the actual path to the file.
        pathdesc: A str containing the path, with possible datetime
            strftime descriptors, such as '%Y'.
        time: datetime.datetime parsed from the path using pathdesc.

    """

    def __init__(self, path, pathdesc):
        """Construct a File, and parse its associated time from path
            using pathdesc.

        Args:
            path: The path to the file.
            pathdesc: A str containing the path to the file, with possible
                datetime strftime descriptors, such as '%Y'.
        """

        self.path = path
        self.pathdesc = pathdesc
        try:
            self.time = utc.localize(datetime.datetime.strptime(path, pathdesc))
            return
        except ValueError as exc:
            _logger.error("fileset.File __init__: %s", exc)
            raise
        except sre_constants.error as exc:
            _logger.error("fileset.File __init__: %s", exc)
        except:
            _logger.error(
                "fileset.File __init__ unexpected error: %s",
                sys.exc_info()[0])
            raise

        # strptime chokes when there are two time descriptors for
        # the same time quantity, e.g. two %Y in 'dir/data_%Y/file_%Y%m%d.dat'
        # convert the first %Y, %m etc to '' in pathdesc, and use
        # reg expressions to convert those characters to '' in path.

        #   pathdesc = 'dir/data_%Y/file_%Y%m%d.dat'
        #   path = 'dir/data_2013/file_20130715.dat'
        #
        #   want, for purposes of parsing:
        #   pathdesc = 'dir/data_/file_%Y%m%d.dat'
        #   path = 'dir/data_/file_20130715.dat'
        #
        #   convert
        #   pathdesc = 'dir/data_%Y/file_%Y%m%d.dat'
        #   to
        #   pathdesc = 'dir/data_[12][0-9][0-9][0-9]/file_%Y%m%d.dat'
        #   pat = '^(dir/data_)[12][0-9][0-9][0-9](.*)$'
        #   i is index of '%Y' in pathdesc
        #   pat is '^(' + pathdesc up to i + ')[12][0-9][0-9][0-9](.*)$'
        #   path = re.sub(pat,'\1\2',path)
        #   'dir/data_/file_20130715.dat'
        #   try strptime,
        #   cycle through replace dict {'%Y: '[12][0-9][0-9][0-9]',
        #       trying strptime, and if you get sre_constants.error
        #       keey trying
        #   pathdesc is common to all files, is there a way
        #   so that this process happens only once?
        #   but path must be changed at the same time. Difficult
        #   need a re that is applied to remove unneeded fields
        #
        # this still needs work...

        pref = os.path.commonprefix([path, pathdesc])
        path = path.replace(pref, '')
        pathdesc = pathdesc.replace(pref, '')
        while pathdesc.count('%Y') > 1:
            pattern = pathdesc.replace('%Y', '[12][0-9][0-9][0-9]', 1)
            path = re.sub(pattern, '', path, count=1)
            pathdesc = pathdesc.replace('%Y', '')
        if pathdesc.count('%y') > 1:
            pattern = pathdesc.replace('%y', '[0-9][0-9]', 1)
            path = re.sub(pattern, '', path, count=1)
            pathdesc = pathdesc.replace('%y', '')
        if pathdesc.count('%m') > 1:
            pattern = pathdesc.replace("%m", "[01][0-9]")
            path = re.sub(pattern, '', path, count=1)
            pathdesc = pathdesc.replace('%m', '')
        if pathdesc.count('%d') > 1:
            pattern = pathdesc.replace("%d", "[0-3][0-9]")
            path = re.sub(pattern, '', path, count=1)
            pathdesc = pathdesc.replace('%d', '')
        try:
            # print('try again, path=', path, ', pathdesc=', pathdesc)
            self.time = datetime.datetime.strptime(path, pathdesc)
        except ValueError as exc:
            _logger.error("fileset.File __init__ %s:", exc)
            raise
        except sre_constants.error as exc:
            _logger.error("fileset.File __init__ %s:", exc)
        except:
            _logger.error(
                "fileset.File __init__ unexpected error %s:",
                sys.exc_info()[0])
            raise

class Dir(object):
    """A directory that can be scanned for files matching a
    path containing possible datetime strftime descriptors.

    Example, initial call from Fileset:
        dir = Dir.get(path='/data/acme',pathdesc='/data/acme',
            pathrem='%Y/xxx_%Y%m%d.nc')

        When dir.scan(t1,t2) is called, then for each 4 digit subdirectory
            of /data/acme that is found, then a recursive call for
            files matching 'xxx_%Y%m%d.nc' is performed.

        For example, if '/data/acme' contains a directory '2014':

            subdir = Dir.get(path='/data/acme/2014',pathdesc='/data/acme/%Y'
                pathrem='xxx_%Y%m%d.nc')

        Scan is recursively called on subdir:
            res = subdir.scan(t1,t2)

        Assuming that one or more files in subdir match 'xxx_%Y%m%d.nc',
        for the time period, the list of File objects is returned.
        For example:
        [
            File('/data/acme/2014/xxx_20140414.nc',
                '/data/acme/%Y/xxx_%Y%m%d.nc'),

            File('/data/acme/2014/xxx_20140415.nc',
                '/data/acme/%Y/xxx_%Y%m%d.nc')
        ]

    Attributes:

        path: A str, path to a directory.
        pathdesc: Same as path attribute, but with possible datetime
            descriptors that were resolved to create the actual path.
        pathrem: Remainder of path to be scanned, with possible descriptors.
        modtime: Modification time of the directory at the time it was
            last scanned. If modtime has not changed from the last scan
            then the cached values can be used.
        cached_subdirs: List of Dir objects scanned in this directory
            which match the head portion of pathrem.
        cached_files: List of File objects in this directory which match
            the head portion of pathrem.
        double_check: Have the directory contents been double checked?
        lock: Mutex for modtime, cached_subdirs, cached_files
    """

    __cached_filesets = {}
    __cached_dirs = {}
    __cache_lock = threading.Lock()

    def __init__(self, path, pathdesc, pathrem):
        """Create a Dir.

        Args:
            path: A str, path to a directory.
            pathdesc: A str, same as path, but with possible datetime
                descriptors, such as %Y, %m, %d that were resolved
                to create path.
            pathrem: The portion of pathdesc after path to be scanned.
        """

        self.path = path
        self.pathdesc = pathdesc
        self.pathrem = pathrem
        self.modtime = datetime.datetime.min
        self.cached_subdirs = []
        self.cached_files = []
        self.double_check = False
        self.lock = threading.Lock()

    @staticmethod
    def get(path, pathdesc, pathrem):
        """Return a Dir, which may be from a cache in order to
        avoid repeated scans.
        """

        Dir.__cache_lock.acquire()

        hashval = hash(path) + hash(pathrem)
        if hashval in Dir.__cached_dirs:
            ddir = Dir.__cached_dirs[hashval]
        else:
            ddir = Dir(path, pathdesc, pathrem)
            Dir.__cached_dirs[hash(path) + hash(pathrem)] = ddir

        Dir.__cache_lock.release()
        return ddir

    def scan(self, start_time=datetime.datetime.min,
             end_time=datetime.datetime.max):
        """Scan this Dir for files which match by name and time.

        The current directory is scanned for files which match pathrem.
        Also any subdirectories that match the head of pathrem are
        scanned. A list of files is returns whose associated times
        are within the period [start_time, end_time).

        If the directory has not been modified since the
        previous scan, then the previous list of files in the
        directory, if any is returned.  Scans are performed
        on any subdirectories which match the head of pathrem.

        Args:
            start_time: A datetime.datetime, start of the time period.
            end_time: A datetime.datetime, end of the time period.

        Returns:
            A list of matching File objects, sorted by their associated
            path time, whose times fall within [start_time, end_time).

        Raises:
            FileNotFoundError, PermissionError
        """

        files = []

        try:
            pstat = os.stat(self.path)
        except FileNotFoundError as exc:
            _logger.error(exc)
            raise
        except PermissionError as exc:
            _logger.error(exc)
            raise

        dirmodtime = datetime.datetime.utcfromtimestamp(
            pstat.st_mtime_ns / 1.0e9)

        # get previous snapshot of this directory
        self.lock.acquire()
        prevmodtime = self.modtime
        cached_files = self.cached_files.copy()
        cached_subdirs = self.cached_subdirs.copy()
        double_check = self.double_check
        self.lock.release()

        # Check if modification time of directory is newer than it
        # was at the time of the last directory scan.
        # After 10 seconds have elapsed since the directory modification
        # time, do a second check of its contents.
        # Without this double check there were a significant
        # number of times that a new file was not seen in a
        # directory. Must have been due to either:
        #   1. bug
        #   2. directory modification time was updated before
        #       the os.stat succeeds on the new file
        #   3. file added but directory mod time was not updated.
        # Perhaps this is a symptom of an NFS file system.

        if dirmodtime > prevmodtime or \
            (datetime.datetime.now() > \
                prevmodtime + datetime.timedelta(seconds=10) and \
                not double_check):
            double_check = dirmodtime == prevmodtime
            cached_files = []
            cached_subdirs = []
            prevmodtime = dirmodtime

            (nextpath, pathrem) = pathsplit(self.pathrem)

            # next portion of path
            globpath = globify_time_descriptors(nextpath)

            # search for directories
            for subpath in glob.iglob(os.path.join(self.path, globpath)):
                # print('subpath=', subpath)
                try:
                    pstat = os.stat(subpath)
                except FileNotFoundError as exc:
                    _logger.error(exc)
                    continue    # maybe it was (very) recently deleted
                except PermissionError as exc:
                    _logger.error(exc)
                    continue
                if stat.S_ISDIR(pstat.st_mode):
                    pdir = Dir.get(
                        subpath, os.path.join(self.pathdesc, nextpath), pathrem)
                else:
                    pfile = File(subpath, os.path.join(self.pathdesc, nextpath))
                    cached_files.append(pfile)

            # save snapshot
            self.lock.acquire()
            self.modtime = prevmodtime
            self.double_check = double_check
            self.cached_files = sorted(cached_files, key=lambda x: x.time)
            self.cached_subdirs = cached_subdirs
            self.lock.release()

        for pdir in cached_subdirs:
            # recursive listing.
            files.extend(pdir.scan(start_time, end_time))

        files.extend(cached_files)

        if len(files):
            _logger.debug(
                "scan of %s: total # of files=%d",
                self.path, len(files))

        # exclude files whose time is equal to or after end_time, then sort
        files = sorted(
            list(
                [x for x in files if x.time < end_time]),
            key=lambda x: x.time)

        i = 0
        for i in range(len(files)):
            if files[i].time > start_time:
                break

        # we want to include the previous file
        files = files[max(i-1, 0):]
        # print("len(files)=", len(files))
        return files

class Fileset(object):
    """A set of files defined by a path, which usually contains
    datetime descriptors, such as %Y, %m and %d.

    Attributes:
        path: A str, path with possible strptime descriptors.
        pdir: Dir corresponding to initial portion directory path up to
            a directory or file name with strptime descriptors.
    """

    __cached_filesets = {}

    __cached_dirs = {}

    __cache_lock = threading.Lock()

    def __init__(self, path):
        """Construct a Fileset from a path, which may contain
        datetime strptime descriptors, such as %Y

        Args:
            path: A str, containing the path to the dataset, with possible
                datetime descriptors, such as '/data/acme/xxx_%Y%m%d_%H%M.nc'.
        """
        self.path = path
        pathrem = ''

        # Look for datetime descriptors in path
        while '%' in path:
            # returns a empty string for path if there is only
            # a last pathname component: os.path.split('a') returns ('', 'a')
            (path, tail) = os.path.split(path)
            if len(pathrem) > 0:
                pathrem = os.path.join(tail, pathrem)
            else:
                pathrem = tail

        self.pdir = Dir.get(path, path, pathrem)

    def __str__(self):
        return self.path

    @staticmethod
    def get(path):
        """Fetch a Fileset by path, which may be cached.

        Args:
            path: A str, path describing the Fileset, which may
                contain datetime strftime descriptors.
        """
        Fileset.__cache_lock.acquire()
        if path in Fileset.__cached_filesets:
            fset = Fileset.__cached_filesets[path]
        else:
            fset = Fileset(path)
            Fileset.__cached_filesets[path] = fset

        Fileset.__cache_lock.release()
        return fset

    def scan(
            self, start_time=utc.localize(datetime.datetime.min),
            end_time=utc.localize(datetime.datetime.max)):
        """Scan this Fileset for files matching a time period.

        Args:
            start_time: A datetime.datetime, start of the time period.
            end_time: A datetime.datetime, end of the time period.

        Returns:
            A list of matching File objects, sorted by their associated
            path time, whose times fall within [start_time, end_time).

        Raises:
            FileNotFoundError, PermissionError

        """
        return self.pdir.scan(start_time, end_time)

