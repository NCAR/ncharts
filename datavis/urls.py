from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'datavis.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^ncharts/', include('ncharts.urls', namespace='ncharts')),
    url(r'^admin/', include(admin.site.urls), name="admin:index"),
    url(r'^$', 'datavis.views.index')
)
