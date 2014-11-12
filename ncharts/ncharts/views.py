# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014 Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from django.shortcuts import render, get_object_or_404
# from django.views.generic.base import TemplateView
# from django.views.generic.edit import FormView
from django.views.generic.edit import View
from django.utils.safestring import mark_safe

from ncharts.models import Root, Project, Platform, Dataset, UserSelection
from ncharts.forms import DatasetSelectionForm
from ncharts import netcdf

import json
import numpy
# import simplejson

from pytz import timezone


def index(request):
    return HttpResponse("Hello world, ncharts index")

def projects(request):
    ''' request for list of projects '''

    # get_object_or_404(name='projects')
    # get_list_or_404(name='projects') uses filter()
    root = Root.objects.get(name='projects')

    projects = root.project_set.all()
    print('projects len=%d' % len(projects))

    context = { 'projects': projects }
    return render(request,'ncharts/projects.html',context)

def project(request,project_name):
    ''' request for list of platforms and datasets of a project'''
    try:
        project = Project.objects.get(name=project_name)
        print('project.name=' + str(project))

        datasets = project.dataset_set.all()

        platforms = Platform.objects.filter(projects__name__exact=project_name)

        context = {
            'project': project,
            'platforms': platforms,
            'datasets': datasets }
        return render(request,'ncharts/project.html',context)
    except Project.DoesNotExist:
        raise Http404

def platforms(request):
    ''' request for list of platforms '''

    root = Root.objects.get(name='platforms')

    platforms = root.platform_set.all()
    print('platforms len=%d'  % len(platforms))

    context = { 'platforms': platforms }
    return render(request,'ncharts/platforms.html',context)

def platform(request,platform_name):
    ''' request for list of projects related to a platform'''
    try:
        platform = Platform.objects.get(name=platform_name)
        projects = platform.projects.all()
        print('projects len=%d' % len(projects))

        context = {
            'platform': platform,
            'projects': projects,
            }
        return render(request,'ncharts/platform.html',context)
    except (Project.DoesNotExist, Platform.DoesNotExist):
        raise Http404

def platformProject(request,platform_name,project_name):
    ''' request for list of dataset related to a project and platform'''
    try:

        platform = Platform.objects.get(name=platform_name)
        project = Project.objects.get(name=project_name)

        datasets = Dataset.objects.filter(project__name__exact=project_name).filter(platforms__name__exact=platform_name)

        print('datasets len=%d' % len(datasets))

        context = {
            'project': project,
            'platform': platform,
            'datasets': datasets,
            }
        return render(request,'ncharts/platformProject.html',context)
    except (Project.DoesNotExist, Platform.DoesNotExist):
        raise Http404

class MyJSONEncoder(json.JSONEncoder):
    '''
    A JSON encoder for numpy.ndarray, which also uses
    float(format(obj,'.5g')) on each element to reduce
    the number of significant digits.
    Because converting to ascii and back isn't slow
    enough, we do it twice :-).

    The only other method found on the web to reduce the digits
    is to use an expression like
        round(v,-int(floor(log10(abs(v))+n)))
    where you also have to treat 0 specially. That still might
    be faster than
        float(format(v,'.5g'))
    '''
    def default(self,obj):
        if isinstance(obj,numpy.ndarray):
            if len(obj.shape) > 1:
                # this should reduce the rank by one
                return [v for v in obj[:]]
            else:
                return [float(format(v,'.5g')) for v in obj]
        else:
            return json.JSONEncoder.default(self,obj)

