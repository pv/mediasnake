from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.list, name='index'),
    url(r'^thumbnail/(?P<id>\d+)/$', views.thumbnail, name='thumbnail'),
    url(r'^stream/(?P<id>\d+)/$', views.stream, name='stream'),
    url(r'^ticket/(?P<secret>[a-f0-9]+)/$', views.ticket_stream, name='ticket')
)
