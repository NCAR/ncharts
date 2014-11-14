# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014 Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

import json, os

from django.db import models

from ncharts import fileset

class Project(models.Model):
    ''' '''
    name = models.CharField(max_length=64,primary_key=True)

    # To get all projects:  Project.objects.all()

    # To find all platforms of a project:
    # Platform.objects.filter(projects__name__exact='METCRAXII')
    # So we don't need this:
    # platforms = models.ManyToManyField('ncharts.Platform')

    # To find all datasets of a project:
    # Dataset.objects.filter(project__name__exact='METCRAXII')
    # So, you don't need this:
    # datasets = models.ManyToManyField('ncharts.Dataset',related_name='datasets')

    def __str__(self):
        return 'Project: %s' % self.name

class Platform(models.Model):
    ''' '''
    name = models.CharField(max_length=64,primary_key=True)

    # To get all platforms:  Platform.objects.all()

    projects = models.ManyToManyField(Project)

    def __str__(self):
        return 'Platform: %s' % self.name

class Variable(models.Model):
    name = models.CharField(max_length=64)
    units = models.CharField(max_length=64)
    long_name = models.CharField(max_length=256)

class Dataset(models.Model):
    ''' '''
    name = models.CharField(max_length=256)

    # To find all datasets of a project:
    # Dataset.objects.filter(project__name__exact='METCRAXII')
    project = models.ForeignKey(Project)

    # To find all datasets of a platform:
    # Dataset.objects.filter(platforms__name__exact="ISFS")
    platforms = models.ManyToManyField(Platform)

    # To find all datasets of a project and platform:
    # Dataset.objects.filter(platforms__name__exact=platform_name).filter(project__name__exact=project_name)

    location = models.CharField(max_length=256)

    timezone = models.CharField(max_length=64)

    directory = models.CharField(max_length=256)

    filenames = models.CharField(max_length=256)

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    variables = models.ManyToManyField(Variable,related_name='dataset+')

    def __str__(self):
        return 'Dataset: %s of %s' % (self.name,self.project)

    def add_platform(self,platform):
        ''' when one does a dataset.platforms.add(isfs), also do
            project.platforms.add(isfs)
            problem is, doesn't work '''
        self.platforms.add(platform)
        platform.projects.add(self.project)

    def get_fileset(self):
        return fileset.Fileset.get(os.path.join(self.directory,self.filenames))

    def get_variables(self):
        if len(self.variables.values()) > 0:
            res = {}
            for v in self.variables.all():
                res[v.name] = {"units": v.units, "long_name": v.long_name}
            return res
        return self.get_fileset().get_variables(self.start_time, self.end_time)

    # dataset.variables does not exist:
    # based on latest modification time of files or dataset could specify a
    # variable rescan interval:
    #   parse start times from filenames in directory
    #   extract variables:
    #       read every Nth file
    # methods called by view:
    #   getVariables(time period)
    #   setStations(), setHeights(), getTimeZone()
    #   getData(time period)

    # don't add __init__ method, instead add @classmethod create() or a
    # custom Manager.
    # See https://docs.djangoproject.com/en/dev/ref/models/instances/

    # For instance variables, just set them in instance methods.


class UserSelection(models.Model):
    ''' '''

    variables = models.TextField()  # list of variables, stringified by json

    dataset = models.ForeignKey(Dataset,related_name='+')

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    def __str__(self):
        return 'UserSelection for dataset: %s' % (self.dataset.name)

    def clean(self):
        print('UserSelection clean')
        if self.start_time < self.dataset.start_time:
            raise ValidationError("start_time is earlier than dataset.start_time")
        if self.end_time > self.dataset.end_time:
            raise ValidationError("end_time is earlier than dataset.end_time")
        if self.start_time >= self.end_time:
            raise ValidationError("start_time is not earlier than end_time")

