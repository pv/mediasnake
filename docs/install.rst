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
    secret_key = "type some random characters here: fjkjakjdklda"
    video_dirs = "/home/data/My Videos", "/home/data/More of My Videos"
    hostnames = "localhost", "127.0.0.1", "mysite.com"

Of course, choose the above two video directories accordingly.  The
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
``env/``, and ask you to create a superuser account and a password.

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
    command = uwsgi_python -H env --socket data/uwsgi.sock --mount=/mediasnake=mediasnake/wsgi.py
    directory = /srv/mediasnake
    user = www-data

Now do::

    /etc/init.d/supervisor stop
    /etc/init.d/supervisor start
    supervisorctl

The ``supervisorctl`` should indicate the process is now running. The
site should now be ready to go.


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
