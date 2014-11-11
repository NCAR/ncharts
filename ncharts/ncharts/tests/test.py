from charts.models import Root, Project, Platform, Dataset, Variable
# UserSelection, SelectedVariable, SelVar
from charts.forms import DatasetSelectionForm


project_name = 'Weather'
project = Project.objects.get(name=project_name)
dsets = project.dataset_set.all()

dataset_name = 'flab-5min'
dataset = project.dataset_set.get(name=dataset_name)

form = DatasetSelectionForm(dataset=dataset)


from pytz import timezone, utc
from datetime import datetime, timedelta

mtn = timezone("US/Mountain")

projroot = Root.objects.create(name='projects')
platroot = Root.objects.create(name='platforms')

proj = Project.objects.create(name='Weather', projects=projroot)

wx = Platform.objects.create(name='Weather Station',platforms=platroot)

dset = Dataset.objects.create(name='flab-5min',
    location='NCAR Foothills Lab, Boulder CO',
    timezone='US/Mountain',
    directory='/home/maclean/www/weather/flab/data',
    filenames='flab.%Y%m%d.cdf',
    variables = 'tdry, rh, pres, cpres0, dp, wdir, wspd, wmax, wchill, raina, raina24',
    start_time = datetime(2009,1,1,0,0,0,tzinfo=utc),
    end_time = datetime.now(utc),
    project=proj)

dset.add_platform(wx)

usersel = UserSelection.objects.create(
    dataset = dset,
    start_time = datetime(2013,9,27,0,0,0,tzinfo=utc),
    end_time = datetime.now(utc),
    # variables = 'tdry, rh, pres, cpres0, dp, wdir, wspd, wmax, wchill, raina, raina24'
    )

tdry = SelectedVariable.objects.create(name='tdry',selected=False)

link = SelVar(var=tdry,sel=usersel)

# usersel.variables.add(tdry)

# f = UserSelectionForm(instance=usersel)

