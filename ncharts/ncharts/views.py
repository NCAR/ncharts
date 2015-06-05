# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Views used by ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

from django.shortcuts import render, get_object_or_404, redirect

from django.http import HttpResponse, Http404

from django.views.generic.edit import View
from django.views.generic import TemplateView
from django.utils.safestring import mark_safe
from django.template import TemplateDoesNotExist

from ncharts import models as nc_models
from ncharts import forms as nc_forms
from ncharts import exceptions as nc_exceptions

import json, math, logging
import numpy as np
import pytz
import datetime

_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

class StaticView(TemplateView):
    """View class for rendering a simple template page.
    """
    def get(self, request, page, *args, **kwargs):
        self.template_name = page
        print("page=", page)
        response = super().get(request, *args, **kwargs)
        try:
            return response.render()
        except TemplateDoesNotExist:
            raise Http404()

def index_unused(request):
    """View function which could be used as a default URL.

    Unused.
    """
    #pylint: disable=unused-argument
    return HttpResponse("<a href='projects'>projects</a>")

def projects(request):
    """View function for a view of a list of projects.
    """

    # get_object_or_404(name='projects')
    # get_list_or_404(name='projects') uses filter()
    # root = Root.objects.get(name='projects')
    # projs = root.project_set.all()

    projs = nc_models.Project.objects.all()

    # print('projs len=%d' % len(projs))

    context = {'projects': projs}
    return render(request, 'ncharts/projects.html', context)

def platforms(request):
    """View function for list of platforms.
    """

    # root = Root.objects.get(name='platforms')
    # plats = root.platform_set.all()

    plats = nc_models.Platform.objects.all()

    # print('plats len=%d'  % len(plats))

    context = {'platforms': plats}
    return render(request, 'ncharts/platforms.html', context)

def projects_platforms(request):
    """View function for a request for a list of projects and platforms.
    """

    # get_object_or_404(name='projects')
    # get_list_or_404(name='projects') uses filter()
    # root = Root.objects.get(name='projects')
    # projs = root.project_set.all()

    projs = nc_models.Project.objects.all()
    plats = nc_models.Platform.objects.all()

    # print('projs len=%d' % len(projs))

    context = {'projects': projs, 'platforms': plats}
    return render(request, 'ncharts/projectsPlatforms.html', context)

def project(request, project_name):
    """View function for list of platforms and datasets of a project.
    """
    try:
        proj = nc_models.Project.objects.get(name=project_name)
        # print('proj.name=' + str(proj))
        dsets = proj.dataset_set.all()
        plats = nc_models.Platform.objects.filter(
            projects__name__exact=project_name)
        context = {'project': proj, 'platforms': plats, 'datasets': dsets}
        return render(request, 'ncharts/project.html', context)
    except nc_models.Project.DoesNotExist:
        raise Http404

def platform(request, platform_name):
    """View function for list of projects related to a platform.
    """
    try:
        plat = nc_models.Platform.objects.get(name=platform_name)
        projs = plat.projects.all()
        # print('projs len=%d' % len(projs))
        context = {'platform': plat, 'projects': projs}
        return render(request, 'ncharts/platform.html', context)
    except (nc_models.Project.DoesNotExist, nc_models.Platform.DoesNotExist):
        raise Http404

def platform_project(request, platform_name, project_name):
    """View function for a list of datasets related to a project and platform.
    """
    try:

        plat = nc_models.Platform.objects.get(name=platform_name)
        proj = nc_models.Project.objects.get(name=project_name)

        dsets = nc_models.Dataset.objects.filter(
            project__name__exact=project_name).filter(
                platforms__name__exact=platform_name)

        # print('dsets len=%d' % len(dsets))

        context = {'project': proj, 'platform': plat, 'datasets': dsets}
        return render(request, 'ncharts/platformProject.html', context)
    except (nc_models.Project.DoesNotExist, nc_models.Platform.DoesNotExist):
        raise Http404

