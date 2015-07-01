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
#   remove any ClientState instances that are not associated
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

import json, math, logging
import numpy as np
import datetime

import collections

_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

# Abbreviated name of a sounding, e.g. "Jun23_0413Z"
SOUNDING_NAME_FMT = "%b%d_%H%MZ"

class StaticView(TemplateView):
    """View class for rendering a simple template page.
    """
    def get(self, request, page, *args, **kwargs):
        self.template_name = page
        _logger.debug("StaticView, page=%s", page)
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

    context = {'projects': projs}
    return render(request, 'ncharts/projects.html', context)

def platforms(request):
    """View function for list of platforms.
    """

    # root = Root.objects.get(name='platforms')
    # plats = root.platform_set.all()

    plats = nc_models.Platform.objects.all()

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

    context = {'projects': projs, 'platforms': plats}
    return render(request, 'ncharts/projectsPlatforms.html', context)

def project(request, project_name):
    """View function for list of platforms and datasets of a project.
    """
    try:
        proj = nc_models.Project.objects.get(name=project_name)
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

        # _logger.debug("type(obj)=%s", type(obj))
        if isinstance(obj, np.ndarray):
            if len(obj.shape) > 1:
                # this should reduce the rank by one
                # _logger.debug("Encoder, default, len(obj.shape)=%d",
                #   len(obj.shape))
                return [v for v in obj[:]]
            else:
                # _logger.debug("Encoder, default, len(obj.shape)=%d",
                #   len(obj.shape))
                return [roundcheck(v) for v in obj]
        else:
            return json.JSONEncoder.default(self, obj)

def client_id_name(project_name, dataset_name):
    """Create a name for saving the client state in their session.

    Args:
        project_name
        dataset_name

    Returns: name built from project and dataset names.

    A dataset name is unique within a project.
    In order to allow the user to easily browse multiple
    datasets, and save their previous states, their
    client state is saved in the session under the name
    'pdid_' + project_name + '_' + dataset_name.

    django reserves session values starting with underscore,
    so we prepend 'pdid' to the name, just in the rare case
    that the project would start with an underscore.
    """

    return 'pdid_' + project_name + '_' + dataset_name

def get_client_id_from_session(session, project_name, dataset_name):
    """Return a client state id, given a session, project and dataset.

    Args:
        session
        project_name
        dataset_name
    Raises:
        Http404
    Returns:
        The nc_models.ClientState for the project and dataset
        associated with the session.

    Note that for this to work, caching must be turned off for this view
    in django, otherwise the get() method may not be called, and the
    previous client state will not be displayed.
    """

    sel_id_name = client_id_name(project_name, dataset_name)
    return session.get(sel_id_name)

def get_client_from_session(session, project_name, dataset_name):
    """Return a client state, given a session, project and dataset.

    Args:
        session
        project_name
        dataset_name
    Raises:
        Http404
    Returns:
        The nc_models.ClientState for the project and dataset
        associated with the session.

    Note that for this to work, caching must be turned off for this view
    in django, otherwise the get() method may not be called, and the
    previous client state will not be displayed.
    """

    client_id = get_client_id_from_session(session, project_name, dataset_name)
    client_state = None
    if client_id:
        client_state = get_object_or_404(
            nc_models.ClientState.objects, id=client_id)
    else:
        session.set_test_cookie()
    return client_state

def save_client_to_session(
        session, project_name, dataset_name, client_state):
    """Save the client state to the session.

    Args:
        session
        project_name
        dataset_name
        client_state: nc_models.ClientState
    """
    sel_id_name = client_id_name(project_name, dataset_name)
    session[sel_id_name] = client_state.id

