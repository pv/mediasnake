============
Installation
============

Mediasnake is a Django application written in Python. There are many
ways to serve it. Here, we describe how to do it on Debian-based Linux
systems, using NGINX or Apache as the web server.


Unpacking
=========

First, select a location where you want to put the code. It does not
matter much where it is, but it **must NOT be inside the web root** of
your web server. Below, we assume you will install the application
under: ``/srv/mediasnake``.

Unpack the source package there. Now, under ``/srv/mediasnake`` you
should have::

    /srv/mediasnake
        bootstrap.py
	config.ini.example
	data/
	docs/
	manage.py
	mediasnake/
	mediasnakefiles/
	...


Prerequisites
=============

If you are using Apache::

    apt-get install python-virtualenv ffmpegthumbnailer libapache2-mod-wsgi

If you are using NGINX + uWSGI + Supervisord::

    apt-get install python-virtualenv ffmpegthumbnailer supervisor uwsgi-plugin-python

If you want something else, take a look at
https://docs.djangoproject.com/en/1.5/howto/deployment/


Configuration
=============

Go to ``/srv/mediasnake/`` and copy ``config.ini.example`` to
``config.ini``.

Change the following options::

    url_prefix = /mediasnake
    video_dirs = "/home/data/My Videos", "/home/data/More of My Videos"
    hostnames = "localhost", "127.0.0.1", "mysite.com"

Of course, choose the above two video directories as you like.  The
``url_prefix`` above is something that needs to match your web server
configuration, see below.  The ``hostnames`` need to match the names
of your virtual hosts.


File permissions
================

Set the file permissions so that the web and app servers can access
the data files::

    mkdir env
    chmod a+rX -R /srv/mediasnake/
    chgrp www-data -R data/ env/
    chmod ug=rwX,o= -R data/ env/

Moreover, you need to make sure the www-data user or group can
actually read the video files that you plan to serve.


Initialization
==============

Run::

    sudo -u www-data python bootstrap.py

This will download and install all dependencies into a directory
``env/``, and ask you to create a user account and a password.

The system uses a Sqlite database stored in the ``data/`` directory.


Web server configuration (Apache)
=================================

First enable the Apache WSGI module::

    a2enmod wsgi

Then write an Apache configuration file ``/etc/apache2/conf.d/mediasnake``::

    Alias /mediasnake/static /srv/mediasnake/data/static

    <Directory /srv/mediasnake/data/static>
        Order deny,allow
        Allow from all
        AllowOverride None
    </Directory>

    WSGIScriptAlias /mediasnake /srv/mediasnake/mediasnake/wsgi.py
    WSGIPythonHome /srv/mediasnake/env
    WSGIPythonPath /srv/mediasnake

    <Directory /srv/mediasnake/mediasnake>
        <Files wsgi.py>
    	    Order deny,allow
    	    Allow from all
        </Files>
    </Directory>

You can also find this example file under in the ``docs/examples/``
directory.

If you have multiple virtual hosts, you may want to drop the
configuration into only one of them instead.

Now, do::

    /etc/init.d/apache reload

This also needs to be done after every time you change ``config.ini``.

You should be able to browse to http://yoursite/mediasnake/ There, log
in, and go to the admin tab. Press "Rescan for Videos" and wait ---
this may take some time as it generates all video thumbnails at once.
After that, you should be all set!


Web server configuration (NGINX)
================================

This assumes you understand how NGINX configuration in general works.

A suitable NGINX + uWSGI configuration for Mediasnake looks like
this::

    location /mediasnake/static/ {
        try_files $uri $uri/ =404;
        alias /srv/mediasnake/data/static/;
    }

    location /mediasnake/streaming/ {
        internal;
        alias /srv/mediasnake/data/streaming/;
    }

    location /mediasnake/ {
        include /etc/nginx/uwsgi_params;
        uwsgi_param SCRIPT_NAME /mediasnake;
        uwsgi_modifier1 30;
        uwsgi_pass unix:/srv/mediasnake/data/uwsgi.sock;
    }

You can now set ``file_serving = nginx`` in ``config.ini`` to hand off
file streaming to NGINX. Finally, do::

    /etc/init.d/nginx reload

As you know, NGINX expects app servers to run as separate
processes. This is conveniently done by using e.g. ``supervisord``. We
only need to create a configuration file
``/etc/supervisor/conf.d/mediasnake.conf``::

    [program:mediasnake]
    command = uwsgi_python -H env --socket data/uwsgi.sock --mount=/mediasnake=mediasnake/wsgi.py -M -p 4
    directory = /srv/mediasnake
    user = www-data

This spawns 4 worker processes.

Now do::

    /etc/init.d/supervisor stop
    /etc/init.d/supervisor start
    supervisorctl

The ``supervisorctl`` should indicate the process is now running. The
site should now be ready to go.


Streaming on HTTP, serving on HTTPS
===================================

It turns out that SSL, self-signed certificates in particular, cause
major pain for would-be player applications. It then makes sense to
stream the video content over plain HTTP.

The security implications of this are not extremely bad:

- Authentication information is not sent over HTTP.
- The streaming URL is locked to a single IP address.
- It is only valid for a couple of hours.
- The URL address does not contain information about the file name.
- It is not possible to browse the collection via HTTP.

A man-in-the-middle party snooping on you (e.g., someone on your local
network, or your ISP or government) will mostly find out that you
watched some video. Unless they act fast or record ALL network traffic,
they don't get much wiser than that.

It is now assumed that you have followed the above instructions, and
configured the service to go through a SSL enabled virtual host.

We also assume that you have a second virtual host for serving HTTP.
If not, you need to add it.

The configuration for this case is as follows: first change in your
``config.ini``::

    http_streaming_address = http://mysite.com:80/

where the site and the port number correspond to your HTTP virtual
host.

You should now configure Mediasnake on the HTTP virtual host. The
configuration goes exactly the same as on the other virtual host.

When ``http_streaming_address`` is set in the configuration file,
Mediasnake will only serve streaming tickets if it notices the virtual
host doesn't have SSL. Moreover, the authentication cookies are set
SSL-only, so they are not transmitted unencrypted.

However, if you had an active logged-in session going, you should log
out, so that the cookie gets its correct SSL-only status!


Troubleshooting
===============

If you encounter 500 Internal Server errors, try setting ``debug=1``
in ``config.ini`` and looking into Apache logs and into
``data/mediasnake.log``.


Development
===========

If you want to hack on it, just run::

    . env/bin/activate
    ./manage.py runserver

Then go read Django documentation from http://djangoproject.com/ if
you haven't already and hack away.