def dataset_unused(request, project_name, dataset_name):
    """Unused.
    """
    try:
        proj = nc_models.Project.objects.get(name=project_name)
        dset = proj.dataset_set.get(name=dataset_name)
        context = {'project': proj, 'dataset': dset}
        return render(request, 'ncharts/dataset.html', context)
    except (nc_models.Project.DoesNotExist, nc_models.Dataset.DoesNotExist):
        raise Http404

class NChartsJSONEncoder(json.JSONEncoder):
    """A JSON encoder for np.ndarray, which reduces the number of
    significant digits.

    This uses float(format(obj,'.5g')) on each element to reduce the
    number of significant digits.

    Because converting to ascii and back isn't slow
    enough, we do it twice :-).

    The only other method found on the web to reduce the digits
    is to use an expression like
        round(v, -int(floor(log10(abs(v))+n)))
    where you also have to treat 0 specially. That still might
    be faster than
        float(format(v, '.5g'))

    Also generate a None if data is a nan.
    """

    def default(self, obj): #pylint: disable=method-hidden
        """Implementation of JSONEncoder default method.

        Return a serializable object from an np.ndarray.
        """

        def roundcheck(val):
            """Round a value to 5 significant digits, returning None for a nan.
            """
            if math.isnan(val):
                return None
            else:
                return float(format(val, '.5g'))

        # print("type(obj)=", type(obj))
        if isinstance(obj, np.ndarray):
            if len(obj.shape) > 1:
                # this should reduce the rank by one
                # print("Encoder, default, len(obj.shape)=", len(obj.shape))
                return [v for v in obj[:]]
            else:
                # print("Encoder, default, len(obj.shape)=", len(obj.shape))
                return [roundcheck(v) for v in obj]
        else:
            return json.JSONEncoder.default(self, obj)

