# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:
#
# 2014 Copyright University Corporation for Atmospheric Research
# 
# This file is part of the "django-ncharts" package.
# The license and distribution terms for this file may be found in the
# file LICENSE in this package.

from django import forms
from datetimewidget.widgets import DateTimeWidget

from ncharts.models import Variable

from pytz import timezone, utc
import datetime

import logging

logger = logging.getLogger(__name__)

time_units_choices = {'day': 'day', 'hour': 'hour', 'minute': 'minute', 'second': 'second' }
# time_units_choices = ['day', 'hour', 'minute', 'second']
time_len_choices = [1,4,5,7,8,12,24,30]

class DatasetSelectionForm(forms.Form):
    ''' '''

    variables = forms.MultipleChoiceField(required=True,
            widget=forms.CheckboxSelectMultiple,label='Variables:')

    # pickerPosition: bottom-right, bottom-left
    #       popup calendar box is to lower left or right of textbox & icon
    start_time = forms.DateTimeField(
        widget=DateTimeWidget(
            bootstrap_version=3,options={'format': 'yyyy-mm-dd hh:ii',
            'clearBtn': 0, 'todayBtn': 1, 'pickerPosition': 'bottom-right'}))

    # choices: (value,label)
    strchoices = [(str(i),str(i),) for i in time_len_choices]
    strchoices[:0] = [('0','other->',)]
    time_length_choice = forms.TypedChoiceField(choices=strchoices,coerce=float,
            initial=strchoices[1][0],label='Time length')

    time_length_val = forms.FloatField(min_value=0,initial=0,label='',required=False)

    time_length_units = forms.ChoiceField(
            choices=[(c,c,) for c in time_units_choices.values()],
            initial=time_units_choices['hour'],label='')

    def __init__(self, *args, dataset=None, selected=[], start_time=None, time_length=None, **kwargs):

        super().__init__(*args,**kwargs)

        # dataset is not a Field, must be set in __init__ whether this form is bound or not
        self.dataset = dataset

        # choices is a list of tuples: (value,label)
        if not hasattr(self.fields['variables'],'choices') or len(self.fields['variables'].choices) == 0:
            logger.debug("form variables has no choices, form is_bound=%s",self.is_bound)
            dvars = sorted(dataset.get_variables().keys())
            self.fields['variables'].choices = [ (v,v) for v in dvars ]
        else:
            logger.debug("variables choices=%s",repr(self.fields['variables'].choices))

        # files is not a Field
        self.files = []

        # bound to data: capable of validating that data and rendering it as HTML
        # unbound: no data to validate
        if not self.is_bound:

            self.fields['start_time'].label = "Start time (timezone={})".format(dataset.timezone)

            dtz = self.dataset.get_timezone()

            # initial selected variables
            self.fields['variables'].initial = selected

            # start_time will be timezone aware
            '''
            if start_time.tzinfo == None or start_time.tzinfo.utcoffset(start_time) == None:
                logger.debug("form __init__ start_time is timezone naive")
            else:
                logger.debug("form __init__ start_time is timezone aware")
            '''

            # convert to dataset timezone
            self.fields['start_time'].initial = datetime.datetime.fromtimestamp(start_time.timestamp(),tz=dtz)

            if not time_length:
                time_length = datetime.timedelta(days=1)
            elif not isinstance(time_length,datetime.timedelta):
                time_length = datetime.timedelta(seconds=time_length)

            tlen = time_length.total_seconds()

            if tlen >= datetime.timedelta(days=1).total_seconds():
                tunits = time_units_choices['day']
                tlen /= 86400
            elif tlen >= datetime.timedelta(hours=1).total_seconds():
                tunits = time_units_choices['hour']
                tlen /= 3600
            elif tlen >= datetime.timedelta(minutes=1).total_seconds():
                tunits = time_units_choices['minute']
                tlen /= 60
            else:
                tunits = time_units_choices['second']

            if tlen in time_len_choices:
                tother = 0
            else:
                tlen = 0
                tother = tlen

            tlen = '{:f}'.format(tlen)
            '''
            print("tlen=",tlen,", tother=",tother)

            print("type(self.fields['time_length_choice'].initial)=",
                type(self.fields['time_length_choice'].initial))
            '''
            self.fields['time_length_units'].initial = tunits
            self.fields['time_length_choice'].initial = tlen
            self.fields['time_length_val'].initial = tother

    def clean(self):
        '''
        print('DatasetSelectionForm clean')
        print("cleaned_data=",cleaned_data)
        '''

        cleaned_data = super().clean()

        dtz = self.dataset.get_timezone()
        # print("dtz=",dtz)
        t1 = cleaned_data['start_time']

        # start_time in cleaned data is timezone aware
        '''
        A datetime object d is aware if d.tzinfo is not None and d.tzinfo.utcoffset(d)
        does not return None. If d.tzinfo is None, or if d.tzinfo is not None but
        d.tzinfo.utcoffset(d) returns None, d is naive. 
        if t1.tzinfo == None or t1.tzinfo.utcoffset(t1) == None:
            print("form clean start_time is timezone naive")
        else:
            print("form clean start_time is timezone aware")
        '''

        # the time fields are in the browser's timezone. Use those exact fields, but interpret
        # them in the dataset timezone
        t1 = dtz.localize(t1.replace(tzinfo=None))

        # Allow user to be sloppy by a week
        if t1 < self.dataset.get_start_time() - datetime.timedelta(days=7):
            msg = "chosen start time: {} is earlier than dataset start time: {}".format(
                t1.isoformat(),self.dataset.get_start_time().isoformat())
            self._errors['start_time'] = self.error_class([msg])
            raise forms.ValidationError(msg)

        cleaned_data['start_time'] = t1
        
        tunits = cleaned_data['time_length_units']

        if not tunits in time_units_choices:
            raise forms.ValidationError('invalid time units: {}'.format(tunits))

        tchoice = cleaned_data['time_length_choice']
        tval = cleaned_data['time_length_val']

        if tchoice > 0:
            tval = tchoice

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

        t2 = t1 + tdelta

        if not 'variables' in cleaned_data or len(cleaned_data['variables']) == 0:
            raise forms.ValidationError('no variables selected')

        fset = self.dataset.get_fileset()

        self.files = [f.path for f in fset.scan(t1,t2)]

        if len(self.files) == 0:
            msg = "no files found between {} and {}".format(
                t1.isoformat(),t2.isoformat())
            raise forms.ValidationError(msg)

        return cleaned_data


    def get_cleaned_time_length(self):
        '''
        '''

        tchoice = self.cleaned_data['time_length_choice']   # normalized to float
        tlen = self.cleaned_data['time_length_val']         # float
        tunits = self.cleaned_data['time_length_units']     # string

        if tchoice > 0:
            tlen = tchoice

        if tunits == 'day':
            return datetime.timedelta(days=tlen)
        elif tunits == 'hour':
            return datetime.timedelta(hours=tlen)
        elif tunits == 'minute':
            return datetime.timedelta(minutes=tlen)
        else:
            return datetime.timedelta(seconds=tlen)

    def too_much_data(self,e):
        self.errors['__all__'] = self.error_class([repr(e)])

    def no_data(self,e):
        self.errors['__all__'] = self.error_class([repr(e)])


    def get_files(self):
        return self.files

def get_time_length(tchoice,tval,tunits):
    '''
    From string values of tchoice, tval and tunits, 
    return a timedelta.
    '''

    if tchoice != '0' and tchoice != '':
        tval = float(tchoice)
    else:
        tval = float(tval)

    if tunits == 'day':
        return datetime.timedelta(days=tval)
    elif tunits == 'hour':
        return datetime.timedelta(hours=tval)
    elif tunits == 'minute':
        return datetime.timedelta(minutes=tval)
    else:
        return datetime.timedelta(seconds=tval)

