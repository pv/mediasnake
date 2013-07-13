==========
Mediasnake
==========

Mediasnake is a simple web application for streaming videos from disk
via HTTP(S).

It does not do anything complicated --- no transcoding etc. --- just a
list of videos with thumbnails, and the possibility to stream them.

Installation
------------

For install instructions, read ``docs/install``.


Usage on Android
----------------

A simple way to stream videos to an Android tablet is:

- Install VLC Android media player.

- Browse to your Mediasnake server, and click "Stream" on a video of
  your liking.

- Unless your videos are in MP4 format, they don't play in the Android
  web browser directly.

  If so, do a long press on the "Direct link" button in Mediasnake's
  streaming view, and choose to open the file with VLC. Presto!


.. toctree::
   :maxdepth: 1

   install
