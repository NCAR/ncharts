from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import RedirectView

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'datavis.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', RedirectView.as_view(url='/ncharts')),

    url(r'^ncharts/', include('ncharts.urls', namespace='ncharts'), name="ncharts"),
    url(r'^admin/', include(admin.site.urls), name="admin:index")
)
