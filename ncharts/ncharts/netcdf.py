
import netCDF4
from datetime import datetime
import pytz
import numpy

class NetCDFDataset:
    ''' crude alternative to netCDF4.MFDataset, allowing for a variable to be missing in
    one or more files.
    '''

    def __init__(self, files, time_names=['time','time_offset']):

        """
        """

        self.files = files
        self.variables = {}

        for file in self.files:
            try:
                print("file=",file)
                ds = netCDF4.Dataset(file)

                if not "base_time" in self.__dict__ and "base_time" in ds.variables:
                    self.base_time = "base_time"

                if not "time_dim" in self.__dict__ and "time" in ds.dimensions:
                    tdim = ds.dimensions["time"]
                    # tdim.is_unlimited
                    self.time_dim = "time"
                else:
                    continue

                if "station" in ds.dimensions:
                    if not "nstations" in self.__dict__:
                        self.nstations = len(ds.dimensions["station"])
                        self.station_dim = "station"
                    elif not self.nstations == len(ds.dimensions["station"]):
                        print("station dimension is changing")

                    if not "station_names" in self and "station" in ds.variables:
                        var = ds.variables["station"]
                        if var.datatype == numpy.dtype('S1'):
                            self.station_names = [str(netCDF4.chartostring(v)) for v in var]

                if not "time_name" in self.__dict__:
                    for (n,v) in ds.variables.items():
                        if n in time_names and tdim._name in v.dimensions:
                            self.time_name = n
                            break
                    if not "time_name" in self.__dict__:
                        continue

                for (n,v) in ds.variables.items():
                    if tdim._name in v.dimensions:
                        if not n in self.variables:
                            self.variables[n] = {}
                            self.variables[n]["shape"] = v.shape
                            for a in ["units","long_name","short_name"]:
                                if hasattr(v,a):
                                    self.variables[n][a] = getattr(v,a)

                        elif not self.variables[n] == v.shape:
                            print("shape of variable ",n," is not constant")
                            del(self.variables[n])
                            continue

            finally:
                ds.close()

    def read(self,variables=[],start_time=datetime.min,end_time=datetime.max,
            selectdim={}):
        """
            utime 1403454068 +%c
            Sun Jun 22 16:21:08 2014

        http://momentjs.com/
        http://momentjs.com/timezone/docs/#/use-it/
        In javascript (with moment.tz):
            var timestamp = 1403454068850
            date = new Date(timestamp);

            moment.tz(timestamp, "America/Los_Angeles").format();
                // 2014-06-22T09:21:08-07:00
            moment(timestamp).tz("America/Los_Angeles").format();
                // 2014-06-22T09:21:08-07:00
            moment.tz(date, "America/Los_Angeles").format();
                // 2014-06-22T09:21:08-07:00
            moment(date).tz("America/Los_Angeles").format();
                // 2014-06-22T09:21:08-07:00'

        highcharts
            series: [{
                data: [
                    [Date.UTC(1970,  9, 27), 0   ],
                    [Date.UTC(1970, 10, 10), 0.6 ],
                    [Date.UTC(1970, 10, 18), 0.7 ],


        netCDF4.num2date([i for i in range(10)],'seconds since 1970-01-01 00:00:00 00:00','standard')

        """

        data = {}
        times = []
        for file in self.files:
            try:
                ds = netCDF4.Dataset(file)

                dsdata = {}

                base_time = 0

                if "base_time" in self.__dict__ and self.base_time in ds.variables and len(ds.variables[self.base_time].dimensions) == 0:
                    base_time = ds.variables[self.base_time].getValue()

                if self.time_name in ds.variables:
                    var = ds.variables[self.time_name]
                    if 'units' in var.__dict__ and 'since' in var.units:
                        tv = [d.replace(tzinfo=pytz.UTC) for d in netCDF4.num2date(var[:],var.units,'standard')]
                        # tv = [d.timestamp() for d in netCDF4.num2date(var[:],var.units,'standard')]
                    else:
                        tv = [ datetime.fromtimestamp(base_time + val,tz=pytz.utc) for val in var[:] ]
                    tindex = [ i for i,t in enumerate(tv) if t >= start_time and t < end_time]
                    times.extend([tv[i] for i in tindex])
                else:
                    continue

                idx = (tindex,)
                for vname in variables:
                    if vname in self.variables and vname in ds.variables:
                        vshape = self.variables[vname]["shape"]
                        var = ds.variables[vname]

                        if var.shape != vshape:
                            continue

                        # if len(var.dimensions) < 1 or not var.dimensions[0] == self.time_dim:
                        #     continue

                        # user has asked for variables with a certain dimension
                        for d in selectdim:
                            if not d in var.dimensions:
                                if type(selectdim[d]) == type([]):
                                    if not any(i < 0 for i in selectdim[d]):
                                        continue
                        for d in var.dimensions:
                            if d == self.time_dim:
                                idx = (tindex,)
                            elif d == "sample":
                                # deal with this later...
                                idx += (0)
                            elif d in selectdim:
                                if type(selectdim[d]) == type([]):
                                    idx += (sort([i for i in selectdim[d] if i >= 0]))
                                else:
                                    idx += (selectdim[d])
                            else:
                                idx += (0)

                        dsdata[vname] = var[idx]
            finally:
                ds.close()

            for vname in variables:
                if not vname in dsdata:
                    if not vname in data:
                        data[vname] = numpy.ma.array(data=numpy.empty(
                            shape=self.variables[vname]["shape"],dtype=float),
                            mask=True,fill_value=float('nan'))
                    else:
                        data[vname] = numpy.append(data[vname],
                                numpy.ma.array(data=numpy.empty(
                                    shape=self.variables[vname]["shape"],dtype=float),
                                    mask=True,fill_value=float('nan')))
                else:
                    if not vname in data:
                        data[vname] = dsdata[vname]
                    else:
                        data[vname] = numpy.append(data[vname], dsdata[vname])


        return {"time" : times, "data": data }


