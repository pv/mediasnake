from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib import admin

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group

admin.autodiscover()
admin.site.unregister(Group)
admin.site.unregister(Site)

urlpatterns = patterns('',
    url(r'^login/$', 'django.contrib.auth.views.login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', dict(next_page=settings.LOGIN_URL)),
    url(r'^account/$', 'django.contrib.auth.views.password_change'),
    url(r'^account/password-changed/$', 'django.contrib.auth.views.password_change_done'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^books/', include('mediasnakebooks.urls')),
    url(r'^comics/', include('mediasnakecomics.urls')),
    url(r'^', include('mediasnakefiles.urls')),
)
