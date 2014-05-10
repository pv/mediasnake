from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='comic-index'),
    url(r'^recent/$', views.recent, name='comic-recent'),
    url(r'^(?P<id>\d+)/$', views.comic, name='comic-start'),
    url(r'^(?P<id>\d+)/(?P<page>\d+)/$', views.image, name='comic-image'),
    url(r'^(?P<id>\d+)/bookmark/$', views.bookmark, name='comic-bookmark'),
)
