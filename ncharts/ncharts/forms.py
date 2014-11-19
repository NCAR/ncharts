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
from datetime import datetime

class DatasetSelectionForm(forms.Form):
    ''' '''

    variables = forms.MultipleChoiceField(required=False,
            widget=forms.CheckboxSelectMultiple,label='Variables:')

    # pickerPosition: bottom-right, bottom-left
    #       popup calendar box is to lower left or right of textbox & icon
    start_time = forms.DateTimeField(
        widget=DateTimeWidget(
            bootstrap_version=3,options={'format': 'yyyy-mm-dd hh:ii',
            'clearBtn': 0, 'todayBtn': 1, 'pickerPosition': 'bottom-right'}))

    end_time = forms.DateTimeField(
        widget=DateTimeWidget(
            bootstrap_version=3,options={'format': 'yyyy-mm-dd hh:ii',
            'clearBtn': 0,'todayBtn': 1, 'pickerPosition': 'bottom-right'}))

    def __init__(self,*args,dataset=None,selected=[],
            start_time=None,end_time=None,
             **kwargs):

        super().__init__(*args,**kwargs)

        self.dataset = dataset

        # print("form is_bound=",self.is_bound)

        self.fields['start_time'].label = "Start time (timezone={})".format(dataset.timezone)
        self.fields['end_time'].label = "End time (timezone={})".format(dataset.timezone)

        if not self.is_bound:
            # initial selected variables
            self.fields['variables'].initial = selected
            self.fields['start_time'].initial = start_time
            self.fields['end_time'].initial = end_time

        dvars = sorted(dataset.get_variables().keys())

        # choices is a list of tuples: (value,label)
        self.fields['variables'].choices = [ (v,v) for v in dvars ]

        self.files = []

    def clean(self):
        '''
        print('DatasetSelectionForm clean')
        print("cleaned_data=",cleaned_data)
        '''

        cleaned_data = super().clean()

        dtz = self.dataset.get_timezone()
        # print("dtz=",dtz)
        t1 = dtz.localize(cleaned_data['start_time'].replace(tzinfo=None))
        t2 = dtz.localize(cleaned_data['end_time'].replace(tzinfo=None))

        if t1 < self.dataset.get_start_time():
            msg = "chosen start time: {} is earlier than dataset start time: {}".format(
                t1.isoformat(),self.dataset.get_start_time().isoformat())
            self._errors['start_time'] = self.error_class([msg])
            raise forms.ValidationError(msg)

        if t2 > self.dataset.get_end_time():
            msg = "chosen end time: {} is later than dataset end time: {}".format(
            t2.isoformat(),self.dataset.get_end_time().isoformat())
            self._errors['end_time'] = self.error_class([msg])
            raise forms.ValidationError(msg)

        if t1 >= t2:
            msg = "chosen start time: {} is later than end time: {}".format(
                t1.isoformat(),t2.isoformat())
            raise forms.ValidationError(msg)

        cleaned_data['start_time'] = t1
        cleaned_data['end_time'] = t2

        if len(cleaned_data['variables']) == 0:
            raise forms.ValidationError('no variables selected')

        fset = self.dataset.get_fileset()

        self.files = [f.path for f in fset.scan(cleaned_data['start_time'],cleaned_data['end_time'])]

        if len(self.files) == 0:
            msg = "no files found between {} and {}".format(
                t1.isoformat(),t2.isoformat())
            raise forms.ValidationError(msg)

        return cleaned_data

    def get_files(self):
        return self.files