def get_dataset(client_state):
    """Return the dataset from a ClientState, casting to either
    a FileDataset or DBDataset.

    """
    dset = client_state.dataset

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

        client_state = None
        try:
            client_state = get_client_from_session(
                request.session, project_name, dataset_name)
        except Http404:
            pass

        if not client_state:
            # _logger.debug('DatasetView get, dset.variables=%s',
            #   dset.variables)

            tnow = datetime.datetime.now(timezone.tz)
            delta = datetime.timedelta(days=1)

            if dset.get_end_time() < tnow or isinstance(dset, nc_models.DBDataset):
                stime = dset.get_start_time()
            else:
                stime = tnow - delta

            client_state = nc_models.ClientState.objects.create(
                dataset=dset,
                timezone=timezone.tz,
                start_time=stime,
                time_length=delta.total_seconds())

            save_client_to_session(
                request.session, project_name, dataset_name, client_state)
            _logger.info(
                "get, new session, client id=%d, project=%s,"
                " dataset=%s", client_state.id, project_name, dataset_name)

        else:
            if client_state.dataset.pk == dset.pk:
                # could check that client_state.dataset.name == dataset_name and
                # client_state.dataset.project.name == project_name
                # but I believe that is unnecessary, since the pk members
                # are unique.
                pass
            else:
                # Dataset stored under in user session
                # doesn't match that for project and dataset name.
                # Probably a server restart
                client_state.dataset = dset
                client_state.timezone = timezone.tz
                client_state.variables = ""
                client_state.soundings = ""

                tnow = datetime.datetime.now(timezone.tz)
                delta = datetime.timedelta(days=1)
                if dset.get_end_time() > tnow:
                    stime = tnow - delta
                else:
                    stime = dset.get_start_time()

                client_state.start_time = stime
                client_state.time_length = delta.total_seconds()
                client_state.save()

        # variables selected previously by user
        if client_state.variables:
            svars = json.loads(client_state.variables)
            if debug:
                _logger.debug(
                    "get, old session, same dataset, " \
                    "project=%s, dataset=%s, variables=%s",
                    project_name, dataset_name, client_state.variables)
        else:
            if debug:
                _logger.debug(
                    "get, old session, same dataset, "
                    "project=%s, dataset=%s, no variables",
                    project_name, dataset_name)
            svars = []

        tlen = client_state.time_length

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
            client_state.start_time.timestamp(),
            tz=timezone.tz).replace(tzinfo=None)

        if debug:
            _logger.debug(
                "DatasetView get, old session, same dataset, "
                "project=%s, dataset=%s, start_time=%s, vars=%s",
                project_name, dataset_name,
                start_time, client_state.variables)

        sel_soundings = []
        if client_state.soundings:
            sel_soundings = json.loads(client_state.soundings)

        form = nc_forms.DataSelectionForm(
            initial={
                'variables': svars,
                'timezone': client_state.timezone,
                'start_time': start_time,
                'time_length_units': tunits,
                'time_length': tlen,
                'track_real_time': client_state.track_real_time,
                'soundings': sel_soundings,
            },
            dataset=dset)

        if dset.end_time < datetime.datetime.now(timezone.tz):
            form.fields['track_real_time'].widget.attrs['disabled'] = True

        soundings = []
        try:
            dvars = sorted(dset.get_variables().keys())
            form.set_variable_choices(dvars)

            if dset.dset_type == "sounding":
                # all soundings in the dataset
                soundings = dset.get_series_tuples(
                    series_name_fmt=SOUNDING_NAME_FMT)

                # soundings between the start and end time
                s_choices = dset.get_series_names(
                    series_name_fmt=SOUNDING_NAME_FMT,
                    start_time=client_state.start_time,
                    end_time=client_state.start_time + \
                        datetime.timedelta(seconds=client_state.time_length))

                s_choices = [(s, s) for s in s_choices]
                _logger.debug("s_choices=%s",s_choices)
                form.fields['soundings'].choices = s_choices

        except OSError as exc:
            form.no_data(repr(exc))

        return render(
            request, self.template_name,
            {
                'form': form,
                'dataset': dset,
                'soundings': mark_safe(json.dumps(soundings))
            })

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

        client_state = None
        try:
            client_state = get_client_from_session(
                request.session, project_name, dataset_name)
        except Http404:
            pass

        if not client_state:
            # There is probably a scenario where a POST can come in
            # without client id. Redirect them back to the get.
            _logger.error(
                "post but no session value for project %s, "
                "dataset %s, redirecting to get",
                project_name, dataset_name)
            # Uses the name='dataset' in urls.py
            return redirect(
                'ncharts:dataset', project_name=project_name,
                dataset_name=dataset_name)

        dset = get_dataset(client_state)

        # dataset name and project name from POST should agree with
        # those in the cached dataset.
        if dset.name != dataset_name or dset.project.name != project_name:
            _logger.error(
                "post, old session, project=%s, dataset=%s, "
                "url project=%s, dataset=%s",
                dset.project.name, dset.name,
                project_name, dataset_name)

            return redirect(
                'ncharts:dataset', project_name=project_name,
                dataset_name=dataset_name)

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

        # Have to set the choices for variables and soundings
        # before the form is validated.
        soundings = []
        try:
            dvars = sorted(dset.get_variables().keys())
            form.set_variable_choices(dvars)

            if dset.dset_type == "sounding":
                # all soundings in the dataset
                soundings = dset.get_series_tuples(
                    series_name_fmt=SOUNDING_NAME_FMT)

                s_choices = dset.get_series_names(
                    series_name_fmt=SOUNDING_NAME_FMT)

                s_choices = [(s, s) for s in s_choices]
                form.fields['soundings'].choices = s_choices

        except OSError as exc:
            form.no_data(repr(exc))

        if not form.is_valid():
            _logger.error('User form is not valid!: %s', repr(form.errors))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        # Save the client state from the form
        svars = form.cleaned_data['variables']
        sel_soundings = form.cleaned_data['soundings']

        stime = form.cleaned_data['start_time']
        delt = form.get_cleaned_time_length()
        etime = stime + delt
        client_state.variables = json.dumps(svars)
        client_state.start_time = stime
        client_state.timezone = form.cleaned_data['timezone']
        client_state.time_length = delt.total_seconds()
        client_state.track_real_time = form.cleaned_data['track_real_time']
        client_state.soundings = json.dumps(sel_soundings)
        client_state.save()

        # filedset = None
        # try:
        #     filedset = dset.filedataset
        # except nc_models.FileDataset.DoesNotExist as exc:
        #     raise Http404

        try:
            dvars = sorted(dset.get_variables().keys())
            form.set_variable_choices(dvars)

            if dset.dset_type == "sounding":
                # soundings between the start and end time
                s_choices = dset.get_series_names(
                    series_name_fmt=SOUNDING_NAME_FMT,
                    start_time=stime,
                    end_time=etime)

                s_choices = [(s, s) for s in s_choices]
                form.fields['soundings'].choices = s_choices
        except OSError as exc:
            _logger.error("%s, %s: %s", project_name, dataset_name, exc)
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        if isinstance(dset, nc_models.FileDataset):
            ncdset = dset.get_netcdf_dataset()

            # a variable can be in a dataset, but not in a certain set of files.
            try:
                dsvars = ncdset.get_variables(
                    start_time=stime, end_time=etime)
            except OSError as exc:
                _logger.error("%s, %s: %s", project_name, dataset_name, exc)
                form.no_data(repr(exc))
                return render(
                    request, self.template_name,
                    {
                        'form': form,
                        'dataset': dset,
                        'soundings': mark_safe(json.dumps(soundings))
                    })

        elif isinstance(dset, nc_models.DBDataset):
            try:
                dbcon = dset.get_database_connection()
                dsvars = dbcon.get_variables()
            except Exception as exc:
                _logger.error("%s, %s: %s", project_name, dataset_name, exc)
                form.no_data(repr(exc))
                return render(
                    request, self.template_name,
                    {
                        'form': form,
                        'dataset': dset,
                        'soundings': mark_safe(json.dumps(soundings))
                    })

        # selected and available variables, using set intersection
        savail = list(set(svars) & set(dsvars.keys()))

        if len(savail) == 0:
            exc = nc_exceptions.NoDataException(
                "variables {} not found in dataset".format(svars))
            _logger.warn(repr(exc))
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        series_name_fmt = None
        if dset.dset_type == "sounding":
            if len(sel_soundings) == 0:
                exc = nc_exceptions.NoDataException(
                    "select one or more soundings")
                _logger.warn(repr(exc))
                form.no_data(repr(exc))
                return render(
                    request, self.template_name,
                    {
                        'form': form,
                        'dataset': dset,
                        'soundings': mark_safe(json.dumps(soundings))
                    })
            series_name_fmt = SOUNDING_NAME_FMT
        else:
            sel_soundings = None

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
                    savail, start_time=stime, end_time=etime,
                    series=sel_soundings,
                    series_name_fmt=series_name_fmt)
            else:
                ncdata = dbcon.read_time_series(
                    savail, start_time=stime, end_time=etime)

        except OSError as exc:
            _logger.error("%s, %s: %s", project_name, dataset_name, exc)
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        except nc_exceptions.TooMuchDataException as exc:
            _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
            form.too_much_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        except nc_exceptions.NoDataException as exc:
            _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        time0 = {}
        for series_name in ncdata['time']:

            if series_name == "":
                for vname in savail:
                    try:
                        # works for any shape, as long as time is the
                        # first dimension
                        lastok = np.where(~np.isnan(
                            ncdata['data'][series_name][vname]))[0][-1]
                        time_last_ok = ncdata['time'][series_name][lastok]
                    except IndexError:
                        # all data is nan
                        time_last_ok = (stime - \
                            datetime.timedelta(seconds=0.001)).timestamp()

                    time_last = ncdata['time'][series_name][-1]

                    client_state.save_data_times(
                        vname, time_last_ok, time_last)

            # As an easy compression, subtract first time from all times,
            # reducing the number of characters sent.
            time0[series_name] = 0
            if len(ncdata['time'][series_name]) > 0:
                time0[series_name] = ncdata['time'][series_name][0]

            # subtract off time0
            ncdata['time'][series_name] = [x - time0[series_name] for \
                    x in ncdata['time'][series_name]]

        time0 = json.dumps(time0)
        time = json.dumps({k: ncdata['time'][k] for k in ncdata['time']})
        data = json.dumps(
            {k: ncdata['data'][k] for k in ncdata['data']}, cls=NChartsJSONEncoder)
        dim2 = json.dumps(
            {k: ncdata['dim2'][k] for k in ncdata['dim2']}, cls=NChartsJSONEncoder)

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
        if len(ncdata['time']) == 1 and '' in ncdata['time']:
            for vname, var in variables.items():
                ptype = type_by_shape(ncdata['data'][''][vname].shape)
                var['plot_type'] = ptype
                plot_types.add(ptype)
        else:
            plot_types.add("sounding-profile")


        # Create plot groups dictionary, for each
        # group, the variables in the group, their units, long_names, plot_type
        # Use OrderedDict so the plots come out in this order
        plot_groups = collections.OrderedDict()

        # loop over plot_types
        grpid = 0
        for ptype in plot_types:
            # _logger.debug("ptype=%s", ptype)

            # For a heatmap, one plot per variable.
            if ptype == 'heatmap':
                for vname in sorted(variables):
                    var = variables[vname]
                    if var['plot_type'] == ptype:
                        plot_groups['g{}'.format(grpid)] = {
                            'series': "",
                            'variables': mark_safe(json.dumps([vname])),
                            'units':
                                mark_safe(json.dumps([var['units']])),
                            'long_names':
                                mark_safe(json.dumps([var['long_name']])),
                            'plot_type': mark_safe(ptype),
                        }
                        grpid += 1
            elif ptype == 'sounding-profile':
                # one profile plot per series name
                for series_name in ncdata['time']:
                    vnames = [v for v in variables]
                    units = [var['units'] for var in variables.values()]
                    long_names = [var['long_name'] for var in variables.values()]
                    plot_groups['g{}'.format(grpid)] = {
                        'series': series_name,
                        'variables': mark_safe(json.dumps(vnames)),
                        'units': mark_safe(json.dumps(units)),
                        'long_names': mark_safe(json.dumps(long_names)),
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
                        'series': "",
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
                'selid': client_state.id,
                'time0': mark_safe(time0),
                'time': mark_safe(time),
                'data': mark_safe(data),
                'dim2': mark_safe(dim2),
                'time_length': client_state.time_length,
                'soundings': mark_safe(json.dumps(soundings)),
                })

