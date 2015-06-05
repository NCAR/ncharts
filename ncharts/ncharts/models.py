# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set tabstop=8 shiftwidth=4 softtabstop=4 expandtab:

"""Models used by ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

import os, pytz, logging

from django.db import models

from ncharts import netcdf

from django.core import exceptions as dj_exc

import datetime

from timezone_field import TimeZoneField

_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

class TimeZone(models.Model):
    """ """
    tz = TimeZoneField(default=pytz.utc, primary_key=True)

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

    timezones = models.ManyToManyField(
        TimeZone,
        blank=True,
        related_name='+',
        help_text='Supported timezones for plotting data of this project')

    def __str__(self):
        return 'Project: %s' % self.name

class Platform(models.Model):
    """An observing platform with a unique name, deployed on one or more
    projects.

    To get all platforms:
        Platform.objects.all()
    """
    name = models.CharField(max_length=64, primary_key=True)

    # This adds a platform_set attribute to Project.
    projects = models.ManyToManyField(Project)

    def __str__(self):
        return 'Platform: %s' % self.name

class Variable(models.Model):
    """A variable in a dataset, used if the dataset does not have
    sufficient meta-data for its variables.
    """

    name = models.CharField(max_length=64)

    units = models.CharField(max_length=64, blank=True)

    long_name = models.CharField(max_length=256, blank=True)

def validate_timezone_disabled(tzname):
    """Check a timezone string.

    Args:
        tzname: A name of a time zone.
    Raises:
        dj_exc.ValidationError
    """
    try:
        pytz.timezone(tzname)
    except:
        raise dj_exc.ValidationError(
            "%s is not a recognized timezone" % tzname)

class Dataset(models.Model):
    """A dataset, whose name should be unique within a project.

    Tried making this an abstract base class in django.
    From the django doc on abstract base classes of models:
        This model will then not be used to create any database table.
        Instead, when it is used as a base class for other models,
        its fields will be added to those of the child class. It is
        an error to have fields in the abstract base class with the
        same name as those in the child (and Django will raise an exception).

    However, a Dataset is a ForeignKey of a UserSelection, and
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
        max_length=256,
        help_text='The name of a dataset should be unique within a project')

    # This adds a dataset_set attribute to Project
    project = models.ForeignKey(
        Project,
        help_text='A dataset is associated with one project')

    # This adds a dataset_set attribute to Platform
    platforms = models.ManyToManyField(
        Platform,
        help_text='A dataset is associated with one or more platforms')

    timezones = models.ManyToManyField(
        TimeZone,
        help_text='Overrides the timezones of the project')

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    location = models.CharField(
        max_length=256, blank=True,
        help_text="Location for dataset if different than for project")

    # '+' tells django not to create a backwards relation from
    # Variable to Dataset
    variables = models.ManyToManyField(
        Variable, related_name='+')

    # netcdf_time_series, raf_postgres
    # dstype = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return 'Dataset: %s of %s' % (self.name, self.project)

    def add_platform(self, platform):
        """When one does a dataset.platforms.add(isfs), also do
        project.platforms.add(isfs).
        """
        self.platforms.add(platform)
        platform.projects.add(self.project)

    def get_timezone_disabled(self):
        """ self.timezones is a dict object containing tzinfos for named
            timezones
        """

        # TODO: needs a lock
        # print("get_timezone, self.timezone=", self.timezone)
        if not hasattr(self, "timezones"):
            # pylint: disable=attribute-defined-outside-init
            self.timezones = {}

        if hasattr(self.timezones, self.timezone):
            return self.timezones[self.timezone]

        try:
            timezone = pytz.timezone(self.timezone)
            # print("get_timezone, tz=", timezone)
            self.timezones[self.timezone] = timezone
            self.timezones['UTC'] = pytz.utc
        except:
            raise dj_exc.ValidationError(
                "%s is not a recognized timezone" % self.timezone)

        return timezone

    def get_start_time(self):
        '''
        A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None. If d.tzinfo is
        None, or if d.tzinfo is not None but d.tzinfo.utcoffset(d)
        returns None, d is naive.
        '''

        # print("Dataset get_start_time, start_time=",
        #    self.start_time.isoformat())
        if self.start_time.tzinfo == None or \
                self.start_time.tzinfo.utcoffset(self.start_time) == None:
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

        # print("Dataset get_end_time, end_time=", self.end_time.isoformat())
        if self.end_time.tzinfo == None or \
                self.end_time.tzinfo.utcoffset(self.end_time) == None:
            self.end_time = pytz.utc.localize(self.end_time)
            _logger.debug(
                "Dataset localized end_time: %s",
                self.end_time.isoformat())

        return self.end_time

    def get_variables_disabled(self):
        """Get variables in this dataset.

        Method to be implemented in sub-class.

        Returns:
        """
        return []

class FileDataset(Dataset):
    """A Dataset consisting of a set of similarly named files.

    """

    directory = models.CharField(
        max_length=256,
        help_text='Path to the directory containing the files for this dataset')

    # format of file names, often containing timedate descriptors: %Y etc
    filenames = models.CharField(
        max_length=256,
        help_text='Format of file names, often containing timedate '
                  'descriptors such as %Y')

    def get_netcdf_dataset(self):
        """Return the netcdf.NetCDFDataset corresponding to this
        FileDataset.
        """
        return netcdf.NetCDFDataset(
            os.path.join(self.directory, self.filenames))

    def get_variables(self):
        """Return the time series variables in this FileDataset.
        """
        if len(self.variables.values()) > 0:
            res = {}
            for var in self.variables.all():
                res[var.name] = \
                    {"units": var.units, "long_name": var.long_name}
            return res

        ncdset = self.get_netcdf_dataset()

        return ncdset.get_variables(
            self.start_time, self.end_time)


class DBDataset(Dataset):
    """A Dataset whose contents are in a database.

    """

    dbname = models.CharField(
        max_length=128,
        help_text='Database name')

    host = models.CharField(
        max_length=128,
        help_text='Database host')

    user = models.CharField(
        max_length=128,
        help_text='Database user')

    password = models.CharField(
        max_length=128,
        help_text='Database password')

    port = models.IntegerField(
        default=5432,
        help_text='Database port number, defaults to 5432')


    # def get_connection(self):
    #     """Return a connection corresponding to this Database.
    #     """
    #     return DatabaseConnection(self.dbname, self.host,
    #                               self.port, self.user, self.password)

    def get_variables(self):
        """Return the time series variables in this DBDataset.
        """

        # return self.get_connection().get_variables(
        #     self.start_time, self.end_time)
        return []

def validate_positive(value):
    """Validator."""
    if value <= 0:
        raise dj_exc.ValidationError('%s is not greater than zero' % value)

class UserSelection(models.Model):
    """Fields returned from the data selection form.

    The automatic primary key 'id' of an instance of this model
    is stored in the session, and so the previous selection of
    the user is maintained in the database.
    """

    variables = models.TextField()  # list of variables, stringified by json

    # '+' tells django not to create a backwards relation
    # from Dataset to UserSelection
    # This ForeignKey cannot be a Dataset, since it is
    # abstract.
    dataset = models.ForeignKey(Dataset, related_name='+')

    timezone = TimeZoneField(blank=False)

    start_time = models.DateTimeField()

    time_length = models.FloatField(
        blank=False, validators=[validate_positive],
        default=datetime.timedelta(days=1).total_seconds())

    def __str__(self):
        return 'UserSelection for dataset: %s' % (self.dataset.name)

    def clean(self):
        print('UserSelection clean')
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

