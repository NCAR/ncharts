# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014 Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

from django.shortcuts import render, get_object_or_404

from django.http import HttpResponse, Http404

from django.views.generic.edit import View
from django.utils.safestring import mark_safe

from ncharts.models import  Project, Platform, Dataset, UserSelection
from ncharts.forms import DatasetSelectionForm
from ncharts import netcdf, exceptions

import json, numpy, math, logging
from pytz import timezone
from datetime import datetime

logger = logging.getLogger(__name__)

def index(request):
    return HttpResponse("<a href='projects'>projects</a>")

def projects(request):
    ''' request for list of projects '''

    # get_object_or_404(name='projects')
    # get_list_or_404(name='projects') uses filter()
    # root = Root.objects.get(name='projects')
    # projects = root.project_set.all()

    projects = Project.objects.all()

    # print('projects len=%d' % len(projects))

    context = { 'projects': projects }
    return render(request,'ncharts/projects.html',context)

def project(request,project_name):
    ''' request for list of platforms and datasets of a project'''
    try:
        project = Project.objects.get(name=project_name)
        # print('project.name=' + str(project))

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

    # root = Root.objects.get(name='platforms')
    # platforms = root.platform_set.all()

    platforms = Platform.objects.all()

    # print('platforms len=%d'  % len(platforms))

    context = { 'platforms': platforms }
    return render(request,'ncharts/platforms.html',context)

