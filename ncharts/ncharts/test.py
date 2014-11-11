import os
import netCDF4
from ncharts import fileset
from ncharts import netcdf
from datetime import datetime
from pytz import utc


ndir='/home/maclean/isff/projects/METCRAXII/ISFF/netcdf'
nfile='isfs_%Y%m%d.nc'

start_time = datetime(2013,10,2,19,0,0,tzinfo=utc)
end_time = datetime(2013,10,5,19,0,0,tzinfo=utc)

fset = fileset.Fileset.get(os.path.join(ndir,nfile))

files = [f.path for f in fset.scan(start_time=start_time, end_time=end_time)]

ncdset = netcdf.NetCDFDataset(files)

d = ncdset.read(variables=["RH_40m_rim"],start_time=start_time,end_time=end_time)


"""

nc = netCDF4.MFDataset(files)
KeyError: 'Rsw_out_flr'
nc = netCDF4.MFDataset(files[5:9])

tv = nc.variables['time']

dir(tv.__class__)

tv._shape()
dir(nc.variables['time'].__class__)
"""

nfile='/home/maclean/isff/projects/METCRAXII/ISFF/netcdf/isfs_20131005.nc'
ds = netCDF4.Dataset(nfile)

var = ds.variables["time"]










