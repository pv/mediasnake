from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='ebook-index'),
    url(r'^(?P<id>\d+)/(?P<pos>\d+)/$', views.ebook, name='ebook-pos'),
    url(r'^(?P<id>\d+)/(?P<pos>\d+)/ajax/tokens/(?P<language>[a-z0-9@-]+)/$', views.tokens, name='ebook-ajax-tokens'),
)
