# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Views used by ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

# TODO:
#   cronjob to iterate over user sessions, age off expired ones,
#   remove any UserSelection instances that are not associated
#   with a session.

from django.shortcuts import render, get_object_or_404, redirect

from django.http import HttpResponse, Http404, HttpResponseForbidden

from django.views.generic.edit import View
from django.views.generic import TemplateView
from django.utils.safestring import mark_safe
from django.template import TemplateDoesNotExist

from ncharts import models as nc_models
from ncharts import forms as nc_forms
from ncharts import exceptions as nc_exceptions

import json, math, logging, threading
import numpy as np
import datetime

import collections

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

def selection_id_name(project_name, dataset_name):
    """Create a name for saving the user's data selection in their session.

    Args:
        project_name
        dataset_name

    Returns: name built from project and dataset names.

    A dataset name is unique within a project.
    In order to allow the user to easily browse multiple
    datasets, and save their previous selections, their
    selection is saved in the session under the name
    'pdid_' + project_name + '_' + dataset_name.

    django reserves session values starting with underscore,
    so we prepend 'pdid' to the name, just in the rare case
    that the project would start with an underscore.
    """

    return 'pdid_' + project_name + '_' + dataset_name

def get_selection_id_from_session(session, project_name, dataset_name):
    """Return the user's selection of dataset parameters,
    given a session, project and dataset.

    Args:
        session
        project_name
        dataset_name
    Raises:
        Http404
    Returns:
        The nc_models.UserSelection for the project and dataset
        associated with the session.

    Note that for this to work, caching must be turned off for this view
    in django, otherwise the get() method may not be called, and the
    previous selection will not be displayed.
    """

    sel_id_name = selection_id_name(project_name, dataset_name)
    return session.get(sel_id_name)

def get_selection_from_session(session, project_name, dataset_name):
    """Return the user's selection of dataset parameters,
    given a session, project and dataset.

    Args:
        session
        project_name
        dataset_name
    Raises:
        Http404
    Returns:
        The nc_models.UserSelection for the project and dataset
        associated with the session.

    Note that for this to work, caching must be turned off for this view
    in django, otherwise the get() method may not be called, and the
    previous selection will not be displayed.
    """

    request_id = get_selection_id_from_session(session, project_name, dataset_name)
    usersel = None
    if request_id:
        usersel = get_object_or_404(nc_models.UserSelection.objects,
                                    id=request_id)
    else:
        session.set_test_cookie()
    return usersel

def save_selection_to_session(
        session, project_name, dataset_name, usersel):
    """Save the user' selection of dataset parameters to the session.

    Args:
        session
        project_name
        dataset_name
        usersel: nc_models.UserSelection
    """
    sel_id_name = selection_id_name(project_name, dataset_name)
    session[sel_id_name] = usersel.id

def get_dataset(usersel):
    """Return the dataset from a UserSelection, casting to either
    a FileDataset or DBDataset.

    """
    dset = usersel.dataset

    try:
        dset = dset.filedataset
    except nc_models.FileDataset.DoesNotExist:
        try:
            dset = dset.dbdataset
        except nc_models.DBDataset.DoesNotExist:
            raise Http404

    return dset

