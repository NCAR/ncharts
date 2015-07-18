# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set tabstop=8 shiftwidth=4 softtabstop=4 expandtab:

"""Forms used by ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

from django import forms
from django.contrib import messages

from datetimewidget import widgets as dt_widgets

import pytz

# from django.utils.encoding import force_text
# from django.utils.safestring import mark_safe

import datetime

import sys, logging

_logger = logging.getLogger(__name__)   # pylint: disable=invalid-name

TIME_UNITS_CHOICES = ['day', 'hour', 'minute', 'second']
TIME_LEN_CHOICES = [1, 2, 4, 5, 7, 8, 12, 24, 30]

class FloatWithChoiceWidget(forms.MultiWidget):
    """MultiWidget for use with FloatWithChoiceField.

    First widget is a TextInput so that user can enter any float value,
    second is a Select widget for quick selection from a list.

    """

    def __init__(self, choices, attrs=None):
        """Create the two widgets.

        """
        _widgets = [
            forms.TextInput(attrs=attrs),
            forms.Select(choices=choices, attrs=attrs)
        ]
        super().__init__(_widgets)

    def decompress(self, value):
        """Takes a single "compressed" value from the field, and returns
        a list of two values for the two widgets.

        Complement to FloatWithChoiceField compress method.

        Returns:
            List containing two string values, the first for the TextInput
            widget, the second for the Select widget.
        """

        # print("decompress, type(value)=", type(value),
        #         ",value=", repr(value))
        if not value:
            return ['1', '1']
        try:
            val = float(value)
            if val % 1 == 0:
                value = '{:.0f}'.format(val)
            if not val in TIME_LEN_CHOICES:
                return [value, '0']
        except ValueError:
            value = '1'
        return [value, value]

class FloatWithChoiceField(forms.MultiValueField):
    """ChoiceField with an option for a user-submitted "other" value.

    The last item in the choices array passed to __init__ is expected
    to be a choice for "other". This field's cleaned data is a tuple
    consisting of the choice the user made, and the "other" field
    typed in if the choice made was the last one.
    """

    def __init__(self, *args, choices=[], coerce=float,
                 min_value=sys.float_info.min, max_value=sys.float_info.max,
                 **kwargs):

        self.coerce = coerce

        # choices = kwargs.pop('choices', [])
        # min_value = kwargs.pop('min_value', sys.float_info.min)
        # max_value = kwargs.pop('max_value', sys.float_info.max)

        fields = [
            forms.FloatField(
                *args, min_value=min_value, max_value=max_value,
                required=False, **kwargs),
            # Like a ChoiceField, but with a coerce function.
            forms.TypedChoiceField(
                *args, choices=choices, coerce=coerce, **kwargs),
        ]

        widget = FloatWithChoiceWidget(choices=choices)

        super().__init__(
            *args, widget=widget, fields=fields,
            require_all_fields=False, **kwargs)

    def compress(self, value):
        """Return a single value for this field from the two component fields.

        First value comes from the FloatField/TextInput widget, second from
        the TypedChoiceField/Select widget. Both values are floats.

        The render method of the FloatWithChoiceWidget generates
        javascript that updates the TextInput if the user
        selects from the Select widget. Therefore, the value
        result from this MultiValueField is value[0], from the
        FloatField/TextInput widget.
        """

        # print("compress, type(value)=", type(value), ",value=", value)
        if not value or not isinstance(value, list) or len(value) != 2:
            raise ValueError("value not a list of length 2")

        # The values may not be equal if the text widget was
        # the most recently updated.

        # Return the text widget value
        return value[0]

def timezone_coerce(tzstr):
    """Function to coerce a string to a timezone.
    """
    try:
        return pytz.timezone(tzstr)
    except pytz.UnknownTimeZoneError as exc:
        _logger.error("timezone_coerce: %s", exc)
    return pytz.utc

class DataSelectionForm(forms.Form):
    """Form for selection of dataset parameters, such as time and variables.

    """

    variables = forms.MultipleChoiceField(
        label='Variables:',
        required=True, widget=forms.CheckboxSelectMultiple(
            attrs={
                # 'data-mini': 'true'
            }))

    timezone = forms.TypedChoiceField(
        required=True,
        label="time zone",
        coerce=timezone_coerce)

    # pickerPosition: bottom-right, bottom-left
    #       popup calendar box is to lower left or right of textbox & icon
    start_time = forms.DateTimeField(
        widget=dt_widgets.DateTimeWidget(
            bootstrap_version=3,
            options={
                'format': 'yyyy-mm-dd hh:ii',
                'clearBtn': 0,
                'todayBtn': 1,
                'pickerPosition': 'bottom-right'
            }))

    # this should only be enabled if the end time of the project
    # is in the future.
    track_real_time = forms.BooleanField(required=False, initial=False)

    # choices: (value, label)
    time_length = FloatWithChoiceField(
        choices=[(str(i), str(i),) for i in TIME_LEN_CHOICES],
        label='Time length', min_value=0)

    time_length_units = forms.ChoiceField(
        choices=[(c, c,) for c in TIME_UNITS_CHOICES],
        initial=TIME_UNITS_CHOICES[0], label='')

    soundings = forms.MultipleChoiceField(
        label='Soundings',
        required=False, widget=forms.CheckboxSelectMultiple(
            attrs={
                # 'data-mini': 'true'
            }))

    # Variable to plot on Y axis in sounding plot. Only
    # required for a sounding
    yvariable = forms.ChoiceField(
        label='Variable to plot on Y axis in sounding plot',
        required=False)

    def __init__(self, *args, dataset=None, request=None, **kwargs):
        """Set choices for time zone from dataset.

        Raises:
        """

        super().__init__(*args, **kwargs)

        self.dataset = dataset
        self.request = request
        self.clean_method_altered_data = False

        if len(dataset.timezones.all()) > 0:
            self.fields['timezone'].choices = \
                [(v.tz, str(v.tz)) for v in dataset.timezones.all()]
        else:
            proj = dataset.project
            self.fields['timezone'].choices = \
                [(v.tz, str(v.tz)) for v in proj.timezones.all()]


    def set_variable_choices(self, variables):
        """Set the available variables in this form.

        Args:
            variables: list of variable names.
        """
        # choices: (value, label)
        self.fields['variables'].choices = [(v, v) for v in variables]

    def set_yvariable_choices(self, variables):
        """Set the available Y axis variables in this form.

        Args:
            variables: list of variable names.
        """
        # choices: (value, label)
        self.fields['yvariable'].choices = [(v, v) for v in variables]


    def clean(self):
        """Check the user's selections for correctness.

        If the user has selected a start_time outside of the dataset's time
        period, the value of cleaned_data['start_time'] will be updated
        to be within the dataset period.  A message will be added to the
        request to indicate what has happened.

        Likewise, set cleaned_data['track_real_time'] to False if the current
        time is after the end of the dataset.

        If either field has been altered, set self.clean_method_altered_data=True
        so that the view method knows to generate a new form with the altered values.

        Returns:
            A dictionary of cleaned_data. As of django 1.7 this is no longer required.

        """

        cleaned_data = super().clean()

        timezone = cleaned_data['timezone']
        tnow = datetime.datetime.now(timezone)
        post_real_time = tnow > self.dataset.end_time

        if post_real_time:
            if cleaned_data['track_real_time']:
                self.clean_method_altered_data = True
            cleaned_data['track_real_time'] = False
            self.fields['track_real_time'].widget.attrs['disabled'] = True

        # the time fields are in the browser's timezone. Use those exact fields,
        # but interpret them in the dataset timezone
        start_time = self.get_cleaned_start_time()

        if start_time < self.dataset.get_start_time():
            msg = "chosen start time: {} is earlier than " \
                "dataset start time, resetting to {}".format(
                    start_time.isoformat(),
                    self.dataset.get_start_time().astimezone(timezone).isoformat())
            if self.request:
                messages.warning(self.request, msg)
            # self.add_error('start_time', forms.ValidationError(msg))
            start_time = self.dataset.get_start_time().astimezone(timezone)
            cleaned_data['start_time'] = start_time.replace(tzinfo=None)
            self.clean_method_altered_data = True

        tunits = cleaned_data['time_length_units']

        if not tunits in TIME_UNITS_CHOICES:
            raise forms.ValidationError('invalid time units: {}'.format(tunits))

        if not 'time_length' in cleaned_data:
            self.add_error('time_length', forms.ValidationError('invalid time length'))

        tdelta = self.get_cleaned_time_length()

        if tdelta.total_seconds() <= 0:
            msg = "time length must be positive"
            self.add_error('time_length', forms.ValidationError(msg))

        if cleaned_data['track_real_time']:
            start_time = (tnow - tdelta).astimezone(timezone)
            cleaned_data['start_time'] = start_time.replace(tzinfo=None)
            self.clean_method_altered_data = True
        elif start_time > self.dataset.get_end_time():
            new_start_time = (self.dataset.get_end_time() - tdelta).astimezone(timezone)
            msg = "chosen start time: {} is later than " \
                "dataset end time: {}, resetting to {}".format(
                    start_time.isoformat(),
                    self.dataset.get_end_time().astimezone(timezone).isoformat(),
                    new_start_time.isoformat())
            if self.request:
                messages.warning(self.request, msg)
            # self.add_error('start_time', forms.ValidationError(msg))
            start_time = new_start_time
            cleaned_data['start_time'] = start_time.replace(tzinfo=None)
            self.clean_method_altered_data = True

        if not 'variables' in cleaned_data or len(cleaned_data['variables']) == 0:
            self.add_error('variables', forms.ValidationError('no variables selected'))

        if self.dataset.dset_type == "sounding":
            if not 'soundings' in cleaned_data or \
                len(cleaned_data['soundings']) == 0:
                self.add_error('soundings', forms.ValidationError('no soundings selected'))

        return cleaned_data

    def get_cleaned_time_length(self):
        """Return the time period length chosen by the user.

        Returns:
            a datetime.timedelta.
        """

        tlen = self.cleaned_data['time_length']   # normalized to float

        tunits = self.cleaned_data['time_length_units']     # string

        return get_time_length(tlen, tunits)

    def get_cleaned_start_time(self):
        """Return a timezone aware start_time from cleaned_data of the form.

        Returns:
            A datetime.datetime, within the timezone of cleaned_data['timezone'].

        """
        start_time = self.cleaned_data['start_time']
        timezone = self.cleaned_data['timezone']

        # start_time in cleaned data at this point is timezone aware, but
        # with the browser's timezone
        """
        A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None. If d.tzinfo is
        None, or if d.tzinfo is not None but d.tzinfo.utcoffset(d)
        returns None, d is naive.
        if start_time.tzinfo == None or
            start_time.tzinfo.utcoffset(start_time) == None:
            _logger.debug("form clean start_time is timezone naive")
        else:
            _logger.debug("form clean start_time is timezone aware")
        """

        # the time fields are in the browser's timezone. Use those exact fields,
        # but interpret them in the dataset timezone
        return timezone.localize(start_time.replace(tzinfo=None))


    def too_much_data(self, exc):
        """Set an error on this form. """
        self.errors['__all__'] = self.error_class([repr(exc)])

    def no_data(self, exc):
        """Set an error on this form. """
        self.errors['__all__'] = self.error_class([repr(exc)])

    def data_not_available(self, exc):
        """Set an error on this form. """
        self.errors['__all__'] = self.error_class([repr(exc)])

    # def get_files(self):
    #     return self.files

def get_time_length(tval, tunits):
    """From a time length and string of units, return a timedelta.

    Args:
        tval: a length of time
        tunits: the units of tval: 'day', 'hour', 'minute' or 'seconds'
    Returns:
        a datetime.timedelta.
    """

    if isinstance(tval, str):
        tval = float(tval)

    if tunits == 'day':
        return datetime.timedelta(days=tval)
    elif tunits == 'hour':
        return datetime.timedelta(hours=tval)
    elif tunits == 'minute':
        return datetime.timedelta(minutes=tval)
    else:
        return datetime.timedelta(seconds=tval)

def get_time_length_fields(tdelta):
    """From a timedeltat, or time length in seconds, return
    values of a length and a string tunits.

    Args:
        tdelta: a datetime.timedelta or a number of seconds

    Returns:
        (tval, tunits), where tval is a numeric time length and tunits
            are the units of tval: 'day', 'hour', 'minute' or 'seconds'.
    """

    if isinstance(tdelta, datetime.timedelta):
        tdelta = tdelta.total_seconds()

    if tdelta >= datetime.timedelta(days=1).total_seconds():
        tunits = 'day'
        tdelta /= 86400
    elif tdelta >= datetime.timedelta(hours=1).total_seconds():
        tunits = 'hour'
        tdelta /= 3600
    elif tdelta >= datetime.timedelta(minutes=1).total_seconds():
        tunits = 'minute'
        tdelta /= 60
    else:
        tunits = 'second'

    return (tdelta, tunits)

