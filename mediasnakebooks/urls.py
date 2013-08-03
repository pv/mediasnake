from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='ebook-index'),
    url(r'^(?P<id>\d+)/(?P<pos>\d+)/$', views.ebook, name='ebook-pos'),
    url(r'^ajax/tokens/(?P<id>\d+)/(?P<pos>\d+)/(?P<language>[A-Za-z0-9@-]+)/$', views.tokens, name='ebook-ajax-tokens'),
    url(r'^ajax/dict/(?P<language>[A-Za-z0-9@-]+)/(?P<word>.*)/$', views.word_dict, name='ebook-ajax-dict'),
    url(r'^ajax/word/(?P<language>[A-Za-z0-9@-]+)/(?P<word>.*)/$', views.word_adjust, name='ebook-ajax-word'),
    url(r'^ajax/words/(?P<language>[A-Za-z0-9@-]+)/$', views.words, name='ebook-ajax-words'),
)
