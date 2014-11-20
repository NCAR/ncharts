from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'eoldatasite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^ncharts/', include('ncharts.urls', namespace='ncharts')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'eoldatasite.views.index')
)
