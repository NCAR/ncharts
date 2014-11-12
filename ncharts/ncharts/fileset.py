# -*- mode: python; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014, Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

import os, glob, stat, re, sys
# from stat import *
from datetime import datetime
from pytz import utc
from ncharts import netcdf
import sre_constants

# DatasetView.post():
#       know dataset, including directory, file name format, start, stop
#               times, selected variables
#       convert % descriptors to regex's, as in R.
#       also can have a P<flight> regex
#       scan directories (is there only one?), save directory modification
#               times,
#               convert file names to start times
#       return list of file names:  getFiles(dir,namefmt,start,end), simple function
#               should it be a class?
#                       "hashed" by dir and namefmt
#                       keep dir mod times, as well as file names and start times
#                       how does django know to get rid of this?
#                               I don't think it's an issue. Could have exp date
#                       it is independent of the requests, multiple requests could use it
#               on subsequent getFiles, check to see if dir mod time is newer, if so
#                       rescan
#       return list of ts variables,units, long_names,
#                dimensions (station, sample)
#                getTSVariables(fullfilenames,type): class function
#       dictionary of NetCDFFileSets, indexed by hash of dir + namefmt
#       at some point will also probably want station names
#       getTSData(start,end,varnames,dimension start, count)
#               

cached_filesets = {}
cached_dirs = {}

def globifyTimeDescriptors(path):
    '''
    Convert strptime time descriptors in path, such as '%Y', to a glob-compatible expression.
    '''
    path = path.replace('%Y','[12][0-9][0-9][0-9]')
    path = path.replace('%y','[0-9][0-9]')
    path = path.replace('%m','[01][0-9]')
    path = path.replace('%d','[0-3][0-9]')
    path = path.replace('%H','[0-2][0-9]')
    path = path.replace('%M','[0-5][0-9]')
    path = path.replace('%S','[0-5][0-9]')
    return path

def pathsplit(path):
    """ Like os.path.split, but the first value returned is the leading portion of the path.
    For 'a/b/c/d.txt' return ('a','b/c/d.txt"), whereas os.path.split() returns
    ('a/b/c','d.txt')
    """

    # python.org says do not use os.sep to split path names, use os.path.split()
    tail = ''
    rem = ''
    while len(path) > 0 and not path == os.sep:
        # print('path=',path)
        if (len(rem) > 0):
            rem = os.path.join(tail,rem)
        else:
            rem = tail
        (path,tail) = os.path.split(path)
    return (tail,rem)

class File:
    """ A file path, the path expression containing time descriptors that 
    was used to create the path, and the associated time parsed from the
    path.
    """
    def __init__(self,path,pathexpr):
        self.path = path
        self.pathexpr = pathexpr
        # print('path=',path,', pathexpr=',pathexpr)
        try:
            self.time = utc.localize(datetime.strptime(path,pathexpr))
            return
        except ValueError as e:
            print(e.args)
            raise
        except sre_constants.error as e:
            print(e.args)
        except:
            print('unexpected error:',sys.exc_info()[0])
            raise

        # strptime chokes when there are two time descriptors for
        # the same time quantity, e.g. two %Y in 'dir/data_%Y/file_%Y%m%d.dat'
        # convert the first %Y, %m etc to '' pathexpr, and use
        # reg expressions to convert those characters to '' in path.

        #   pathexpr = 'dir/data_%Y/file_%Y%m%d.dat'
        #   path = 'dir/data_2013/file_20130715.dat'
        #
        #   want, for purposes of parsing:
        #   pathexpr = 'dir/data_/file_%Y%m%d.dat'
        #   path = 'dir/data_/file_20130715.dat'
        #
        #   convert
        #   pathexpr = 'dir/data_%Y/file_%Y%m%d.dat'
        #   to
        #   pathexpr = 'dir/data_[12][0-9][0-9][0-9]/file_%Y%m%d.dat'
        #   pat = '^(dir/data_)[12][0-9][0-9][0-9](.*)$'
        #   i is index of '%Y' in pathexpr
        #   pat is '^(' + pathexpr up to i + ')[12][0-9][0-9][0-9](.*)$'
        #   path = re.sub(pat,'\1\2',path)
        #   'dir/data_/file_20130715.dat'
        #   try strptime,
        #   cycle through replace dict {'%Y: '[12][0-9][0-9][0-9]',
        #       trying strptime, and if you get sre_constants.error
        #       keey trying
        #   pathexpr is common to all files, is there a way
        #   so that this process happens only once?
        #   but path must be changed at the same time. Difficult
        #   need a re that is applied to remove unneeded fields
        #
        # this still needs work...

        pref = os.path.commonprefix([path,pathexpr])
        path = path.replace(pref,'')
        pathexpr = pathexpr.replace(pref,'')
        while pathexpr.count('%Y') > 1:
            pattern = pathexpr.replace('%Y','[12][0-9][0-9][0-9]',1)
            path = re.sub(pattern,'',path,count=1)
            pathexpr = pathexpr.replace('%Y','')
        if pathexpr.count('%y') > 1:
            pattern = pathexpr.replace('%y','[0-9][0-9]',1)
            path = re.sub(pattern,'',path,count=1)
            pathexpr = pathexpr.replace('%y','')
        if pathexpr.count('%m') > 1:
            pattern = pathexpr.replace("%m","[01][0-9]")
            path = re.sub(pattern,'',path,count=1)
            pathexpr = pathexpr.replace('%m','')
        if pathexpr.count('%d') > 1:
            pattern = pathexpr.replace("%d","[0-3][0-9]")
            path = re.sub(pattern,'',path,count=1)
            pathexpr = pathexpr.replace('%d','')
        try:
            print('try again, path=',path,', pathexpr=',pathexpr)
            self.time = datetime.strptime(path,pathexpr)
        except ValueError as e:
            print(e.args)
            raise
        except sre_constants.error as e:
            print(e.args)
        except:
            print('unexpected error:',sys.exc_info()[0])
            raise

