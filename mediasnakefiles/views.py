import os
import re

from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from mediasnake_sendfile import sendfile

from mediasnakefiles.models import VideoFile, StreamingTicket, scan


def _sort_key(video_file):
    dirname = video_file.relative_dirname
    basename = video_file.basename
    title = video_file.title
    numbers = tuple(int(x) for x in re.sub(r'[^0-9 \t]', '', title).split())
    return (dirname.split(os.path.sep), numbers, title, basename)


class _VideoGroup(object):
    def __init__(self, name, video_files):
        self.video_files = video_files
        self.name = name


@login_required
def index(request):
    video_files = VideoFile.objects.all()
    video_groups = []

    if video_files:
        group = None
        for video_file in sorted(video_files, key=_sort_key):
            if group is None or video_file.relative_dirname != group.name:
                group = _VideoGroup(video_file.relative_dirname, [])
                video_groups.append(group)
            group.video_files.append(video_file)

    context = {'video_groups': video_groups}
    return render(request, "mediasnakefiles/index.html", context)


@login_required
def thumbnail(request, id):
    try:
        video_file = VideoFile.objects.get(pk=id)
    except VideoFile.DoesNotExist:
        raise Http404

    fn = video_file.thumbnail_filename

    if not os.path.isfile(fn):
        raise Http404

    return sendfile(request, fn, mimetype="image/jpeg")


@login_required
def stream(request, id):
    try:
        video_file = VideoFile.objects.get(pk=id)
    except VideoFile.DoesNotExist:
        raise Http404

    ticket = StreamingTicket.new_for_video(video_file,
                                           request.META['REMOTE_ADDR'])
    ticket.save()

    # Do some housekeeping at the same time
    StreamingTicket.cleanup()

    context = {'video_file': video_file,
               'ticket': ticket}

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

    scan()

    return redirect(index)