class DatasetView(View):
    """Render a form where the user can choose parameters to plot a dataset.
    """

    template_name = 'ncharts/dataset.html'

    __sent_data_times = {}
    __sent_data_times_lock = threading.Lock()

    @classmethod
    def set_sent_data_times(cls, requestid, vname, time_last_ok, time_last):
        """Class method, for a request id, and a variable, set the time of the
        last non-nan data sent, and the time of the last value sent.

        Args:
            cls:
            requestid: id from UserSelection
            vname: name of variable
            time_last_ok: time of last data value sent for the variable
                that was non a NAN
            time_last: time of last data value sent for the variable

        """
        cls.__sent_data_times_lock.acquire()

        if not requestid in cls.__sent_data_times:
            cls.__sent_data_times[requestid] = {}
        cls.__sent_data_times[requestid][vname] = [time_last_ok, time_last]
        cls.__sent_data_times_lock.release()

    @classmethod
    def get_sent_data_times(cls, requestid, vname):
        """Class method, for a request id, and a variable, get the time of the
        last non-nan data sent, and the time of the last value sent.

        Args:
            cls:
            requestid: id from UserSelection
            vname: name of variable

        Returns:
            List of length 2:
                [0]: time of last data value sent for the variable
                    that was non a NAN
                [1]: time of last data value sent for the variable
        """
        cls.__sent_data_times_lock.acquire()

        if not requestid in cls.__sent_data_times:
            return [None, None]
        if not vname in cls.__sent_data_times[requestid]:
            return [None, None]

        if len(cls.__sent_data_times[requestid][vname]) != 2:
            return [None, None]

        time_last_ok = cls.__sent_data_times[requestid][vname][0]
        time_last = cls.__sent_data_times[requestid][vname][1]

        cls.__sent_data_times_lock.release()

        return [time_last_ok, time_last]

    def get(self, request, *args, project_name, dataset_name, **kwargs):
        """Respond to a get request where the user has specified a
        project and dataset.

        """

        debug = False

        if debug:
            _logger.debug(
                "DatasetView get, dataset %s of project %s",
                dataset_name, project_name)

        proj = get_object_or_404(nc_models.Project.objects, name=project_name)

        # Get the named dataset of the project
        dset = get_object_or_404(proj.dataset_set, name=dataset_name)

        # cast to a FileDataset, or if that fails, a DBDataset
        try:
            dset = dset.filedataset
        except nc_models.FileDataset.DoesNotExist:
            try:
                dset = dset.dbdataset
            except nc_models.DBDataset.DoesNotExist:
                raise Http404

        if len(dset.timezones.all()) > 0:
            timezone = dset.timezones.all()[0]
        elif len(dset.project.timezones.all()) > 0:
            timezone = dset.project.timezones.all()[0]
        else:
            _logger.error(
                "dataset %s of project %s has no associated timezone",
                dataset_name, project_name)
            timezone = nc_models.TimeZone.objects.get(tz='UTC')

        usersel = None
        try:
            usersel = get_selection_from_session(
                request.session, project_name, dataset_name)
        except Http404:
            pass

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

            save_selection_to_session(
                request.session, project_name, dataset_name, usersel)
            _logger.info(
                "get, new session, selection id=%d, project=%s,"
                " dataset=%s", usersel.id, project_name, dataset_name)

        else:
            if usersel.dataset.pk == dset.pk:
                # could check that usersel.dataset.name == dataset_name and
                # usersel.dataset.project.name == project_name
                # but I believe that is unnecessary, since the pk members
                # are unique.
                pass
            else:
                # Dataset stored under in user session
                # doesn't match that for project and dataset name.
                # Probably a server restart
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
            svars = json.loads(usersel.variables)
            if debug:
                _logger.debug(
                    "get, old session, same dataset, " \
                    "project=%s, dataset=%s, variables=%s",
                    project_name, dataset_name, usersel.variables)
        else:
            if debug:
                _logger.debug(
                    "get, old session, same dataset, "
                    "project=%s, dataset=%s, no variables",
                    project_name, dataset_name)
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

        # when sending times to datetimepicker, make them naive,
        # with values set as approproate for the dataset timezone
        start_time = datetime.datetime.fromtimestamp(
            usersel.start_time.timestamp(), tz=timezone.tz).replace(tzinfo=None)

        if debug:
            _logger.debug(
                "DatasetView get, old session, same dataset, "
                "project=%s, dataset=%s, start_time=%s, vars=%s",
                project_name, dataset_name,
                start_time, usersel.variables)

        form = nc_forms.DataSelectionForm(
            initial={
                'variables': svars,
                'timezone': timezone.tz,
                'start_time': start_time,
                'time_length_units': tunits,
                'time_length': tlen
            },
            dataset=dset)

        # if dset.end_time < datetime.datetime.now(timezone.tz):
        #     form.fields['track_real_time'].widget.attrs['disabled'] = True

        try:
            dvars = sorted(dset.get_variables().keys())
            form.set_variable_choices(dvars)
        except OSError as exc:
            form.no_data(repr(exc))

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

        try:
            usersel = get_selection_from_session(
                request.session, project_name, dataset_name)
        except Http404:
            pass

        if not usersel:
            # There is probably a scenario where a POST can come in
            # without selection id. Redirect them back to the get.
            _logger.error(
                "post but no session value for project %s, "
                "dataset %s, redirecting to get",
                project_name, dataset_name)
            # Uses the name='dataset' in urls.py
            return redirect(
                'ncharts:dataset', project_name=project_name,
                dataset_name=dataset_name)

        dset = get_dataset(usersel)

        # dataset name and project name from POST should agree with
        # those in the cached dataset.
        if dset.name != dataset_name or dset.project.name != project_name:
            _logger.error(
                "post, old session, project=%s, dataset=%s, "
                "url project=%s, dataset=%s",
                dset.project.name, dset.name,
                project_name, dataset_name)

            return self.get(request, *args, project_name=project_name,
                            dataset_name=dataset_name, **kwargs)

        # vars = [ v.name for v in dset.variables.all() ]

        # page-backward or page-forward in time
        # TODO: implement a javascript button that manipulates the
        # html field directly

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

        dvars = sorted(dset.get_variables().keys())
        form.set_variable_choices(dvars)

        # print("request.POST=", request.POST)
        if not form.is_valid():
            _logger.error('User form is not valid!: %s', repr(form.errors))
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
            ncdset = dset.get_netcdf_dataset()

            # a variable can be in a dataset, but not in a certain set of files.
            try:
                dsvars = ncdset.get_variables(
                    start_time=stime, end_time=etime)
            except OSError as exc:
                _logger.error("%s, %s: %s", project_name, dataset_name, exc)
                form.no_data(repr(exc))
                return render(request, self.template_name,
                              {'form': form, 'dataset': dset})

        elif isinstance(dset, nc_models.DBDataset):
            dbcon = dset.get_connection()
            dsvars = dbcon.get_variables(start_time=stime, end_time=etime)

        # selected and available variables, using set intersection
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

        try:
            if isinstance(dset, nc_models.FileDataset):
                ncdata = ncdset.read_time_series(
                    savail, start_time=stime, end_time=etime)
            else:
                ncdata = dbcon.read_time_series(
                    savail, start_time=stime, end_time=etime)

        except OSError as exc:
            _logger.error("%s, %s: %s", project_name, dataset_name, exc)
            form.no_data(repr(exc))
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

        for vname in savail:
            try:
                # works for any shape, as long as time is the first dimension
                lastok = np.where(~np.isnan(ncdata['data'][vname]))[0][-1]
                time_last_ok = ncdata['time'][lastok]
            except IndexError:
                # all data is nan
                time_last_ok = (stime - datetime.timedelta(seconds=0.001)).timestamp()

            time_last = ncdata['time'][-1]
            DatasetView.set_sent_data_times(
                usersel.id, vname, time_last_ok, time_last)

        # As an easy compression, subtract first time from all times,
        # reducing the number of characters sent.
        time0 = 0
        if len(ncdata['time']) > 0:
            time0 = ncdata['time'][0]
        time = json.dumps([x - time0 for x in ncdata['time']])

        def type_by_shape(shape):
            """Crude function to return a plot type, given a dimension.
            """
            if len(shape) == 1:
                return 'time-series'
            elif len(shape) == 2:
                return 'heatmap'
            else:
                return 'none'

        plot_types = set()
        for vname, var in variables.items():
            ptype = type_by_shape(ncdata['data'][vname].shape)
            var['plot_type'] = ptype
            plot_types.add(ptype)

        data = json.dumps(ncdata['data'], cls=NChartsJSONEncoder)

        dim2 = json.dumps(ncdata['dim2'], cls=NChartsJSONEncoder)

        # Create plot groups dictionary, for each
        # group, the variables in the group, their units, long_names, plot_type
        # Use OrderedDict so the plots come out in this order
        plot_groups = collections.OrderedDict()

        # loop over plot_types
        grpid = 0
        for ptype in plot_types:
            # print("ptype=", ptype)

            # For a heatmap, one plot per variable.
            if ptype == 'heatmap':
                for vname in sorted(variables):
                    var = variables[vname]
                    if var['plot_type'] == ptype:
                        plot_groups['g{}'.format(grpid)] = {
                            'variables': mark_safe(json.dumps([vname])),
                            'units':
                                mark_safe(json.dumps([var['units']])),
                            'long_names':
                                mark_safe(json.dumps([var['long_name']])),
                            'plot_type': mark_safe(ptype),
                        }
                        grpid += 1
            else:
                # unique units, in alphabetical order by the name of the
                # first variable which uses it. It is better to
                # have plots in alphabetical order by the first variable
                # plotted, rather than by their units.
                uunits = []
                # sorted(dict) becomes a list of sorted keys
                for vname in sorted(variables):
                    units = variables[vname]['units']
                    if not units in uunits:
                        uunits.append(units)

                # unique units
                for unit in uunits:
                    uvars = sorted([vname for vname, var in variables.items() \
                        if var['plot_type'] == ptype and var['units'] == unit])
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
                'dataset': dset,
                'plot_groups': plot_groups,
                'selid': usersel.id,
                'time0': time0,
                'time': mark_safe(time),
                'data': mark_safe(data),
                'dim2': mark_safe(dim2),
                'time_length': usersel.time_length
                })

