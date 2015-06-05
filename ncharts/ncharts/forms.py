# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set tabstop=8 shiftwidth=4 softtabstop=4 expandtab:

"""Forms used by ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

from django import forms

from datetimewidget import widgets

import pytz

# from django.utils.encoding import force_text
from django.utils.safestring import mark_safe

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

    def render(self, name, value, attrs=None):
        """Returns HTML for the widget, as a Unicode string.

        """

        html = super().render(name, value, attrs)

        # add javascript to set the value of the text field
        # from the selection.
        # TODO: do the reverse. If a users enters a value in the
        # text field that matches a choice, update the selection.
        html += '''<script>
            (function($) {
                $("select#%(id)s_1").change(function() {
                    $("input#%(id)s_0").val(this.value);
                });
            })(jQuery);
            </script>''' % {'id': attrs['id']}

        return mark_safe(html)

    def format_output_unused(self, rendered_widgets):
        """Given a list of rendered widgets (as strings), returns a
        Unicode string representing the HTML for the whole lot.

        Probably could use the super method.
        """

        return u''.join(rendered_widgets)

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
        required=True, widget=forms.CheckboxSelectMultiple(
            attrs={'data-mini': 'true'}),
        label='Variables:')

    timezone = forms.TypedChoiceField(
        required=True,
        label="time zone",
        coerce=timezone_coerce)

    # pickerPosition: bottom-right, bottom-left
    #       popup calendar box is to lower left or right of textbox & icon
    start_time = forms.DateTimeField(
        widget=widgets.DateTimeWidget(
            bootstrap_version=3, options={
                'format': 'yyyy-mm-dd hh:ii', 'clearBtn': 0, 'todayBtn': 1,
                # 'format': 'YYYY-MM-DD HH:mm', 'clearBtn': 0, 'todayBtn': 1,
                'pickerPosition': 'bottom-right'}))

    # choices: (value, label)
    time_length = FloatWithChoiceField(
        choices=[(str(i), str(i),) for i in TIME_LEN_CHOICES],
        label='Time length', min_value=0)

    time_length_units = forms.ChoiceField(
        choices=[(c, c,) for c in TIME_UNITS_CHOICES],
        initial=TIME_UNITS_CHOICES[0], label='')

    def __init__(self, *args, dataset=None, **kwargs):
        """Set choices for variables and time zone from dataset.
        """

        super().__init__(*args, **kwargs)

        self.dataset = dataset
        dvars = sorted(dataset.get_variables().keys())
        self.fields['variables'].choices = [(v, v) for v in dvars]

        if len(dataset.timezones.all()) > 0:
            self.fields['timezone'].choices = \
                [(v.tz, str(v.tz)) for v in dataset.timezones.all()]
        else:
            proj = dataset.project
            self.fields['timezone'].choices = \
                [(v.tz, str(v.tz)) for v in proj.timezones.all()]

        self.fields['variables'].choices = [(v, v) for v in dvars]

    def clean(self):
        """ """

        '''
        print('DataSelectionForm clean')
        print("cleaned_data=", cleaned_data)
        '''

        cleaned_data = super().clean()

        start_time = cleaned_data['start_time']
        timezone = cleaned_data['timezone']

        # start_time in cleaned data is timezone aware, but
        # with the browser's timezone
        """
        A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None. If d.tzinfo is
        None, or if d.tzinfo is not None but d.tzinfo.utcoffset(d)
        returns None, d is naive.
        if start_time.tzinfo == None or
            start_time.tzinfo.utcoffset(start_time) == None:
            print("form clean start_time is timezone naive")
        else:
            print("form clean start_time is timezone aware")
        """

        # the time fields are in the browser's timezone. Use those exact fields,
        # but interpret them in the dataset timezone
        start_time = timezone.localize(start_time.replace(tzinfo=None))

        # Allow user to be sloppy by a week
        if start_time < self.dataset.get_start_time() - \
                datetime.timedelta(days=7):
            msg = "chosen start time: {} is earlier than " \
                "dataset start time: {}".format(
                    start_time.isoformat(),
                    self.dataset.get_start_time().isoformat())
            self._errors['start_time'] = self.error_class([msg])
            raise forms.ValidationError(msg)

        cleaned_data['start_time'] = start_time

        tunits = cleaned_data['time_length_units']

        if not tunits in TIME_UNITS_CHOICES:
            raise forms.ValidationError('invalid time units: {}'.format(tunits))

        if not 'time_length' in cleaned_data:
            raise forms.ValidationError('invalid time length')

        tval = cleaned_data['time_length']

        if tunits == 'day':
            tdelta = datetime.timedelta(days=tval)
        elif tunits == 'hour':
            tdelta = datetime.timedelta(hours=tval)
        elif tunits == 'minute':
            tdelta = datetime.timedelta(minutes=tval)
        else:
            tdelta = datetime.timedelta(seconds=tval)

        if tdelta.total_seconds() <= 0:
            msg = "time length must be positive"
            raise forms.ValidationError(msg)

        end_time = start_time + tdelta

        if not 'variables' in cleaned_data or \
            len(cleaned_data['variables']) == 0:
            raise forms.ValidationError('no variables selected')

        return cleaned_data

    def get_cleaned_time_length(self):
        """Return the time period length chosen by the user.

        Returns:
            a datetime.timedelta.
        """

        tlen = self.cleaned_data['time_length']   # normalized to float

        tunits = self.cleaned_data['time_length_units']     # string

        if tunits == 'day':
            return datetime.timedelta(days=tlen)
        elif tunits == 'hour':
            return datetime.timedelta(hours=tlen)
        elif tunits == 'minute':
            return datetime.timedelta(minutes=tlen)
        else:
            return datetime.timedelta(seconds=tlen)

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
    """From string values of tval and tunits, return a timedelta.
    """

    tval = float(tval)

    if tunits == 'day':
        return datetime.timedelta(days=tval)
    elif tunits == 'hour':
        return datetime.timedelta(hours=tval)
    elif tunits == 'minute':
        return datetime.timedelta(minutes=tval)
    else:
        return datetime.timedelta(seconds=tval)


