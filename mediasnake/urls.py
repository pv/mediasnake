from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^login/$', 'django.contrib.auth.views.login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', dict(next_page=settings.LOGIN_URL)),
    url(r'^account/$', 'django.contrib.auth.views.password_change'),
    url(r'^account/password-changed/$', 'django.contrib.auth.views.password_change_done'),

    url(r'^', include('mediasnakefiles.urls')),

    # Examples:
    # url(r'^$', 'mediasnake.views.home', name='home'),
    # url(r'^mediasnake/', include('mediasnake.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