class DataView(View):
    """Respond to ajax request for data.
    """

    def get(self, request, *args, client_id, **kwargs):
        """Respond to a ajax get request.

        """

        debug = False

        if not request.session.test_cookie_worked():
            # The django server is backed by memcached, so I believe
            # this won't happen when the django server is restarted,
            # but will happen if the memcached daemon is restarted.
            _logger.error(
                "session test cookie check failed, host=%s",
                request.get_host())

            # redirect back to square one
            # return redirect('ncharts:projectsPlatforms')

            return HttpResponse("Your cookie is not recognized.  Either "\
                "this server was restarted, or you need to enable cookies "\
                "in your browser. Then please try again.")

        # client id is passed in the get
        client_state = get_object_or_404(
            nc_models.ClientState.objects, id=client_id)
        dset = get_dataset(client_state)

        dataset_name = dset.name
        project_name = dset.project.name

        client_id = get_client_id_from_session(
            request.session, project_name, dataset_name)

        if client_id:
            if not client_id == client_state.id:
                _logger.warning(
                    "%s, %s: DataView get, client_id=%s"
                    " does not match client id from sesson=%d",
                    project_name, dataset_name, client_id, client_id)
                return HttpResponseForbidden(
                    "Unknown browser session, start over")
        else:
            _logger.warning(
                "%s, %s: DataView get, client_id=%s"
                " not found in session",
                project_name, dataset_name, client_id)
            return HttpResponseForbidden("Unknown browser session, start over")

        if isinstance(dset, nc_models.FileDataset):
            ncdset = dset.get_netcdf_dataset()
        elif isinstance(dset, nc_models.DBDataset):
            dbcon = dset.get_connection()

        # selected variables
        svars = json.loads(client_state.variables)

        if len(svars) == 0:
            _logger.warn(
                "%s, %s: variables not found for id=%d",
                project_name, dataset_name, client_state.id)
            return redirect(
                'ncharts:dataset', project_name=project_name,
                dataset_name=dataset_name)

        timezone = client_state.timezone

        all_vars_data = {}

        for vname in svars:

            # timetag of last non-nan sample for this variable sent to client
            # timetag of last sample for this variable sent to client
            [time_last_ok, time_last] = client_state.get_data_times(vname)
            if not time_last_ok:
                _logger.warn(
                    "%s, %s: data times not found for client id=%d, " \
                    "variable=%s",
                    project_name, dataset_name, client_state.id, vname)
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
                        ~np.isnan(ncdata['data'][''][vname]))[0][-1]
                    time_last_ok = ncdata['time'][''][lastok]
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
                    idx = next((i for i, t in enumerate(ncdata['time']['']) \
                        if t > time_last), -1)
                    if idx >= 0:
                        ncdata['time'][''] = ncdata['time'][''][idx:]
                        ncdata['data'][''][vname] = ncdata['data'][''][vname][idx:]
                        time_last = ncdata['time'][''][-1]
                    else:
                        if debug:
                            _logger.debug(
                                "Dataview Get, %s, %s: variable=%s, no new data, "
                                "stime=%s, etime=%s, time_last=%s",
                                project_name, dataset_name, vname,
                                stime.isoformat(), etime.isoformat(),
                                datetime.datetime.fromtimestamp(
                                    time_last, tz=timezone).isoformat())
                        ncdata['time'][''] = []
                        ncdata['data'][''][vname] = []
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
                    'time': {
                        '': []
                    },
                    'data': {
                        '': {
                            vname: [],
                        },
                    },
                    'dim2': {
                        '': {},
                    }
                }
                # {vname: np.array([], dtype=np.dtype("float32"))},

            client_state.save_data_times(vname, time_last_ok, time_last)

            # As an easy compression, subtract first time from all times,
            # reducing the number of characters sent.
            time0 = 0
            if len(ncdata['time']['']) > 0:
                time0 = ncdata['time'][''][0]

            dim2 = []
            if vname in ncdata['dim2'][''] and 'data' in ncdata['dim2'][''][vname]:
                dim2 = json.dumps(
                    ncdata['dim2'][''][vname]['data'],
                    cls=NChartsJSONEncoder)

            time = json.dumps([x - time0 for x in ncdata['time']['']])

            data = json.dumps(ncdata['data'][''][vname], cls=NChartsJSONEncoder)

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

