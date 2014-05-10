from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='comic-index'),
    url(r'^recent/$', views.recent, name='comic-recent'),
    url(r'^(?P<id>\d+)/$', views.comic_start, name='comic-start'),
    url(r'^(?P<id>\d+)/(?P<page>\d+)/$', views.comic_page, name='comic-page'),
    url(r'^(?P<id>\d+)/(?P<page>\d+)/image/$', views.image, name='comic-image'),
)
