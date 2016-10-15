# from django.conf.urls import patterns, include, url
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView

admin.autodiscover()

urlpatterns = [

    # redirect empty URL to /ncharts
    url(r'^$', RedirectView.as_view(url='/ncharts',permanent=True)),

    # If URL starts with ncharts, remove "ncharts/", pass what's
    # left on to ncharts.urls
    url(r'^ncharts/', include('ncharts.urls', namespace='ncharts'), name="ncharts"),

    url(r'^admin/', include(admin.site.urls), name="admin:index")
]
