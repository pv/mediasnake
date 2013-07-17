import os
import re
import time

from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseForbidden, StreamingHttpResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import cache_control
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from mediasnake_sendfile import sendfile

from mediasnakefiles.models import VideoFile, StreamingTicket, get_scan_status, spawn_rescan, \
     get_thumbnail_filename


def _sort_key(video_file):
    dirname = video_file.relative_dirname
    basename = video_file.basename
    title = video_file.title
    numbers = tuple(int(x) for x in re.sub(r'[^0-9 \t]', '', title).split())
    return (dirname.split(os.path.sep), numbers, title, basename)


class Folder(object):
    def __init__(self, name, groups):
        self.groups = groups
        self.name = name


class VideoGroup(object):
    def __init__(self, base_file, video_files):
        self.video_files = video_files
        self.base_file = base_file


@login_required
@cache_page(30*24*60*60)
def index(request):
    # Note: the cache will be invalidated by rescanning, so we can use
    # a long caching time

    video_files = VideoFile.objects.all()
    folders = []

    if video_files:
        folder = None
        group = None
        last_base = None
        for video_file in sorted(video_files, key=_sort_key):
            if folder is None or video_file.relative_dirname != folder.name:
                folder = Folder(video_file.relative_dirname, [])
                last_base = None
                folders.append(folder)

            base, ext = os.path.splitext(
                os.path.join(video_file.relative_dirname, video_file.basename))

            if group is None or base != last_base:
                group = VideoGroup(video_file, [])
                last_base = base
                folder.groups.append(group)

            group.video_files.append(video_file)

    context = {'folders': folders}
    return render(request, "mediasnakefiles/index.html", context)


@login_required
@cache_page(30*24*60*60)
@cache_control(private=True, max_age=30*24*60*60)
def thumbnail(request, thumbnail):
    # The thumbnail id is a hash formed from file contents, so it is
    # essentially 1-to-1 with the thumbnail, which allows us to use
    # long caching times.

    fn = get_thumbnail_filename(thumbnail)

    if not os.path.isfile(fn):
        raise Http404

    return sendfile(request, fn, mimetype="image/jpeg")


class StreamEntry(object):
    def __init__(self, video_file, ticket):
        self.video_file = video_file
        self.ticket = ticket


@login_required
def stream(request, id):
    try:
        video_file = VideoFile.objects.get(pk=id)
    except VideoFile.DoesNotExist:
        raise Http404

    base, ext = os.path.splitext(video_file.filename)

    videos = video_file.get_all_versions()
    entries = [StreamEntry(x, StreamingTicket.new_for_video(x, request.META['REMOTE_ADDR']))
               for x in videos]
    for entry in entries:
        entry.ticket.save()

    # Do some housekeeping at the same time
    StreamingTicket.cleanup()

    context = {'title': videos[0].title,
               'entries': entries}

    return render(request, "mediasnakefiles/stream.html", context)


def ticket_stream(request, secret):
    secret = re.sub(r'\..*', '', secret)
    try:
        ticket = StreamingTicket.objects.get(secret=secret)
    except StreamingTicket.DoesNotExist:
        raise Http404

    if not ticket.is_valid(request.META['REMOTE_ADDR']):
        return HttpResponseForbidden()

    video_file = ticket.video_file
    filename = ticket.create_symlink()
    response = sendfile(request, filename, mimetype=video_file.mimetype,
                        accept_ranges=True)
    response['Content-Disposition'] = 'inline; filename=\"%s\"' % ticket.dummy_name
    return response


@login_required
def rescan(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method != 'POST':
        return redirect(index)

    spawn_rescan()

    time.sleep(0.5)

    context = {}
    return render(request, "mediasnakefiles/rescan.html", context)


@login_required
def rescan_status(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    status = get_scan_status()
    if status is None:
        return HttpResponse('{"complete": true}', content_type="application/json")
    return HttpResponse(status, content_type="application/json")