def platform(request,platform_name):
    ''' request for list of projects related to a platform'''
    try:
        platform = Platform.objects.get(name=platform_name)
        projects = platform.projects.all()
        # print('projects len=%d' % len(projects))

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

        # print('datasets len=%d' % len(datasets))

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

    Also generate a None if data is a nan.
    '''
    def default(self,obj):
        def roundcheck(v):
            if math.isnan(v):
                return None
            else:
                return float(format(v,'.5g'))

        # print("type(obj)=",type(obj))
        if isinstance(obj,numpy.ndarray):
            if len(obj.shape) > 1:
                # this should reduce the rank by one
                # print("Encoder, default, len(obj.shape)=",len(obj.shape))
                return [v for v in obj[:]]
            else:
                # print("Encoder, default, len(obj.shape)=",len(obj.shape))
                return [roundcheck(v) for v in obj]
        else:
            return json.JSONEncoder.default(self,obj)

class DatasetView(View):
    ''' '''
    template_name = 'ncharts/dataset.html'
    # form_class = DatasetSelectionForm
    # model = UserSelection
    # fields = ['variables']

    def get(self, request, *args, project_name, dataset_name, **kwargs):

        project = get_object_or_404(Project.objects,name=project_name)
        dataset = get_object_or_404(project.dataset_set,name=dataset_name)
        '''
        try:
            project = Project.objects.get(name=project_name)
            dataset = project.dataset_set.get(name=dataset_name)
        except (Project.DoesNotExist, Dataset.DoesNotExist):
            raise Http404
        '''

        usersel = None
        request_id = None

        if 'request_id' in request.session and request.session['request_id']:
            request_id = request.session['request_id']
            try:
                usersel = UserSelection.objects.get(id=request_id)
            except UserSelection.DoesNotExist:
                pass
        else:
            request.session.set_test_cookie()

        if not usersel:
            # print('DatasetView get, dataset.variables=',dataset.variables)
            # Initial user selection times need more thought:
            #   real-time project (end_time near now):
            #       start_time, end_time a day at end of dataset
            #   not real-time project
            #       start_time, end_time a day at beginning of dataset
            usersel = UserSelection.objects.create(
                    dataset=dataset,
                    start_time=dataset.get_start_time(),
                    end_time=dataset.get_end_time(),
                    )
            request_id = usersel.id
            request.session['request_id'] = request_id
            logger.info("get, new session, request_id=%d, project=%s,dataset=%s",
                    request_id,project_name,dataset_name)

        else:

            if usersel.dataset.pk == dataset.pk:
                logger.info("get, old session, request_id=%d, project=%s,dataset=%s",
                        request_id,project_name,dataset_name)
                # could check that usersel.dataset.name == dataset_name and
                # usersel.dataset.project.name == project_name
                # but I believe that is unnecessary, since the pk members
                # are unique.
            else:
                # User has changed dataset of interest
                logger.info("get, old session, request_id=%d, dataset.pk=%d, old dataset.pk=%d, project=%s, dataset=%s",
                        request_id,dataset.pk,usersel.dataset.pk,
                        project_name,dataset_name)
                usersel.dataset = dataset
                usersel.variables = []
                usersel.start_time = dataset.get_start_time()
                usersel.end_time = dataset.get_end_time()
                usersel.save()

        # print('DatasetView get, dir(usersel)=', dir(usersel))
        # print('DatasetView get, dir(usersel.variables)=', dir(usersel.variables))

        # variables selected previously by user
        if usersel.variables:
            # print('DatasetView get, usersel.variables=', usersel.variables)
            svars = json.loads(usersel.variables)
        else:
            svars = []

        form = DatasetSelectionForm(dataset=dataset,selected=svars,
                start_time=usersel.start_time,end_time=usersel.end_time)

        return render(request,self.template_name, { 'form': form , 'dataset': dataset})

    def post(self, request, *args, project_name, dataset_name, **kwargs):

        if not request.session.test_cookie_worked():
            # The django server is backed by memcached, so I believe this won't happen when
            # the django server is restarted, but will happen if the memcached daemon
            # is restarted.
            logger.error("session cookie check failed. Either this server was restarted, or the user needs to enable cookies")
            return HttpResponse("Your cookie is not recognized. Either this server was restarted, or you need to enable cookies in your browser. Then please try again.")

        if 'request_id' not in request.session or not request.session['request_id']:
            # not sure if it is possible for a post to come in without a session id,
            # but we'll redirect them to the get.
            logger.error("post but no request_id, redirecting to get")
            # Uses the name='dataset' in urls.py
            return redirect('dataset', project_name=project_name, dataset_name=dataset_name)

        usersel = get_object_or_404(UserSelection.objects,id=request.session['request_id'])
        dataset = usersel.dataset

        logger.info("post, old session, request_id=%d, project=%s,dataset=%s",
                request.session['request_id'],dataset.project.name,dataset.name)

        # dataset name and project name from URL should agree with
        # session values. There are probably situations where that may
        # be violated such as a user re-posting an old form.
        if dataset.name != dataset_name or dataset.project.name != project_name:
            logger.error("post, old session, request_id=%d, project=%s,dataset=%s, url project=%s, dataset=%d",

                request.session['request_id'],dataset.project.name,dataset.name,
                project_name,dataset_name)
            return get(request, *args, project_name=project_name,
                    dataset_name=dataset_name, **kwargs)

        # vars = [ v.name for v in dataset.variables.all() ]

        # page-backward or page-forward in time
        # better to implement a javascript button that manipulates the
        # html field directly
        if 'submit' in request.POST and request.POST['submit'][0:4] == 'page':
            dtz = dataset.get_timezone()
            t1 = dtz.localize(datetime.strptime(request.POST['start_time'],"%Y-%m-%d %H:%M"))
            t2 = dtz.localize(datetime.strptime(request.POST['end_time'],"%Y-%m-%d %H:%M"))

            if request.POST['submit'] == 'page-backward':
                dt = t2 - t1
                t1 -= dt
                t2 -= dt
                # print('paged backward, t1=',t1.isoformat(),', t2=',t2.isoformat())
            elif request.POST['submit'] == 'page-forward':
                dt = t2 - t1
                t1 += dt
                t2 += dt
                # print('paged forward, t1=',t1.isoformat(),', t2=',t2.isoformat())

            postx = request.POST.copy()
            postx['start_time'] = t1.strftime("%Y-%m-%d %H:%M")
            postx['end_time'] = t2.strftime("%Y-%m-%d %H:%M")

            form = DatasetSelectionForm(postx,dataset=dataset)
        else:
            form = DatasetSelectionForm(request.POST,dataset=dataset)

        # print("request.POST=",request.POST)
        if not form.is_valid():
            # print('form ain\'t valid!')
            return render(request,self.template_name, { 'form': form,
                'dataset': dataset})

        svars = form.cleaned_data['variables']

        usersel.variables = json.dumps(svars)
        usersel.start_time = form.cleaned_data['start_time']
        usersel.end_time = form.cleaned_data['end_time']
        usersel.save()

        # files from a valid form will always have len > 0.
        # See the DatasetSelectionForm clean method.
        files = form.get_files()
        # print("view, len(files)=",len(files))

        ncdset = netcdf.NetCDFDataset(files)

        # If variables exists in the dataset, get their
        # attributes there, otherwise from the NetCDF files.
        if len(dataset.variables.all()) > 0:
            variables = { k:{'units': dataset.variables.get(name=k).units,
                'long_name': dataset.variables.get(name=k).long_name }
                    for k in svars }
        else:
            variables = { k:ncdset.variables[k] for k in svars }

        try:
            ncdata = ncdset.read(svars,start_time=form.cleaned_data['start_time'],
                    end_time=form.cleaned_data['end_time'])
        except exceptions.TooMuchDataException as e:
            form.too_much_data(repr(e))
            return render(request,self.template_name, { 'form': form,
                'dataset': dataset})

        # As an easy compression, subtract first time from all times,
        # reducing the number of characters sent.
        time0 = 0
        if len(ncdata['time']) > 0:
            time0 = ncdata['time'][0].timestamp()
        time = json.dumps([x.timestamp() - time0 for x in ncdata['time']])

        def type_by_dimension(d):
            if len(d.shape) == 1:
                return 'time-series'
            elif len(d.shape) == 2:
                return 'heatmap'
            else:
                return 'none'

        plot_types = set()
        for n,v in variables.items():
            pt = type_by_dimension(ncdata['data'][n])
            v['plot_type'] = pt
            plot_types.add(pt)

        data = json.dumps(ncdata['data'],cls=MyJSONEncoder)

        dim2 = json.dumps(ncdata['dim2'],cls=MyJSONEncoder)

        # Create plot groups dictionary, for each
        # group, the variables in the group, their units, long_names, plot_type
        plot_groups = {}

        units = [v['units'] for v in variables.values()]
        # unique units
        uunits = set(units)

        # loop over plot_types
        grpid = 0
        for pt in plot_types:
            # print("pt=",pt)
            # loop over unique units

            # Cannot combine variables with same units on a heatmap
            if pt == 'heatmap':
                for n,val in variables.items():
                    if val['plot_type'] == pt:
                        plot_groups['g{}'.format(grpid)] = {
                            'variables': mark_safe(json.dumps([n])),
                            'units': mark_safe(json.dumps([variables[n]['units']])),
                            'long_names': mark_safe(json.dumps([variables[n]['long_name']])),
                            'plot_type': mark_safe(pt),
                        }
                        grpid += 1
            else:
                for i,u in enumerate(set(units)):
                    uv = [n for n,val in variables.items() if val['plot_type'] == pt and val['units'] == u]
                    # uv is list of variables with units u
                    plot_groups['g{}'.format(grpid)] = {
                        'variables': mark_safe(json.dumps(uv)),
                        'units': mark_safe(json.dumps([variables[v]['units'] for v in uv])),
                        'long_names': mark_safe(json.dumps([variables[v]['long_name'] for v in uv])),
                        'plot_type': mark_safe(pt),
                    }
                    grpid += 1

        return render(request,self.template_name, { 'form': form,
            'dataset': dataset, 'plot_groups': plot_groups,
            'time0': time0, 'time': mark_safe(time),
            'data': mark_safe(data), 'dim2': mark_safe(dim2) })

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

