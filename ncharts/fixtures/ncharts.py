from ncharts.models import Project, Platform, FileDataset, UserSelection, Variable, TimeZone

from pytz import timezone, utc
from datetime import datetime, timedelta

from django.core import serializers

mtntz = TimeZone.objects.create(tz='US/Mountain')
objs = TimeZone.objects.all()
serializers.serialize('json',objs)

mttz = timezone("US/Mountain")
aztz = timezone("US/Arizona")

proj = Project.objects.create(name='Weather')

wx = Platform.objects.create(name='Weather Station')

wxvars = []
for v in ['tdry','rh','pres','cpres0','dp','wdir','wspd','wmax','wchill','raina','raina24']:
    var = Variable.objects.create(name=v)
    wxvars.append(var)

dset = FileDataset.objects.create(name='flab-5min_x3',
    location='NCAR Foothills Lab, Boulder CO',
    timezone='US/Mountain',
    directory='/home/maclean/www/weather/flab/data',
    filenames='flab.%Y%m%d.cdf',
    start_time = mttz.localize(datetime(2009,1,1,0,0,0),is_dst=True),
    end_time = datetime.now(mttz),
    project=proj)

for var in wxvars:
    dset.variables.add(var)

dset.add_platform(wx)
# dset.platforms.add(wx)
# dset.project.platforms.add(wx)
# dset.save()

dset = FileDataset.objects.create(name='nwsc-5min',
    location='NCAR Wyoming Supercomputer Center, Cheyenne WY',
    timezone='US/Mountain',
    directory='/home/maclean/www/weather/nwsc/data',
    filenames='nwsc.%Y%m%d.cdf',
    start_time = mttz.localize(datetime(2009,1,1,0,0,0),is_dst=True),
    end_time = datetime.now(mttz),
    project=proj)

dset.add_platform(wx)
# dset.platforms.add(wx)
# dset.project.platforms.add(wx)
# dset.save()

for var in wxvars:
    dset.variables.add(var)


proj = Project.objects.create(name='METCRAXII')

isfs = Platform.objects.create(name='ISFS')

tz = timezone("US/Arizona")

dset = FileDataset.objects.create(name='5min',
    location='Meteor Crater',
    timezone='US/Arizona',
    directory='/home/maclean/isfs/projects/METCRAXII/netcdf',
    filenames='isfs_%Y%m%d.nc',
    start_time = aztz.localize(datetime(2013,9,27,0,0,0),is_dst=True),
    end_time = aztz.localize(datetime(2013,11,2,0,0,0),is_dst=True),
    project=proj)
dset.add_platform(isfs)
# dset.platforms.add(isfs)
# dset.project.platforms.add(isfs)
# dset.save()

dset = FileDataset.objects.create(name='hr',
    location='Meteor Crater',
    timezone='US/Arizona',
    directory='/home/maclean/isfs/projects/METCRAXII/netcdf_hr',
    filenames='isfs_%Y%m%d.nc',
    start_time = aztz.localize(datetime(2013,9,27,0,0,0),is_dst=True),
    end_time = aztz.localize(datetime(2013,11,2,0,0,0),is_dst=True),
    project=proj)

dset.add_platform(isfs)
# dset.platforms.add(isfs)
# dset.project.platforms.add(isfs)
# dset.save()

objs = list(FileDataset.objects.all()) + list(Dataset.objects.all())
serializers.serialize('json',objs)

'''
usersel = UserSelection.objects.create(
    dataset = dset,
    start_time = datetime(2013,9,27,0,0,0,tzinfo=utc),
    end_time = datetime.now(utc),
    # variables = 'tdry, rh, pres, cpres0, dp, wdir, wspd, wmax, wchill, raina, raina24'
    )

tdry = SelectedVariable.objects.create(name='tdry',selected=False)

usersel.variables.add(tdry)

# f = UserSelectionForm(instance=usersel)

'''
