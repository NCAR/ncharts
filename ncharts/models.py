# -*- mode: python; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set tabstop=8 shiftwidth=4 softtabstop=4 expandtab:

"""Models used by ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

import os
import logging
from collections import OrderedDict
from copy import deepcopy
import datetime

import pytz

from django.db import models, transaction

from django.core import exceptions as dj_exc
from django.utils.translation import gettext_lazy

from django.core.validators import validate_comma_separated_integer_list

from timezone_field import TimeZoneField

from ncharts import netcdf, fileset, raf_database

_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

# Categories of ISFS variables. Used in creating tabs
ISFS_VARIABLE_TYPES = {
    "Met": ["T", "RH", "P", "Spd", "Spd_max", "Dir", "U", "V", "Ifan", "Rainr", "Raina", "Tc", "q", "mr"],
    "Rad": ["Rnet", "Rsw", "Rlw", "Rpile", "Rpar", "Tcase", "Tdome", "Wetness"],
    "Soil": ["Tsoil", "dTsoil_dt", "Qsoil", "Gsoil", "Vheat", "Vpile", \
        "Tau63", "Lambdasoil", "asoil", "Cvsoil", "Gsfc"],
    "3D_Wind": ["u", "v", "w", "ldiag", "diagbits", "spd", "spd_max", "dir"],
    "Gas": ["tc", "t", "h2o", "co2", "kh2o", "o3", "irgadiag", "p"],
    "Power": ["Vbatt", "Tbatt", "Iload", "Icharge", "Vmote", "Vdsm"],
    "GPS_Time": ["GPSnsat", "GPSstat", "Stratum", "Timeoffset"]
}

# Tab names and tooltips for ISFS variables, in the order they will appear
ISFS_TABS = OrderedDict([
    ("Met", {"tooltip":"Meteorological Variables", "variables":[]}),
    ("Rad", {"tooltip":"Radiation Variables", "variables":[]}),
    ("Soil", {"tooltip":"Soil Variables", "variables":[]}),
    ("3D_Wind", {"tooltip":"3D Wind Variables", "variables":[]}),
    ("Gas", {"tooltip":"Gas Analyzer Variables", "variables":[]}),
    ("Power", {"tooltip":"Battery and Solar Power", "variables":[]}),
    ("GPS_Time", {"tooltip":"GPS and timekeeping", "variables":[]}),
    ("Other", {"tooltip":"Other Variables", "variables":[]}),
    ("2ndMoment", {"tooltip":"variances, covariances", "variables":[]}),
    ("3rdMoment", {"tooltip":"", "variables":[]}),
    ("4thMoment", {"tooltip":"", "variables":[]})])

def alphabetic_tabs(variables):
    """Create a dictionary of tabs for the elements in variables.

    This is so that a large number of checkbox widgets for the
    selection of data variables to be plotted can be split into
    tabbed panes.

    The tab names can be created from the first character of the
    variable names, or in a platform-dependent way, by a
    category determined from the variable name.

    Args:
        variables: a django.forms.forms.BoundField, such as
        from form['variables'], where form is an instance
        of ncharts.forms.DataSelectionForm, which has a
        class member named variables of type
        forms.MultipleChoiceField. The variables have been
        alphabetically sorted prior to this call.

    Each element returned by iterating over variables is
    a django.forms.widgets.CheckboxChoiceInput.
    An instance of CheckboxChoiceInput has a choice_label
    attribute containing the label part of the choice tuple,
    (the variable name) and a tab attribute, which when
    rendered in a template, creates the checkbox html.

    References to these widgets are copied into lists
    under each tab.
    """

    nvars = len(variables)

    tabs = OrderedDict()

    for var in iter(variables):
        vname = var.choice_label
        char1 = vname[0].upper()
        if not char1 in tabs:
            tabs[char1] = {"variables":[]}
            tabs[char1]["tooltip"] = char1 + " variables"
        tabs[char1]["variables"].append(var)

    # Combine neighboring tabs if they each contain
    # fewer than tab_limit elements
    tab_limit = 10
    comb_tabs = OrderedDict()
    for tab, vals in tabs.items():

        # Sort by first letter
        # vals.sort(key=lambda x: x.choice_label.lower())

        # pylint thinks ctab could be used before assignment
        # pylint: disable=used-before-assignment
        if not comb_tabs or \
                len(comb_tabs[ctab]["variables"]) > tab_limit or \
                len(vals["variables"]) > tab_limit:
            ctab = tab
            comb_tabs[ctab] = vals
        else:
            nctab = ctab[0] + "-" + tab
            if not nctab in comb_tabs:
                comb_tabs[nctab] = {"variables":[]}
            comb_tabs[nctab]["variables"] = comb_tabs[ctab]["variables"] + vals["variables"]
            comb_tabs[nctab]["tooltip"] = nctab + " variables"
            del comb_tabs[ctab]
            ctab = nctab

    # Double check that we didn't lose any variables
    nres = 0
    for tab, vals in comb_tabs.items():
        nres += len(vals["variables"])

    if nres != nvars:
        _logger.error("%d variables unaccounted for in building tabs", (nvars - nres))

    # Create a "fake" top level dictionary with a key of an
    # empty string. This then has the same 2-level structure
    # as the isfs_tabs.
    tabs = OrderedDict()
    tabs[''] = comb_tabs
    return tabs

class TimeZone(models.Model):
    """A timezone.

    Uses TimeZoneField from django-timezone-field app.
    """

    # If you add "default=pytz.utc" to TimeZoneField, then
    # makemigrations fails, reporting it can't serialize "<UTC>".
    # Haven't found a solution, so leave it off. Probably not an issue.

    # pylint thinks this class member name is too short
    # pylint: disable=invalid-name
    tz = TimeZoneField(primary_key=True)

class Project(models.Model):
    """A field project, with a unique name.

    To get all projects:
        Project.objects.all()

    To find all platforms of a project:
        Platform.objects.filter(projects__name__exact='METCRAXII')
    So we don't need this:
        platforms = models.ManyToManyField('ncharts.Platform')

    To find all datasets of a project:
        Dataset.objects.filter(project__name__exact='METCRAXII')
    So, you don't need this:
        datasets = models.ManyToManyField('ncharts.Dataset',
            related_name='datasets')
    """

    name = models.CharField(max_length=64, primary_key=True)

    location = models.CharField(max_length=256, blank=True)

    long_name = models.CharField(
        blank=True,
        max_length=256,
        help_text=gettext_lazy('More detailed description of the project'))

    timezones = models.ManyToManyField(
        TimeZone,
        blank=True,
        related_name='+',
        help_text=gettext_lazy('Supported timezones for plotting data of this project'))

    start_year = models.IntegerField()

    end_year = models.IntegerField(null=True)

    @classmethod
    def make_tabs(cls, projects):

        """A class method for creating dictionary of projects based on
        their start years and end years. The dictionary keys will be the
        years and the values will be the projects that happen within the
        corresponding years. The years and projects are sorted numerically
        and alphabetically.

        Args: The Project class itself and the list of projects from netcdf.
        Ret: The sorted dictionary of years and projects.
        """

        res = {}
        now = datetime.datetime.now()

        for project in projects:
            if project.end_year is None:
                project.end_year = now.year
            for year in range(project.start_year, min(project.end_year, now.year) + 1):
                res[year] = res.get(year, []) + [project]

        for year, pjcts in res.items():
            pjcts.sort(key=lambda x: x.name)

        odres = OrderedDict(sorted(res.items(), key=lambda x: x[0]))

        return odres

    def __str__(self):
        return self.name

class Platform(models.Model):
    """An observing platform with a unique name, deployed on one or more
    projects.

    To get all platforms:
        Platform.objects.all()
    """
    name = models.CharField(max_length=64, primary_key=True)

    long_name = models.CharField(
        blank=True,
        max_length=256,
        help_text=gettext_lazy('More detailed description of the platform'))

    # This adds a platform_set attribute to Project.
    projects = models.ManyToManyField(Project)

    def __str__(self):
        # return 'Platform: %s' % self.name
        return self.name

class Variable(models.Model):
    """A variable in a dataset, used if the dataset does not have
    sufficient meta-data for its variables.
    """

    name = models.CharField(max_length=64)

    units = models.CharField(max_length=64, blank=True)

    long_name = models.CharField(max_length=256, blank=True)

class Dataset(models.Model):
    """A dataset, whose name should be unique within a project.

    Tried making this an abstract base class in django.
    From the django doc on abstract base classes of models:
        This model will then not be used to create any database table.
        Instead, when it is used as a base class for other models,
        its fields will be added to those of the child class. It is
        an error to have fields in the abstract base class with the
        same name as those in the child (and Django will raise an exception).

    However, a Dataset is a ForeignKey of a ClientState, and
    it appears an abstract model cannot be a ForeignKey. So we
    use the Multi-table inheritance in django.

    Then, to determine if a Dataset is a FileDataset, do

    try:
        x = dataset.filedataset
    except FileDataset.DoesNotExist as exc:
        pass

    To find all datasets of a project:
        Dataset.objects.filter(project__name__exact='METCRAXII')

    To find all datasets of a platform:
        Dataset.objects.filter(platforms__name__exact="ISFS")

    To find all datasets of a project and platform:
        Dataset.objects.filter(
            platforms__name__exact=platform_name).filter(
                project__name__exact=project_name)

    Don't add __init__ method, instead add @classmethod create() or a
    custom Manager.
    See https://docs.djangoproject.com/en/dev/ref/models/instances/

    For other instance variables, just set them in instance methods.
    """

    # class Meta:
    #     abstract = False

    name = models.CharField(
        max_length=128,
        help_text=gettext_lazy('The name of a dataset should be unique within a project'))

    long_name = models.CharField(
        blank=True,
        max_length=256,
        help_text=gettext_lazy('More detailed description of a dataset'))

    url = models.URLField(
        blank=True,
        max_length=200,
        help_text=gettext_lazy('The URL that specifies the complete project dataset'))

    status = models.CharField(
        blank=True,
        max_length=256,
        help_text=gettext_lazy('Current status of the project dataset'))

    # This adds a dataset_set attribute to Project
    # on_delete=models.CASCADE (default behavior): when a project is
    # deleted, all its associated DataSets are deleted too.
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        help_text=gettext_lazy('A dataset is associated with one project'))

    # This adds a dataset_set attribute to Platform
    platforms = models.ManyToManyField(
        Platform,
        help_text=gettext_lazy('A dataset is associated with one or more platforms'))

    timezones = models.ManyToManyField(
        TimeZone,
        help_text=gettext_lazy('Overrides the timezones of the project'))

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    location = models.CharField(
        max_length=256, blank=True,
        help_text=gettext_lazy("Location for dataset if different than for project"))

    dset_type = models.CharField(
        blank=True,
        max_length=16,
        help_text=gettext_lazy('Type of dataset: time-series, sounding'))

    # '+' tells django not to create a backwards relation from
    # Variable to Dataset
    variables = models.ManyToManyField(
        Variable, related_name='+')

    # netcdf_time_series, raf_postgres
    # dstype = models.CharField(max_length=64, blank=True)

    def __str__(self):
        # return 'Dataset: %s' % (self.name,)
        return self.name

    def add_platform(self, platform):
        """When one does a dataset.platforms.add(isfs), also do
        project.platforms.add(isfs).
        """
        self.platforms.add(platform)
        platform.projects.add(self.project)

    def get_start_time(self):
        '''
        A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None. If d.tzinfo is
        None, or if d.tzinfo is not None but d.tzinfo.utcoffset(d)
        returns None, d is naive.
        '''

        # _logger.debug("Dataset get_start_time, start_time=%s",
        #    self.start_time.isoformat())
        if self.start_time.tzinfo is None or \
                self.start_time.tzinfo.utcoffset(self.start_time) is None:
            self.start_time = pytz.utc.localize(self.start_time)
            _logger.debug(
                "Dataset localized start_time: %s",
                self.start_time.isoformat())

        return self.start_time

    def get_end_time(self):
        """
        A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None. If d.tzinfo is None,
        or if d.tzinfo is not None but d.tzinfo.utcoffset(d) returns None,
        d is naive.
        """

        # _logger.debug("Dataset get_end_time, end_time=%s",
        #       self.end_time.isoformat())
        if self.end_time.tzinfo is None or \
                self.end_time.tzinfo.utcoffset(self.end_time) is None:
            self.end_time = pytz.utc.localize(self.end_time)
            _logger.debug(
                "Dataset localized end_time: %s",
                self.end_time.isoformat())

        return self.end_time

    def isfs_tabs(self, variables):
        """Create a tabs dictionary for ISFS variables

        Args:
            variables: a django.forms.forms.BoundField, such as
            from form['variables'], where form is an instance
            of ncharts.forms.DataSelectionForm, which has a
            class member named variables of type
            forms.MultipleChoiceField. The variables have been
            alphabetically sorted prior to this call.
        """


        sitetabs = OrderedDict()

        dsetvars = self.get_variables()

        sites = []

        if self.get_station_names():
            sites.append("stations")

        sites.extend(sorted(self.get_sites().keys()))

        for site in sites:
            tabs = deepcopy(ISFS_TABS)
            sitetabs[site] = tabs

            if site == "stations":
                # loop over variables, checking for dataset variables
                # without a site name
                tabvars = [var for var in variables \
                    if not 'site' in dsetvars[var.choice_label]]
            else:
                # loop over variables with site name==site
                tabvars = [var for var in variables \
                    if 'site' in dsetvars[var.choice_label] and \
                        dsetvars[var.choice_label]['site'] == site]

            for var in iter(tabvars):
                vname = var.choice_label.split(".", 1)[0]
                # higher moments have tic marks to indicate a deviation:
                # e.g.   w'h2o'.3m is a covariance between w and h2o
                quote_num = vname.count("'")
                if quote_num == 0:
                    match = False
                    for tname, tvars in ISFS_VARIABLE_TYPES.items():
                        if vname in tvars:
                            # print("appending %s to %s for site %s" %
                            #         (var.choice_label, tname, site))
                            tabs[tname]["variables"].append(var)
                            match = True
                            break
                    if not match:
                        tabs["Other"]["variables"].append(var)
                elif quote_num == 2:
                    tabs["2ndMoment"]["variables"].append(var)
                elif quote_num == 3:
                    tabs["3rdMoment"]["variables"].append(var)
                elif quote_num == 4:
                    tabs["4thMoment"]["variables"].append(var)
                else:
                    tabs["Other"]["variables"].append(var)

            # Remove empty tabs. Keep original order
            for key, value in tabs.copy().items():
                if not value["variables"]:
                    tabs.pop(key)

        return sitetabs

    def make_tabs(self, variables):

        """Select the correct tabbing method for the corresponding platform.
            If the dataset if of ISFS platform, the isfs_tabs method is used.
            Otherwise, the alphabetic_tabs method is used.

        """

        is_isfs = False

        for plat in self.platforms.all():
            if plat.name == "ISFS":
                is_isfs = True

        if is_isfs:
            return self.isfs_tabs(variables)
        return alphabetic_tabs(variables)

class FileDataset(Dataset):
    """A Dataset consisting of a set of similarly named files.

    """

    directory = models.CharField(
        max_length=256,
        help_text=gettext_lazy('Path to the directory containing the files for this dataset'))

    # format of file names, often containing timedate descriptors: %Y etc
    filenames = models.CharField(
        max_length=256,
        help_text=gettext_lazy('Format of file names, often containing ' \
            'timedate descriptors such as %Y'))

    def get_fileset(self):
        """Return a fileset.Fileset corresponding to this
        FileDataset.
        """
        return fileset.Fileset(
            os.path.join(self.directory, self.filenames))

    def get_netcdf_dataset(self):
        """Return the netcdf.NetCDFDataset corresponding to this
        FileDataset.
        """
        return netcdf.NetCDFDataset(
            os.path.join(self.directory, self.filenames),
            self.get_start_time(), self.get_end_time())

    def get_variables(self):
        """Return the time series variable names of this dataset.

        Raises:
            exception.NoDataException
        """

        ncdset = self.get_netcdf_dataset()
        ncvars = ncdset.get_variables()

        if not self.variables.values():
            return ncvars

        # If variables exist in this model, then only provide
        # those variables to the user, not the complete set from
        # the NetCDF dataset.  Use the units and long_name attributes
        # from the model, rather than the dataset. This overcomes
        # issues with the weather station NetCDF files.
        res = {}
        for var in self.variables.all():
            if var.name in ncvars:
                res[var.name] = ncvars[var.name]
            else:
                res[var.name] = {}
            res[var.name]["units"] = var.units
            res[var.name]["long_name"] = var.long_name
        return res

    def get_station_names(self):
        """Return list of station names.

        Raises:
            exception.NoDataException
        """

        ncdset = self.get_netcdf_dataset()

        return ncdset.get_station_names()

    def get_sites(self):
        """Return dictionary of site long names by the site short names.

        Raises:
            exception.NoDataException
        """

        ncdset = self.get_netcdf_dataset()

        return ncdset.get_sites()

    def get_series_tuples(
            self,
            series_name_fmt="",
            start_time=pytz.utc.localize(datetime.datetime.min),
            end_time=pytz.utc.localize(datetime.datetime.max)):
        """Get the names of the series between the start and end times.
        """
        if self.dset_type != "sounding":
            return []

        files = self.get_fileset().scan(start_time, end_time)

        # series names, formatted from the time of the file.
        # The scan function returns the file previous to start_time.
        # Remove that.
        return [(f.time.strftime(series_name_fmt), f.time.timestamp()) for f in files \
                if f.time >= start_time]

    def get_series_names(
            self,
            series_name_fmt="",
            start_time=pytz.utc.localize(datetime.datetime.min),
            end_time=pytz.utc.localize(datetime.datetime.max)):
        """Get the names of the series between the start and end times.
        """
        if self.dset_type != "sounding":
            return []

        files = self.get_fileset().scan(start_time, end_time)

        # series names, formatted from the time of the file.
        # The scan function returns the file previous to start_time.
        # Remove that.
        return [f.time.strftime(series_name_fmt) for f in files \
                if f.time >= start_time]

class DBDataset(Dataset):
    """A Dataset whose contents are in a database.

    """

    dbname = models.CharField(
        max_length=128,
        help_text=gettext_lazy('Database name'))

    host = models.CharField(
        max_length=128,
        help_text=gettext_lazy('Database host'))

    user = models.CharField(
        max_length=128,
        help_text=gettext_lazy('Database user'))

    password = models.CharField(
        max_length=128,
        help_text=gettext_lazy('Database password'))

    port = models.IntegerField(
        default=5432,
        help_text=gettext_lazy('Database port number, defaults to 5432'))

    table = models.CharField(
        max_length=128,
        help_text=gettext_lazy('Database table name'))


    def get_connection(self):
        """Return a database connection for this DBDataset.

        Raises:
            exception.NoDataException
        """

        return raf_database.RAFDatabase(
            database=self.dbname,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password)

    def get_variables(self):
        """Return the time series variables in this DBDataset.

        Raises:
            exception.NoDataException
        """
        return self.get_connection().get_variables()

    def get_station_names(self):
        return list()

    def get_sites(self):
        return {}

    def get_start_time(self):
        """
        Raises:
            exception.NoDataException
        """
        return self.get_connection().get_start_time()

def validate_positive(value):
    """Validator."""
    if value <= 0:
        raise dj_exc.ValidationError('%s is not greater than zero' % value)

class VariableTimes(models.Model):
    """Times of data sent to a client.

    """

    # blank=False means it is required
    name = models.CharField(max_length=64, blank=False)

    last_ok = models.IntegerField(blank=False)

    last = models.IntegerField(blank=False)


class ClientState(models.Model):
    """Current state of an nchart client.

    The automatic primary key 'id' of an instance of this model
    is stored in the user's session by project and dataset name,
    and so when a user returns to view this dataset, their
    previous state is provided.
    """

    variables = models.TextField(blank=True)  # list of variables, stringified by json

    # Variable on sounding Y axis
    yvariable = models.TextField(blank=True)

    # The selected Dataset. Dataset is a base class for several
    # types of Datasets. Since it is used here as a ForeignKey,
    # it cannot be abstract.
    # related_name='+' tells django not to create a backwards relation
    # from Dataset to ClientState, which we don't need.
    # on_delete=CASCADE (default): when the Dataset is deleted all related
    # ClientStates are deleted too, but there shouldn't be any
    # related ClientStates, due to related_name='+'.
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.DO_NOTHING,
        related_name='+')

    timezone = TimeZoneField(blank=False)

    start_time = models.DateTimeField()

    time_length = models.FloatField(
        blank=False, validators=[validate_positive],
        default=datetime.timedelta(days=1).total_seconds())

    track_real_time = models.BooleanField(default=False)

    data_times = models.ManyToManyField(
        VariableTimes,
        blank=True,
        related_name='+')

    # list of sounding series, stringified by json
    soundings = models.TextField(blank=True)

    # station indices, -1: null station, otherwise non-negative number
    # stations = models.IntegerField(null=True)
    stations = models.CharField(blank=True, default="", max_length=1024, \
        validators=[validate_comma_separated_integer_list])

    def __str__(self):
        return 'ClientState for dataset: %s' % (self.dataset.name)

    def clean(self):
        if self.start_time < self.dataset.get_start_time():
            raise dj_exc.ValidationError(
                "start_time is earlier than dataset.start_time")
        # if self.end_time > self.dataset.end_time:
        #     raise dj_exc.ValidationError(
        #       "end_time is earlier than dataset.end_time")
        # if self.start_time >= self.end_time:
        #     raise dj_exc.ValidationError(
        #       "start_time is not earlier than end_time")

        if self.time_length <= 0:
            raise dj_exc.ValidationError("time_length is not positive")

    @transaction.atomic
    def save_data_times(self, vname, time_last_ok, time_last):
        """Save the times associated with the last chunk of data sent to
        this client.

        Under stress testing of ncharts with a security scanner
        saw the MultipleObjectsReturned exception in the get().
        Seems like it is due to simultaneous access, so we'll
        try adding transaction.atomic() on the check/update of
        data_times.  Note that apache may run multiple processes
        of ncharts, so thread locking is not sufficient, must use
        database locking.

        For info:
        https://docs.djangoproject.com/en/2.2/topics/db/transactions/
        """
        with transaction.atomic():
            first = True
            varts = self.data_times.filter(name=vname)
            if varts:
                for vart in varts:
                    if first:
                        vart.last_ok = time_last_ok
                        vart.last = time_last
                        vart.save()
                        first = False
                    else:
                        self.data_times.remove(vart)
                        _logger.error("multiple data_times in ClientState for variable %s", vname)
            else:
                vart = VariableTimes.objects.create(
                    name=vname, last_ok=time_last_ok, last=time_last)
                self.data_times.add(vart)

    def get_data_times(self, vname):
        """Fetch the times associated with the last chunk of data sent to this client.
        This is just a reader of data_times, don't think it needs to
        use atomic transactions.
        """
        try:
            vart = self.data_times.get(name=vname)
            return [vart.last_ok, vart.last]
        except VariableTimes.DoesNotExist:
            return [None, None]
        # don't catch VariableTimes.MultipleObjectsReturned,
        # so that it's reported.
