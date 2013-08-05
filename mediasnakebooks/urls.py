from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='ebook-index'),
    url(r'^(?P<id>\d+)/$', views.ebook_start, name='ebook-start'),
    url(r'^(?P<id>\d+)/(?P<chapter>[A-Z0-9@]+)/$', views.ebook, name='ebook-chapter'),
    url(r'^ajax/tokens/(?P<id>\d+)/(?P<chapter>\d+)/(?P<language>[A-Za-z0-9@-]+)/$', views.tokens, name='ebook-ajax-tokens'),
    url(r'^ajax/dict/(?P<language>[A-Za-z0-9@-]+)/(?P<word>.*)/$', views.word_dict, name='ebook-ajax-dict'),
    url(r'^ajax/word/(?P<language>[A-Za-z0-9@-]+)/(?P<word>.*)/$', views.word_adjust, name='ebook-ajax-word'),
    url(r'^ajax/words/(?P<language>[A-Za-z0-9@-]+)/$', views.words, name='ebook-ajax-words'),
    url(r'^ajax/bookmark/(?P<id>\d+)/(?P<chapter>[A-Z0-9@]+)/$', views.bookmark, name='ebook-ajax-bookmark'),
    url(r'^words/(?P<language>[A-Za-z0-9@-]+)/$', views.words_export, name='ebook-ajax-words-export'),
    url(r'^recent/$', views.recent, name='ebook-recent'),
)