class Dir:
    """ A path to a directory, and a string, such as 'data/prelim/acme_%Y%m%d.nc' , containing possible time format descriptors and eventually regular expressions, describing a set of files relative to this directory.
    """

    def __init__(self,path,pathexpr,pathrem):
        """
        """
        self.path = path    # real path with no time or regular expressions
        self.pathexpr = pathexpr    # current path with expressions
        self.pathrem = pathrem      # remainder of path, with possible expressions
        self.modtime = datetime.min # modification time of current path
        self.mydirs = []            # dirs matching initial portion of
                                    #   pathexpr in this directory
        self.myfiles = []           # files matching initial portion of
                                    #   pathexpr in this directory
        cached_dirs[hash(path) + hash(pathrem)] = self

    def get(path,pathexpr,pathrem):
        hv = hash(path) + hash(pathrem)
        if hv in cached_dirs:
            return cached_dirs[hv]
        else:
            return Dir(path,pathexpr,pathrem)

    def scan(self,start_time=datetime.min ,end_time=datetime.max) -> 'list of matching files':
        """ Scan this Dir for matching subdirectories and files, returning the list of all files found. 
        Matching subdirectories are scanned recursively.
        """

        files = []

        try:
            pstat = os.stat(self.path)
        except FileNotFoundError as e:
            print(e)
            raise

        dirmodtime = datetime.utcfromtimestamp(pstat.st_mtime)

        # modification time is newer than last scan
        if dirmodtime > self.modtime:

            (nextpath,pathrem) = pathsplit(self.pathrem)

            globpath = globifyTimeDescriptors(nextpath)

            for subpath in glob.iglob(os.path.join(self.path,globpath)):
                # print('subpath=',subpath)
                try:
                    pstat = os.stat(subpath)
                except FileNotFoundError as e:
                    print(e)
                    raise
                if stat.S_ISDIR(pstat.st_mode):
                    pdir = Dir.get(subpath,os.path.join(self.pathexpr,nextpath),pathrem)
                    self.mydirs.append(pdir)
                    files.extend(pdir.scan())
                else:
                    pfile = File(subpath,os.path.join(self.pathexpr,nextpath))
                    files.append(pfile)
                    self.myfiles.append(pfile)
            try:
                pstat = os.stat(self.path)
            except FileNotFoundError as e:
                print(e)
                raise
            self.modtime = datetime.utcfromtimestamp(pstat.st_mtime)
            self.myfiles.sort(key=lambda x: x.time)
        else:
            for pdir in self.mydirs:
                files.extend(pdir.scan())
            files.extend(self.myfiles)

        # exclude files whose time is after end_time, then sort
        files = sorted(list(filter(lambda x: x.time < end_time,files)),
                key=lambda x: x.time)
        # index of first element whose time is > start_time
        # we want to include the previous file
        if len(files) == 0:
            return files
        i = next(filter(lambda i: files[i].time > start_time,range(len(files))))
        return files[max(i-1,0):]

class Fileset:
    ''' '''
    def get(path):
        if path in cached_filesets:
            return cached_filesets[path]
        fset = Fileset(path)
        cached_filesets[path] = fset
        return fset

    def __init__(self,path):
        self.path = path
        pathrem = ''
        while '%' in path:
            (path,tail) = os.path.split(path)
            if (len(pathrem) > 0):
                pathrem = os.path.join(tail,pathrem)
            else:
                pathrem = tail
        self.pathrem = pathrem
        self.pdir = Dir(path,path,pathrem)

    def scan(self,start_time=utc.localize(datetime.min) ,
            end_time=utc.localize(datetime.max)):
        return self.pdir.scan(start_time,end_time)

    def get_variables(self,start_time=utc.localize(datetime.min) ,
            end_time=utc.localize(datetime.max)):
        files = [f.path for f in self.scan(start_time=start_time, end_time=end_time)]

        # if files are too many select a subset
        dset = netcdf.NetCDFDataset(files)

        return dset.variables
        