class DatasetView(View):
    """Render a form where the user can choose parameters of dataset.
    """

    template_name = 'ncharts/dataset.html'
    # form_class = nc_forms.DataSelectionForm
    # model = nc_models.UserSelection
    # fields = ['variables']

    def get(self, request, *args, project_name, dataset_name, **kwargs):
        """Respond to a get request where the user has specified a
        project and dataset.

        """

        proj = get_object_or_404(nc_models.Project.objects, name=project_name)
        dset = get_object_or_404(proj.dataset_set, name=dataset_name)

        try:
            dset = dset.filedataset
        except nc_models.FileDataset.DoesNotExist:
            try:
                dset = dset.dbdataset
            except nc_models.DBDataset.DoesNotExist:
                raise Http404

        usersel = None
        request_id = None

        if len(dset.timezones.all()) > 0:
            timezone = dset.timezones.all()[0]
        elif len(dset.project.timezones.all()) > 0:
            timezone = dset.project.timezones.all()[0]
        else:
            _logger.error(
                "dataset %s of project %s has no associated timezone",
                dataset_name, project_name)
            timezone = nc_models.TimeZone.objects.get(tz='UTC')

        if 'request_id' in request.session and request.session['request_id']:
            request_id = request.session['request_id']
            try:
                usersel = nc_models.UserSelection.objects.get(id=request_id)
            except nc_models.UserSelection.DoesNotExist:
                pass
        else:
            request.session.set_test_cookie()

        if not usersel:
            # print('DatasetView get, dset.variables=', dset.variables)
            # Initial user selection times need more thought:
            #   real-time project (end_time near now):
            #       start_time, end_time a day at end of dataset
            #   not real-time project
            #       start_time, end_time a day at beginning of dataset

            tnow = datetime.datetime.now(timezone.tz)
            delta = datetime.timedelta(days=1)
            if dset.get_end_time() > tnow:
                stime = tnow - delta
            else:
                stime = dset.get_start_time()

            usersel = nc_models.UserSelection.objects.create(
                dataset=dset,
                timezone=timezone.tz,
                start_time=stime,
                time_length=delta.total_seconds())

            request_id = usersel.id
            request.session['request_id'] = request_id
            _logger.info(
                "get, new session, request_id=%d, project=%s,"
                " dataset=%s", request_id, project_name, dataset_name)

        else:
            if usersel.dataset.pk == dset.pk:
                _logger.info(
                    "get, old session, same dataset, request_id=%d, "
                    "project=%s,dataset=%s",
                    request_id, project_name, dataset_name)
                # could check that usersel.dataset.name == dataset_name and
                # usersel.dataset.project.name == project_name
                # but I believe that is unnecessary, since the pk members
                # are unique.
            else:
                # User has changed dataset of interest
                _logger.info(
                    "get, old session, new dataset, request_id=%d, "
                    "dataset.pk=%d, old dataset.pk=%d, project=%s, dataset=%s",
                    request_id, dset.pk, usersel.dataset.pk,
                    project_name, dataset_name)

                usersel.dataset = dset
                usersel.timezone = timezone.tz
                usersel.variables = []

                tnow = datetime.datetime.now(timezone.tz)
                delta = datetime.timedelta(days=1)
                if dset.get_end_time() > tnow:
                    stime = tnow - delta
                else:
                    stime = dset.get_start_time()

                usersel.start_time = stime
                usersel.time_length = delta.total_seconds()
                usersel.save()

        # print('DatasetView get, dir(usersel)=', dir(usersel))
        # print('DatasetView get, dir(usersel.variables)=',
        # dir(usersel.variables))

        # variables selected previously by user
        if usersel.variables:
            # print('DatasetView get, usersel.variables=', usersel.variables)
            svars = json.loads(usersel.variables)
        else:
            svars = []

        tlen = usersel.time_length

        if tlen >= datetime.timedelta(days=1).total_seconds():
            tunits = 'day'
            tlen /= 86400
        elif tlen >= datetime.timedelta(hours=1).total_seconds():
            tunits = 'hour'
            tlen /= 3600
        elif tlen >= datetime.timedelta(minutes=1).total_seconds():
            tunits = 'minute'
            tlen /= 60
        else:
            tunits = 'second'

        if tlen in nc_forms.TIME_LEN_CHOICES:
            tother = 0
        else:
            tlen = 0
            tother = tlen

        tlen = '{:f}'.format(tlen)


        form = nc_forms.DataSelectionForm(
            initial={
                'variables': svars,
                'timezone': timezone.tz,
                'start_time': datetime.datetime.fromtimestamp(
                    usersel.start_time.timestamp(), tz=timezone.tz),
                'time_length_units': tunits,
                'time_length': tlen
            },
            dataset=dset)

        return render(request, self.template_name,
                      {'form': form, 'dataset': dset})

    def post(self, request, *args, project_name, dataset_name, **kwargs):
        """Respond to a post request where the user has sent back a form.

        Using the requested parameters in the form, such as start and end times
        and a list of variables, the dataset can be read, and the contents
        sent back to the user.
        """

        if not request.session.test_cookie_worked():
            # The django server is backed by memcached, so I believe
            # this won't happen when the django server is restarted,
            # but will happen if the memcached daemon is restarted.
            _logger.error(
                "session cookie check failed. Either this server "
                "was restarted, or the user needs to enable cookies")

            # redirect so that next request is a get
            # Uses the name='dataset' in urls.py
            return redirect(
                'ncharts:dataset', project_name=project_name,
                dataset_name=dataset_name)

            # return HttpResponse("Your cookie is not recognized.
            # Either this server was restarted, or you need to
            # enable cookies in your browser. Then please try again.")

        if 'request_id' not in request.session or \
                not request.session['request_id']:
            # not sure if it is possible for a post to come in
            # without a session id, but we'll redirect them to the get.
            _logger.error("post but no request_id, redirecting to get")
            # Uses the name='dataset' in urls.py
            return redirect(
                'ncharts:dataset', project_name=project_name,
                dataset_name=dataset_name)

        usersel = get_object_or_404(
            nc_models.UserSelection.objects,
            id=request.session['request_id'])
        dset = usersel.dataset
        try:
            dset = dset.filedataset
        except nc_models.FileDataset.DoesNotExist as exc:
            try:
                dset = dset.dbdataset
            except nc_models.DBDataset.DoesNotExist as exc:
                raise Http404


        _logger.info(
            "post, old session, request_id=%d, project=%s,dataset=%s",
            request.session['request_id'], dset.project.name, dset.name)

        # dataset name and project name from URL should agree with
        # session values. There are probably situations where that may
        # be violated such as a user re-posting an old form.
        if dset.name != dataset_name or dset.project.name != project_name:
            _logger.error(
                "post, old session, request_id=%d, project=%s, dataset=%s, "
                "url project=%s, dataset=%d",
                request.session['request_id'],
                dset.project.name, dset.name,
                project_name, dataset_name)

            return self.get(request, *args, project_name=project_name,
                            dataset_name=dataset_name, **kwargs)

        # vars = [ v.name for v in dset.variables.all() ]

        # page-backward or page-forward in time
        # better to implement a javascript button that manipulates the
        # html field directly
        '''
        print("POST, time inputs=",
            request.POST['time_length_0'],
            request.POST['time_length_units'])
        '''

        if 'submit' in request.POST and request.POST['submit'][0:4] == 'page':

            timezone = nc_models.TimeZone.objects.get(
                tz=request.POST['timezone']).tz

            stime = timezone.localize(
                datetime.datetime.strptime(
                    request.POST['start_time'], "%Y-%m-%d %H:%M"))

            delt = nc_forms.get_time_length(
                request.POST['time_length_0'],
                request.POST['time_length_units'])

            if request.POST['submit'] == 'page-backward':
                stime = stime - delt
            elif request.POST['submit'] == 'page-forward':
                stime = stime + delt

            postx = request.POST.copy()
            postx['start_time'] = stime.strftime("%Y-%m-%d %H:%M")
            form = nc_forms.DataSelectionForm(postx, dataset=dset)
        else:
            form = nc_forms.DataSelectionForm(request.POST, dataset=dset)

        # print("request.POST=", request.POST)
        if not form.is_valid():
            # print('form ain\'t valid!')
            return render(request, self.template_name,
                          {'form': form, 'dataset': dset})

        # Save the user selection from the form
        svars = form.cleaned_data['variables']

        stime = form.cleaned_data['start_time']
        delt = form.get_cleaned_time_length()
        etime = stime + delt
        usersel.variables = json.dumps(svars)
        usersel.start_time = stime
        usersel.timezone = form.cleaned_data['timezone']
        usersel.time_length = delt.total_seconds()
        usersel.save()

        # filedset = None
        # try:
        #     filedset = dset.filedataset
        # except nc_models.FileDataset.DoesNotExist as exc:
        #     raise Http404

        if isinstance(dset, nc_models.FileDataset):
            # print("view, len(files)=", len(files))
            ncdset = dset.get_netcdf_dataset()

            # a variable can be in a dataset, but not in a certain set of files.
            # savail: selected and available variables, using set intersection
            dsvars = ncdset.get_variables(start_time=stime, end_time=etime)

        elif isinstance(dset, nc_models.DBDataset):
            dbcon = dset.get_connection()
            dsvars = dbcon.get_variables(start_time=stime, end_time=etime)

        savail = list(set(svars) & set(dsvars.keys()))

        if len(savail) == 0:
            exc = nc_exceptions.NoDataException(
                "variables {} not found in dataset".format(svars))
            _logger.warn(repr(exc))
            form.no_data(repr(exc))
            return render(request, self.template_name,
                          {'form': form, 'dataset': dset})

        # If variables exists in the dataset, get their
        # attributes there, otherwise from the actual dataset.
        if len(dset.variables.all()) > 0:
            variables = {
                k:{'units': dset.variables.get(name=k).units,
                   'long_name': dset.variables.get(name=k).long_name}
                for k in savail}
        else:
            variables = {k:dsvars[k] for k in savail}

        if isinstance(dset, nc_models.FileDataset):
            try:
                ncdata = ncdset.read_time_series(
                    savail, start_time=stime, end_time=etime)
            except FileNotFoundError:
                _logger.error("%s, %s: %s", project_name, dataset_name, exc)
                form.no_data(repr(exc))
                return render(request, self.template_name,
                              {'form': form, 'dataset': dset})
            except PermissionError:
                _logger.error("%s, %s: %s", project_name, dataset_name, exc)
                form.data_not_available(repr(exc))
                return render(request, self.template_name,
                              {'form': form, 'dataset': dset})
            except nc_exceptions.TooMuchDataException as exc:
                _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
                form.too_much_data(repr(exc))
                return render(request, self.template_name,
                              {'form': form, 'dataset': dset})
            except nc_exceptions.NoDataException as exc:
                _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
                form.no_data(repr(exc))
                return render(request, self.template_name,
                              {'form': form, 'dataset': dset})
        else:
            try:
                ncdata = dbcon.read_time_series(
                    savail, start_time=stime, end_time=etime)
            except nc_exceptions.TooMuchDataException as exc:
                _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
                form.too_much_data(repr(exc))
                return render(request, self.template_name,
                              {'form': form, 'dataset': dset})
            except nc_exceptions.NoDataException as exc:
                _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
                form.no_data(repr(exc))
                return render(request, self.template_name,
                              {'form': form, 'dataset': dset})


        # As an easy compression, subtract first time from all times,
        # reducing the number of characters sent.
        time0 = 0
        if len(ncdata['time']) > 0:
            time0 = ncdata['time'][0].timestamp()
        time = json.dumps([x.timestamp() - time0 for x in ncdata['time']])

        def type_by_dimension(dim):
            """Crude function to return a plot type, given a dimension.
            """
            if len(dim.shape) == 1:
                return 'time-series'
            elif len(dim.shape) == 2:
                return 'heatmap'
            else:
                return 'none'

        plot_types = set()
        for vname, var in variables.items():
            ptype = type_by_dimension(ncdata['data'][vname])
            var['plot_type'] = ptype
            plot_types.add(ptype)

        data = json.dumps(ncdata['data'], cls=NChartsJSONEncoder)

        dim2 = json.dumps(ncdata['dim2'], cls=NChartsJSONEncoder)

        # Create plot groups dictionary, for each
        # group, the variables in the group, their units, long_names, plot_type
        plot_groups = {}

        units = [v['units'] for v in variables.values()]

        # loop over plot_types
        grpid = 0
        for ptype in plot_types:
            # print("ptype=", ptype)
            # loop over unique units

            # Cannot combine variables with same units on a heatmap
            if ptype == 'heatmap':
                for vname, var in variables.items():
                    if var['plot_type'] == ptype:
                        plot_groups['g{}'.format(grpid)] = {
                            'variables': mark_safe(json.dumps([vname])),
                            'units':
                                mark_safe(json.dumps(
                                    [variables[vname]['units']])),
                            'long_names':
                                mark_safe(json.dumps(
                                    [variables[vname]['long_name']])),
                            'plot_type': mark_safe(ptype),
                        }
                        grpid += 1
            else:
                # unique units
                for unit in set(units):
                    uvars = [vname for vname, var in variables.items() \
                        if var['plot_type'] == ptype and var['units'] == unit]
                    # uvars is list of variables with units unit
                    plot_groups['g{}'.format(grpid)] = {
                        'variables': mark_safe(json.dumps(uvars)),
                        'units': mark_safe(json.dumps(
                            [variables[v]['units'] for v in uvars])),
                        'long_names': mark_safe(json.dumps(
                            [variables[v]['long_name'] for v in uvars])),
                        'plot_type': mark_safe(ptype),
                    }
                    grpid += 1

        return render(
            request, self.template_name, {
                'form': form,
                'dataset': dset, 'plot_groups': plot_groups,
                'time0': time0, 'time': mark_safe(time),
                'data': mark_safe(data), 'dim2': mark_safe(dim2)})