class DataView(View):
    """Respond to ajax request for data.
    """

    def get(self, request, *args, selection_id, **kwargs):
        """Respond to a ajax get request.

        """

        debug = False

        if not request.session.test_cookie_worked():
            # The django server is backed by memcached, so I believe
            # this won't happen when the django server is restarted,
            # but will happen if the memcached daemon is restarted.
            _logger.error(
                "session cookie check failed. Either this server "
                "was restarted, or the user needs to enable cookies")

            # redirect back to square one
            return redirect('ncharts:projectsPlatforms')

            # return HttpResponse("Your cookie is not recognized.
            # Either this server was restarted, or you need to
            # enable cookies in your browser. Then please try again.")

        # selection id is passed in the get
        usersel = get_object_or_404(nc_models.UserSelection.objects,
                                    id=selection_id)
        dset = get_dataset(usersel)

        dataset_name = dset.name
        project_name = dset.project.name

        request_id = get_selection_id_from_session(
            request.session, project_name, dataset_name)

        if request_id:
            if not request_id == usersel.id:
                _logger.warning(
                    "%s, %s: DataView get, selection_id=%s"
                    " does not match selection id from sesson=%d",
                    project_name, dataset_name, selection_id, request_id)
                return HttpResponseForbidden(
                    "Unknown browser session, start over")
        else:
            _logger.warning(
                "%s, %s: DataView get, selection_id=%s"
                " not found in session",
                project_name, dataset_name, selection_id)
            return HttpResponseForbidden("Unknown browser session, start over")

        if isinstance(dset, nc_models.FileDataset):
            ncdset = dset.get_netcdf_dataset()
        elif isinstance(dset, nc_models.DBDataset):
            dbcon = dset.get_connection()

        # selected variables
        svars = json.loads(usersel.variables)

        if len(svars) == 0:
            _logger.warn(
                "%s, %s: variables not found for id=%d",
                project_name, dataset_name, usersel.id)
            return redirect(
                'ncharts:dataset', project_name=project_name,
                dataset_name=dataset_name)

        timezone = usersel.timezone

        all_vars_data = {}

        for vname in svars:

            # timetag of last non-nan sample for this variable sent to client
            # timetag of last sample for this variable sent to client
            [time_last_ok, time_last] = \
                    DatasetView.get_sent_data_times(usersel.id, vname)
            if not time_last_ok:
                _logger.warn(
                    "%s, %s: data times not found for id=%d, variable=%s",
                    project_name, dataset_name, usersel.id, vname)
                return redirect(
                    'ncharts:dataset', project_name=project_name,
                    dataset_name=dataset_name)

            stime = datetime.datetime.fromtimestamp(
                time_last_ok + 0.001, tz=timezone)

            if not debug:
                etime = datetime.datetime.now(timezone)
            else:
                etime = stime + datetime.timedelta(seconds=3600)

            try:
                if isinstance(dset, nc_models.FileDataset):
                    ncdata = ncdset.read_time_series(
                        [vname], start_time=stime, end_time=etime)
                else:
                    ncdata = dbcon.read_time_series(
                        [vname], start_time=stime, end_time=etime)
                try:
                    lastok = np.where(
                        ~np.isnan(ncdata['data'][vname]))[0][-1]
                    time_last_ok = ncdata['time'][lastok]
                    if debug:
                        _logger.debug(
                            "Dataview Get, %s, %s: variable=%s, last_time_ok=%s"
                            "stime=%s, etime=%s",
                            project_name, dataset_name, vname,
                            datetime.datetime.fromtimestamp(
                                time_last_ok, tz=timezone).isoformat(),
                            stime.isoformat(), etime.isoformat())
                except IndexError:
                    # all data nan. Only send those after time_last
                    if debug:
                        _logger.debug(
                            "Dataview Get, %s, %s: variable=%s, all data nan, " \
                            "stime=%s, etime=%s",
                            project_name, dataset_name, vname,
                            stime.isoformat(), etime.isoformat())

                    # index of first time > time_last
                    idx = next((i for i, t in enumerate(ncdata['time']) \
                        if t > time_last), -1)
                    if idx >= 0:
                        ncdata['time'] = ncdata['time'][idx:]
                        ncdata['data'][vname] = ncdata['data'][vname][idx:]
                        time_last = ncdata['time'][-1]
                    else:
                        if debug:
                            _logger.debug(
                                "Dataview Get, %s, %s: variable=%s, no new data, "
                                "stime=%s, etime=%s, time_last=%s",
                                project_name, dataset_name, vname,
                                stime.isoformat(), etime.isoformat(),
                                datetime.datetime.fromtimestamp(
                                    time_last, tz=timezone).isoformat())
                        ncdata['time'] = []
                        ncdata['data'][vname] = []
            except OSError as exc:
                _logger.error("%s, %s: %s", project_name, dataset_name, exc)
                raise Http404(str(exc))
            except nc_exceptions.TooMuchDataException as exc:
                _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
                raise Http404(str(exc))
            except nc_exceptions.NoDataException as exc:
                if debug:
                    _logger.debug(
                        "Dataview Get: %s, %s ,%s: variable=%s, "
                        ", time_last=%s",
                        project_name, dataset_name, exc, vname,
                        datetime.datetime.fromtimestamp(
                            time_last, tz=timezone).isoformat())
                # make up some data
                ncdata = {
                    'time': [],
                    'data': {vname: []},
                    'dim2': []}
                # {vname: np.array([], dtype=np.dtype("float32"))},

            DatasetView.set_sent_data_times(
                usersel.id, vname, time_last_ok, time_last)

            # As an easy compression, subtract first time from all times,
            # reducing the number of characters sent.
            time0 = 0
            dim2 = []
            if len(ncdata['time']) > 0:
                time0 = ncdata['time'][0]
                if 'data' in ncdata['dim2']:
                    dim2 = json.dumps(
                        ncdata['dim2']['data'],
                        cls=NChartsJSONEncoder)

            time = json.dumps([x - time0 for x in ncdata['time']])

            data = json.dumps(ncdata['data'][vname], cls=NChartsJSONEncoder)

            all_vars_data[vname] = {
                'time0': time0,
                'time': time,
                'data': data,
                'dim2': dim2
            }

        # jstr = json.dumps(all_vars_data)
        # _logger.debug("json data=%s",jstr)
        # return HttpResponse(jstr, content_type="application/json")
        return HttpResponse(
            json.dumps(all_vars_data),
            content_type="application/json")

