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

from django.http import HttpResponse, Http404

from django.views.generic.edit import View
from django.views.generic import TemplateView
from django.utils.safestring import mark_safe
from django.template import TemplateDoesNotExist
from django.core.urlresolvers import reverse
from django.contrib import messages

from ncharts import models as nc_models
from ncharts import forms as nc_forms
from ncharts import exceptions as nc_exc

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

    client_id = session.get(sel_id_name)

    if not client_id:
        raise Http404(
            "Session not found for " + \
            project_name + ": " + dataset_name + \
            ". The server may have been restarted or you may need to enable cookies.")
    return client_id

def get_client_from_session(session, project_name, dataset_name):
    """Return a client state, given a session, project and dataset.

    Args:
        session
        project_name
        dataset_name
    Returns:
        The nc_models.ClientState for the project and dataset
        associated with the session.
    Raises:
        Http404

    Note that for this to work, caching must be turned off for this view
    in django, otherwise django will just reply from its cache, which means
    the get() or post() method is not called for the view.
    """

    client_id = get_client_id_from_session(session, project_name, dataset_name)
    return get_object_or_404(nc_models.ClientState.objects, id=client_id)

def attach_client_to_session(
        session, project_name, dataset_name, client_state):
    """Attach the client state to the session, by saving its id.

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

        client_state_needs_save = False

        if not client_state:
            # _logger.debug('DatasetView get, dset.variables=%s',
            #   dset.variables)

            tnow = datetime.datetime.now(timezone.tz)
            tdelta = datetime.timedelta(days=1)

            if dset.get_end_time() < tnow or isinstance(dset, nc_models.DBDataset):
                stime = dset.get_start_time()
            else:
                stime = tnow - tdelta

            client_state = nc_models.ClientState.objects.create(
                dataset=dset,
                timezone=timezone.tz,
                start_time=stime,
                time_length=tdelta.total_seconds())

            attach_client_to_session(
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
                client_state.yvariable = ""
                client_state.soundings = ""

                tnow = datetime.datetime.now(timezone.tz)
                tdelta = datetime.timedelta(days=1)
                if dset.get_end_time() > tnow:
                    stime = tnow - tdelta
                else:
                    stime = dset.get_start_time()

                client_state.start_time = stime
                client_state.time_length = tdelta.total_seconds()
                client_state.track_real_time = False
                client_state_needs_save = True

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

        post_real_time = datetime.datetime.now(timezone.tz) > dset.end_time

        if post_real_time and client_state.track_real_time:
            client_state.track_real_time = False
            client_state_needs_save = True

        if client_state.track_real_time:
            client_state.start_time = datetime.datetime.now(timezone.tz) - \
                datetime.timedelta(seconds=client_state.time_length)
            client_state_needs_save = True
        elif client_state.start_time > dset.end_time:
            client_state.start_time = dset.end_time - \
                datetime.timedelta(seconds=client_state.time_length)
            client_state_needs_save = True

        if client_state_needs_save:
            client_state.save()

        # when sending times to datetimepicker, make them naive,
        # with values set as approproate for the dataset timezone
        form_start_time = client_state.start_time.astimezone(timezone.tz).replace(tzinfo=None)

        if debug:
            _logger.debug(
                "DatasetView get, old session, same dataset, "
                "project=%s, dataset=%s, start_time=%s, vars=%s",
                project_name, dataset_name,
                client_state.start_time, client_state.variables)

        sel_soundings = []
        if client_state.soundings:
            sel_soundings = json.loads(client_state.soundings)

        tlfields = nc_forms.get_time_length_fields(client_state.time_length)

        form = nc_forms.DataSelectionForm(
            initial={
                'variables': svars,
                'yvariable': client_state.yvariable,
                'timezone': client_state.timezone,
                'start_time': form_start_time,
                'time_length_units': tlfields[1],
                'time_length': tlfields[0],
                'track_real_time': client_state.track_real_time,
                'soundings': sel_soundings,
            },
            dataset=dset)

        if post_real_time:
            form.fields['track_real_time'].widget.attrs['disabled'] = True

        soundings = []
        try:
            dsetvars = dset.get_variables()
            dvars = sorted(dsetvars.keys())
            form.set_variable_choices(dvars)
            form.set_yvariable_choices(dvars)

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
                form.fields['soundings'].choices = s_choices

        except (nc_exc.NoDataException, nc_exc.NoDataFoundException) as exc:
            _logger.warn("%s, %s: get_variables: %s", project_name, dset, exc)
            form.no_data("No variables found in {}: {} ".format(str(dset), exc))

        return render(
            request, self.template_name,
            {
                'form': form,
                'dataset': dset,
                'variables': dsetvars,
                'soundings': mark_safe(json.dumps(soundings))
            })

    def post(self, request, *args, project_name, dataset_name, **kwargs):
        """Respond to a post request where the user has sent back a form.

        Using the requested parameters in the form, such as start and end times
        and a list of variables, the dataset can be read, and the contents
        sent back to the user.
        """

        try:
            client_state = get_client_from_session(
                request.session, project_name, dataset_name)
        except Http404 as exc:
            _logger.error(exc)
            messages.warning(request, exc)
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
            messages.warning(request, "session is for a different dataset")
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

            start_time = timezone.localize(
                datetime.datetime.strptime(
                    request.POST['start_time'], "%Y-%m-%d %H:%M"))

            delt = nc_forms.get_time_length(
                request.POST['time_length_0'],
                request.POST['time_length_units'])

            if request.POST['submit'] == 'page-backward':
                start_time = start_time - delt
            elif request.POST['submit'] == 'page-forward':
                start_time = start_time + delt

            post = request.POST.copy()
            post['start_time'] = start_time.replace(tzinfo=None)
            post['track_real_time'] = False
            form = nc_forms.DataSelectionForm(post, dataset=dset, request=request)
        else:
            form = nc_forms.DataSelectionForm(request.POST, dataset=dset, request=request)

        # Have to set the choices for variables and soundings
        # before the form is validated.
        soundings = []
        variable_choices = []
        sounding_choices = []
        try:
            dsetvars = dset.get_variables()
            variable_choices = sorted(dsetvars.keys())
            form.set_variable_choices(variable_choices)
            form.set_yvariable_choices(variable_choices)

            if dset.dset_type == "sounding":
                # all soundings in the dataset
                soundings = dset.get_series_tuples(
                    series_name_fmt=SOUNDING_NAME_FMT)

                sounding_choices = dset.get_series_names(
                    series_name_fmt=SOUNDING_NAME_FMT)

                sounding_choices = [(s, s) for s in sounding_choices]
                form.fields['soundings'].choices = sounding_choices

        except (nc_exc.NoDataFoundException, nc_exc.NoDataException) as exc:
            _logger.warn("%s, %s: get_variables: %s", project_name, dset, exc)
            form.no_data("No variables found in {}: {}".format(dset, exc))

        if not form.is_valid():
            _logger.error('User form is not valid!: %s', repr(form.errors))
            if form.clean_method_altered_data:
                post = request.POST.copy()
                post['start_time'] = form.cleaned_data['start_time']
                post['track_real_time'] = form.cleaned_data['track_real_time']
                form = nc_forms.DataSelectionForm(post, dataset=dset)

            form.set_variable_choices(variable_choices)
            form.set_yvariable_choices(variable_choices)
            if dset.dset_type == "sounding":
                form.fields['soundings'].choices = sounding_choices
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'variables': dsetvars,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        # Save the client state from the form
        svars = form.cleaned_data['variables']
        sel_soundings = form.cleaned_data['soundings']

        yvar = form.cleaned_data['yvariable']

        tdelta = form.get_cleaned_time_length()
        start_time = form.get_cleaned_start_time()

        end_time = start_time + tdelta
        client_state.variables = json.dumps(svars)
        client_state.start_time = start_time
        client_state.timezone = form.cleaned_data['timezone']
        client_state.time_length = tdelta.total_seconds()
        client_state.track_real_time = form.cleaned_data['track_real_time']
        client_state.soundings = json.dumps(sel_soundings)
        client_state.yvariable = yvar
        client_state.save()

        # Re-create form if any values have been altered
        if form.clean_method_altered_data:
            post = request.POST.copy()
            post['start_time'] = form.cleaned_data['start_time']
            post['track_real_time'] = form.cleaned_data['track_real_time']
            form = nc_forms.DataSelectionForm(post, dataset=dset)

        form.set_variable_choices(variable_choices)
        form.set_yvariable_choices(variable_choices)

        try:
            if isinstance(dset, nc_models.FileDataset):
                ncdset = dset.get_netcdf_dataset()
                # a variable can be in a dataset, but not in a certain set of files.
                dsvars = ncdset.get_variables(
                    start_time=start_time, end_time=end_time)

            elif isinstance(dset, nc_models.DBDataset):
                dbcon = dset.get_connection()
                dsvars = dbcon.get_variables()

            if dset.dset_type == "sounding":
                # set sounding choices for selected time period
                # soundings between the start and end time
                sounding_choices = dset.get_series_names(
                    series_name_fmt=SOUNDING_NAME_FMT,
                    start_time=client_state.start_time,
                    end_time=client_state.start_time + \
                        datetime.timedelta(seconds=client_state.time_length))

                sounding_choices = [(s, s) for s in sounding_choices]
                form.fields['soundings'].choices = sounding_choices

        except (nc_exc.NoDataException, nc_exc.NoDataFoundException) as exc:
            _logger.warn("%s, %s: get_variables: %s", project_name, dset, exc)
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'variables': dsvars,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        # selected and available variables, using set intersection
        savail = list(set(svars) & set(dsvars.keys()))

        if len(savail) == 0:
            exc = nc_exc.NoDataException(
                "variables {} not found in {}".format(svars, dset))
            _logger.warn(repr(exc))
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'variables': dsvars,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        if yvar != "":
            if yvar not in dsvars.keys():
                exc = nc_exc.NoDataException(
                    "variable {} not found in {}".format(yvar, dset))
                _logger.warn(repr(exc))
                form.no_data(repr(exc))
                return render(
                    request, self.template_name,
                    {
                        'form': form,
                        'dataset': dset,
                        'variables': dsvars,
                        'soundings': mark_safe(json.dumps(soundings))
                    })

            svars.append(yvar)
            savail = list(set(svars) & set(dsvars.keys()))


        series_name_fmt = None
        if dset.dset_type == "sounding":
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
                    savail, start_time=start_time, end_time=end_time,
                    series=sel_soundings,
                    series_name_fmt=series_name_fmt)
            else:
                ncdata = dbcon.read_time_series(
                    savail, start_time=start_time, end_time=end_time)

        except OSError as exc:
            _logger.error("%s, %s: %s", project_name, dataset_name, exc)
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'variables': dsvars,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        except nc_exc.TooMuchDataException as exc:
            _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
            form.too_much_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'variables': dsvars,
                    'soundings': mark_safe(json.dumps(soundings))
                })

        except (nc_exc.NoDataException, nc_exc.NoDataFoundException) as exc:
            _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
            form.no_data(repr(exc))
            return render(
                request, self.template_name,
                {
                    'form': form,
                    'dataset': dset,
                    'variables': dsvars,
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
                    except IndexError:  # all data is nan
                        time_last_ok = (start_time - \
                            datetime.timedelta(seconds=0.001)).timestamp()

                    try:
                        time_last = ncdata['time'][series_name][-1]
                    except IndexError:  # no data
                        time_last = time_last_ok

                    client_state.save_data_times(vname, time_last_ok, time_last)

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
            # one series, named ''
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
                    vnames = sorted([v for v in variables])
                    units = [variables[v]['units'] for v in vnames]
                    long_names = [variables[v]['long_name'] for v in vnames]
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
                # first variable which uses it. In this way the plots
                # are in alphabetical order on the page by the first plotted variable.
                uunits = []
                # sorted(dict) becomes a list of sorted keys
                for vname in sorted(variables):
                    units = variables[vname]['units']
                    if not units in uunits:
                        uunits.append(units)

                # unique units
                for units in uunits:
                    uvars = sorted([vname for vname, var in variables.items() \
                        if var['plot_type'] == ptype and var['units'] == units])
                    # uvars is a sorted list of variables with units and this plot type.
                    # Might be empty if the variable is of a different plot type
                    if len(uvars) > 0:
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
                'variables': dsvars,
                'plot_groups': plot_groups,
                'time0': mark_safe(time0),
                'time': mark_safe(time),
                'data': mark_safe(data),
                'dim2': mark_safe(dim2),
                'time_length': client_state.time_length,
                'soundings': mark_safe(json.dumps(soundings)),
                'yvariable': mark_safe(yvar),
                })

class DataView(View):
    """Respond to ajax request for data.
    """

    def get(self, request, *args, project_name, dataset_name, **kwargs):
        """Respond to a ajax get request.

        """

        debug = False

        ajax_data = {}

        try:
            client_state = get_client_from_session(
                request.session, project_name, dataset_name)
        except Http404 as exc:
            _logger.error("AJAX DataView get: " + exc)
            ajax_data['redirect'] = \
                request.build_absolute_uri(
                    reverse(
                        'ncharts:dataset',
                        kwargs={
                            'project_name': project_name,
                            'dataset_name':dataset_name,
                        }))
            ajax_data['message'] = exc

            return HttpResponse(
                json.dumps(ajax_data),
                content_type="application/json")

        dset = get_dataset(client_state)

        if isinstance(dset, nc_models.FileDataset):
            ncdset = dset.get_netcdf_dataset()
        elif isinstance(dset, nc_models.DBDataset):
            try:
                dbcon = dset.get_connection()
            except nc_exc.NoDataFoundException as exc:
                _logger.warn(
                    "%s, %s, %d, database connection failed: %s",
                    project_name, dataset_name, client_state.id, exc)
                ajax_data['redirect'] = \
                    request.build_absolute_uri(
                        reverse(
                            'ncharts:dataset',
                            kwargs={
                                'project_name': project_name,
                                'dataset_name':dataset_name,
                            }))
                ajax_data['message'] = exc
                return HttpResponse(
                    json.dumps(ajax_data),
                    content_type="application/json")

        # selected variables
        svars = json.loads(client_state.variables)

        if not len(svars):
            _logger.warn(
                "%s, %s: variables not found for id=%d",
                project_name, dataset_name, client_state.id)
            ajax_data['redirect'] = \
                request.build_absolute_uri(
                    reverse(
                        'ncharts:dataset',
                        kwargs={
                            'project_name': project_name,
                            'dataset_name':dataset_name,
                        }))
            ajax_data['message'] = "No selected variables"
            return HttpResponse(
                json.dumps(ajax_data),
                content_type="application/json")

        timezone = client_state.timezone

        for vname in svars:

            # timetag of last non-nan sample for this variable sent to client
            # timetag of last sample for this variable sent to client
            [time_last_ok, time_last] = client_state.get_data_times(vname)
            if not time_last_ok:
                _logger.warn(
                    "%s, %s: data times not found for client id=%d, " \
                    "variable=%s",
                    project_name, dataset_name, client_state.id, vname)
                continue

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
                    # All data nan. Only send those after time_last.
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
                continue
            except nc_exc.TooMuchDataException as exc:
                _logger.warn("%s, %s: %s", project_name, dataset_name, exc)
                continue
            except (nc_exc.NoDataException, nc_exc.NoDataFoundException, KeyError) as exc:
                # KeyError: variable not found in data
                if debug:
                    _logger.debug(
                        "Dataview Get: %s, %s ,%s: variable=%s, "
                        ", time_last=%s",
                        project_name, dataset_name, exc, vname,
                        datetime.datetime.fromtimestamp(
                            time_last, tz=timezone).isoformat())
                continue

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

            ajax_data[vname] = {
                'time0': time0,
                'time': time,
                'data': data,
                'dim2': dim2
            }

        # jstr = json.dumps(ajax_data)
        # _logger.debug("json data=%s",jstr)
        # return HttpResponse(jstr, content_type="application/json")
        return HttpResponse(
            json.dumps(ajax_data),
            content_type="application/json")