class DatasetView(View):
    ''' '''
    template_name = 'ncharts/dataset.html'
    # form_class = DatasetSelectionForm
    # model = UserSelection
    # fields = ['variables']

    def get(self, request, *args, project_name, dataset_name, **kwargs):
        '''
        print('DatasetView get, type(self)=',type(self))
        print('DatasetView get, dir(self)=',dir(self))
        print('DatasetView get, len(args)=',len(args))
        print('DatasetView get, len(kwargs)=',len(kwargs))
        print('DatasetView get, project_name=',project_name)
        print('DatasetView get, dataset_name=',dataset_name)
        print('DatasetView get, request.session.keys=',
                ['%s' % k for k in request.session.keys()])

        # somehow self.kwargs is set here
        print('DatasetView get, self.kwargs.keys=',
                ['%s' % k for k in self.kwargs.keys()])
        print('DatasetView get, kwargs.keys=',
                ['%s' % k for k in kwargs.keys()])
        '''

        project = Project.objects.get(name=project_name)
        dataset = project.dataset_set.get(name=dataset_name)

        if 'request_id' not in request.session or not request.session['request_id']:
            print('DatasetView get, dataset.variables=',dataset.variables)
            # Initial user selection times need more thought:
            #   real-time project (end_time near now):
            #       start_time, end_time a day at end of dataset
            #   not real-time project
            #       start_time, end_time a day at beginning of dataset
            usersel = UserSelection.objects.create(
                    dataset=dataset,
                    start_time=dataset.start_time,
                    end_time=dataset.end_time,
                    )
            request.session['request_id'] = usersel.id
        else:
            # print("request.session['request_id']=",request.session['request_id'])
            usersel = UserSelection.objects.get(id=request.session['request_id'])

        # print('DatasetView get, dir(usersel)=', dir(usersel))
        print('DatasetView get, dir(usersel.variables)=', dir(usersel.variables))

        # variables selected previously by user
        if usersel.variables:
            print('DatasetView get, usersel.variables=', usersel.variables)
            svars = json.loads(usersel.variables)
        else:
            svars = []

        form = DatasetSelectionForm(dataset=dataset,selected=svars,
                start_time=usersel.start_time,end_time=usersel.end_time)

        '''
        print('DatasetView get, dir(form)=', dir(form))
        print('DatasetView get, dir(form.fields.keys())=',
                ['%s' % k for k in form.fields.keys()])
        print('DatasetView get, type(form.fields[variables]=',
            type(form.fields['variables']))
        print('DatasetView get, type(form.fields[variables].widget)=',
            type(form.fields['variables'].widget))
        print('DatasetView get, form.fields[variables].widget.choices=',
            form.fields['variables'].widget.choices)
        print('DatasetView get, type(form.fields[variables].widget_attrs)=',
            type(form.fields['variables'].widget_attrs))
        
        attrs = form.fields['variables'].widget_attrs(form.fields['variables'].widget)
        print('DatasetView get, type(attrs)=',type(attrs))

        print('DatasetView get, attrs keys=',
                ['%s' % k for k in attrs.keys()])

        print('DatasetView get, dir(form.fields[variables])=',
                dir(form.fields['variables']))

        # form.fields['variables'].choices = tuple( (usersel.variables[k],k) for k in usersel.variables.all() )

        # return render(request,self.template_name, { 'form': form, 'usersel': usersel })
        '''
        return render(request,self.template_name, { 'form': form , 'dataset': dataset})

    def post(self, request, *args, project_name, dataset_name, **kwargs):
        '''
        print('DatasetView post')
        print('DatasetView post, self.kwargs.keys=',
                ['%s' % k for k in self.kwargs.keys()])
        print('DatasetView post, request.session.keys=',
                ['%s' % k for k in request.session.keys()])

        # request.POST is a QueryDict object
        print('DatasetView dir(request.POST)=',
                dir(request.POST))
        print('DatasetView POST keys=',
                ['%s' % k for k in request.POST.keys()])
        if 'variables' in request.POST.keys():
            print('DatasetView POST type(variables)=',
                    type(request.POST['variables']))
            print('DatasetView POST len(variables)=',
                    len(request.POST['variables']))
            print('DatasetView POST getlist variables=',
                    ['%s' % v for v in request.POST.getlist('variables')])

        if 'start_time' in request.POST.keys():
            print('DatasetView POST.values start_time =',
                    request.POST['start_time'])

        '''
        usersel = UserSelection.objects.get(id=request.session['request_id'])

        '''
        if 'variables' in request.POST:
            print('DatasetView POST["variables"]=',
                    ['%s' % type(v) for v in request.POST['variables']])
            print('DatasetView POST["variables"]=',
                    ['%s' % v for v in request.POST['variables']])
            for var in dataset.variables.all():
                usersel.variables.add(var)
        '''

        # project = Project.objects.get(name=project_name)
        dataset = usersel.dataset

        # vars = [ v.name for v in dataset.variables.all() ]
        form = DatasetSelectionForm(request.POST,dataset=dataset)

        if not form.is_valid():
            print('form ain\'t valid!')
            return render(request,self.template_name, { 'form': form,
                'dataset': dataset})

        # validated data is in form.cleaned_data
        '''
        print('DatasetView post, form.cleaned_data.keys=',
                ['%s' % k for k in form.cleaned_data.keys()])
        print('DatasetView post, type(form.cleaned_data[variables])=',
                type(form.cleaned_data['variables']))
        '''

        svars = form.cleaned_data['variables']

        '''
        print('svars=',svars)
        '''
        usersel.variables = json.dumps(svars)
        usersel.start_time = form.cleaned_data['start_time']
        usersel.end_time = form.cleaned_data['end_time']
        usersel.save()

        # files from a valid form will always have len > 0.
        # See the DatasetSelectionForm clean method.
        files = form.get_files()

        ncdset = netcdf.NetCDFDataset(files)

        variables = { k:ncdset.variables[k] for k in svars }

        ncdata = ncdset.read(svars,start_time=form.cleaned_data['start_time'],
                end_time=form.cleaned_data['end_time'])

        # As an easy compression, subtract first time from all times,
        # reducing the number of characters sent.
        time0 = 0
        if len(ncdata['time']) > 0:
            time0 = ncdata['time'][0].timestamp()
        time = json.dumps([x.timestamp() - time0 for x in ncdata['time']])

        data = json.dumps(ncdata['data'],cls=MyJSONEncoder)

        return render(request,self.template_name, { 'form': form,
            'dataset': dataset, 'plot_type': 'time-series',
            'variables': variables, 'time0': time0, 'time': mark_safe(time),
            'data': mark_safe(data) })

def dataset(request,project_name,dataset_name):
    try:
        project = Project.objects.get(name=project_name)
        dataset = project.dataset_set.get(name=dataset_name)
        context = {
            'project': project,
            'dataset': dataset,
            }
        return render(request,'ncharts/dataset.html',context)
    except (Project.DoesNotExist, Dataset.DoesNotExist):
        raise Http404

