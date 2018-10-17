# from django.conf.urls import patterns, include, url
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = [


    # If URL starts with ncharts, remove "ncharts/", pass what's
    # left on to ncharts.urls
    url(r'^ncharts/', include('ncharts.urls', namespace='ncharts'), name="ncharts"),

    # redirect empty URL to /ncharts
    url(r'^$', RedirectView.as_view(url='/ncharts',permanent=True)),

    # datavis/templates/robots.txt
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt',
        content_type='text/plain')),

    url(r'^admin/', include(admin.site.urls), name="admin:index")

]
