# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""
2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

import os

from django import test

from ncharts import models as nc_models
from ncharts import forms as nc_forms
from ncharts import netcdf as nc_netcdf

from datetime import datetime, timedelta
from pytz import timezone, utc

from django.conf import settings

import numpy.testing as ntp

class ModelTestCase(test.TestCase):

    def setUp(self):
        """Create some models. """

        utctz = nc_models.TimeZone.objects.create(tz='UTC')
        mtntz = nc_models.TimeZone.objects.create(tz='US/Mountain')

        nc_models.Project.objects.create(
            name="Weather"
        )

        proj = nc_models.Project.objects.create(
            name="SCP",
            location='Pawnee Grasslands')

        proj.timezones.add(utctz)
        proj.timezones.add(mtntz)

        nc_models.Platform.objects.create(name="ISFS")
        nc_models.Platform.objects.create(name="ISS")
        nc_models.Platform.objects.create(name="S-Pol")

        nc_models.FileDataset.objects.create(
            name='scp_geo_tilt_cor',
            directory=os.path.join(
                settings.BASE_DIR,
                'ncharts/tests/data/netcdf_scp_geo_tilt_cor'),
            filenames='isfs_qc_gtc_%Y%m%d.nc',
            start_time=datetime(2012, 9, 20, 0, 0, 0, tzinfo=utc),
            end_time=datetime(2012, 10, 11, 0, 0, 0, tzinfo=utc),
            project=nc_models.Project.objects.get(name="SCP"))


    def test_models(self):

        projs = nc_models.Project.objects.all()
        self.assertEqual(len(projs), 2)

        utctz = nc_models.TimeZone.objects.get(tz='UTC')
        mtntz = nc_models.TimeZone.objects.get(tz='US/Mountain')

        plats = nc_models.Platform.objects.all()
        self.assertEqual(len(plats), 3)

        isfs = nc_models.Platform.objects.filter(name="ISFS")[0]
        iss = nc_models.Platform.objects.filter(name="ISS")[0]
        spol = nc_models.Platform.objects.filter(name="S-Pol")[0]

        mtn = timezone("US/Mountain")

        self.assertEqual(len(isfs.projects.all()), 0)
        self.assertEqual(len(iss.projects.all()), 0)
        self.assertEqual(len(spol.projects.all()), 0)

        dset = nc_models.FileDataset.objects.get(name='scp_geo_tilt_cor')

        # this should add the scp project to the isfs platform
        dset.add_platform(isfs)
        self.assertEqual(len(isfs.projects.all()), 1)

        scp = nc_models.Project.objects.get(name="SCP")
        # timezones were added to this project in setUp()
        self.assertEqual(len(scp.timezones.all()), 2)

        dset = nc_models.FileDataset.objects.create(
            name='scp_geo_notiltcor',
            directory=os.path.join(
                settings.BASE_DIR,
                'ncharts/tests/data/netcdf_scp_geo_notiltcor'),
            filenames='isfs_ntc_%Y%m%d.nc',
            start_time=datetime(2012, 9, 20, 0, 0, 0, tzinfo=utctz.tz),
            end_time=datetime(2012, 10, 11, 0, 0, 0, tzinfo=utctz.tz),
            project=scp)

        dset.add_platform(isfs)
        dset.add_platform(iss)
        dset.timezones.add(utctz)
        dset.timezones.add(mtntz)
        self.assertEqual(len(isfs.projects.all()), 1)
        self.assertEqual(len(iss.projects.all()), 1)

        self.assertEqual(len(scp.platform_set.all()), 2)

        dsets = nc_models.FileDataset.objects.filter(
            project__name__exact='SCP').filter(
                platforms__name__exact='ISFS')

        self.assertEqual(len(dsets), 2)

        client_state = nc_models.ClientState.objects.create(
            dataset = dset,
            timezone = "US/Mountain",
            start_time = datetime(2013, 9, 27, 0, 0, 0, tzinfo=utc),
            time_length = 86400,
            track_real_time = True
            )

        # print("dir(client_state)={}".format(dir(client_state)))

        # data_times methods:  all(), add(), filter(), get(), get_or_create(),
        # get_queryset()
        # print("dir(client_state.data_times)={}".format(dir(client_state.data_times)))
        # print("dir(client_state.data_times.all())={}".format(dir(client_state.data_times.all())))

        vart = nc_models.VariableTimes.objects.create(name="T",
                last_ok=0,last=1)
        client_state.data_times.add(vart)

        self.assertEqual(len(client_state.data_times.all()),1)

        vart = client_state.data_times.get(name="T")
        self.assertEqual(vart.last_ok,0)
        self.assertEqual(vart.last,1)

    def test_netcdf_dataset(self):

        ndays = 2

        # start time is 1 second past 0Z. This will require
        # (ndays+1) day-long files to be read.
        dset = nc_models.FileDataset.objects.get(name='scp_geo_tilt_cor')

        delta = timedelta(days=ndays)
        start_time = datetime(2012, 10, 1, 0, 0, 1, tzinfo=utc)
        end_time = start_time + delta

        rvars = ['w_1m', 'w_2m_C', 'counts_2m_C']

        ncset = dset.get_netcdf_dataset()

        files = ncset.get_filepaths(start_time, end_time)
        # for f in files:
        #     print(f)
        self.assertEqual(len(files), ndays+1)

        ncvars = ncset.get_variables()

        """
        print("")
        for v in ncvars:
            print(v)
        for s in ncset.station_names:
            print(s)
        """
        # There are several counts variables whose names
        # differ between files
        self.assertEqual(len(ncvars), 11)

        # rvars = ncvars[0:2]

        sdim = {'station': [-1, 4]}
        tsd = ncset.read_time_series(
            rvars, start_time, end_time, selectdim=sdim)

        # print("len(tsd['data'])={}".format(len(tsd['data'])))
        # print("len(tsd['data'][''])={}".format(len(tsd['data'][''])))
        # print("len(tsd['time'])={}".format(len(tsd['time'])))
        # print("len(tsd['time'][''])={}".format(len(tsd['time'][''])))

        # ndays of 5 minute data
        self.assertEqual(len(tsd['time']['']), 86400/(5*60) * ndays)
        self.assertEqual(len(tsd['data']['']), len(rvars))

        for var in tsd['data']['']:
            self.assertEqual(len(tsd['time']['']), tsd['data'][''][var].shape[0])
            self.assertTrue(
                tsd['data'][''][var].shape[1:] == (1,) or
                tsd['data'][''][var].shape[1:] == ())

        # check some data values for a given time
        xtime = datetime(2012, 10, 2, 0, 7, 30, tzinfo=utc).timestamp()

        self.assertTrue(xtime in tsd['time'][''])
        ixtime = tsd['time'][''].index(xtime)

        ixtime_expected = int((xtime-start_time.timestamp()) / (5*60))
        self.assertEqual(ixtime, ixtime_expected)

        # print("tsd['data']['w_1m'][ixtime]=",tsd['data']['w_1m'][ixtime])
        ntp.assert_almost_equal(tsd['data']['']['w_1m'][ixtime], -0.02494044)
        ntp.assert_almost_equal(tsd['data']['']['counts_2m_C'][ixtime], 6000)

        ntp.assert_allclose(tsd['data']['']['w_1m'][ixtime], -0.02494044)
        ntp.assert_allclose(tsd['data']['']['counts_2m_C'][ixtime], 6000)

