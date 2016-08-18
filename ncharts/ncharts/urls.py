# -*- mode: C++; indent-tabs-mode: nil; c-basic-offset: 4; tab-width: 4; -*-
# vim: set shiftwidth=4 softtabstop=4 expandtab:

"""URLs served by the ncharts django web app.

2014 Copyright University Corporation for Atmospheric Research

This file is part of the "django-ncharts" package.
The license and distribution terms for this file may be found in the
file LICENSE in this package.
"""

from django.conf.urls import patterns, url

from django.views.decorators.cache import never_cache

from ncharts import views

# format of a pattern:
#     regular expression, Python callback function
#         [, optional dictionary [, optional_name ]]
#
# url(regex,view,kwargs=None,name=None,prefix="")
#   name gives a name to the URL, so that the URL can be generated
#   where its needed, as in templates/ncharts/dataset.html.

# In django 1.8 urlpatterns should just be a list of url() instances.
# patterns() is deprecated.

urlpatterns = [
    url(r'^$', views.projects_platforms, name='projectsPlatforms'),

    url(r'^help/?$', views.StaticView.as_view(), {'page': 'ncharts/help.html'}),

    url(r'^projects/?$', views.projects, name='projects'),

    url(r'^projects/(?P<project_name>[^/]+)/?$', views.project, name='project'),

    # Don't cache the dataset, so that we can display the user's
    # previous selection, and not what was cached.
    url(r'^projects/(?P<project_name>[^/]+)/(?P<dataset_name>[^/]+)/?$',
        never_cache(views.DatasetView.as_view()), name='dataset'),

    url(r'^platforms/?$', views.platforms, name='platforms'),

    # display list of projects for a platform, user selects project
    url(r'^platforms/(?P<platform_name>[^/]+)/?$', views.platform,
        name='platform'),

    url(r'^platforms/(?P<platform_name>[^/]+)/(?P<project_name>[^/]+)/?$',
        views.platform_project, name='platformProject'),

    url(r'^data/(?P<project_name>[^/]+)/(?P<dataset_name>[^/]+)/?$',
        never_cache(views.DataView.as_view()), name='ajax-data'),
]
