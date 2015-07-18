# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""Admin objects for ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

from django.contrib import admin
from ncharts import models as nc_models

class ProjectAdmin(admin.ModelAdmin):
    pass

admin.site.register(nc_models.Project, ProjectAdmin)

class PlatformAdmin(admin.ModelAdmin):
    pass

admin.site.register(nc_models.Platform, PlatformAdmin)

class FileDatasetAdmin(admin.ModelAdmin):
    pass

admin.site.register(nc_models.FileDataset, FileDatasetAdmin)

class DBDatasetAdmin(admin.ModelAdmin):
    pass

admin.site.register(nc_models.DBDataset, DBDatasetAdmin)

class ClientStateAdmin(admin.ModelAdmin):
    pass

admin.site.register(nc_models.ClientState, ClientStateAdmin)

