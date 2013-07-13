from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^thumbnail/(?P<id>\d+)/$', views.thumbnail, name='thumbnail'),
    url(r'^stream/(?P<id>\d+)/$', views.stream, name='stream'),
    url(r'^ticket/(?P<secret>[a-z0-9.]+)/.*$', views.ticket_stream, name='ticket'),
    url(r'^rescan/$', views.rescan, name='rescan')
)
