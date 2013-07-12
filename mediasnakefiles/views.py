import os

from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from mediasnake_sendfile import sendfile

from mediasnakefiles.models import VideoFile, StreamingTicket


@login_required
def list(request):
    video_files = VideoFile.objects.all()
    context = {'video_files': video_files}
    return render(request, "mediasnakefiles/list.html", context)


@login_required
def thumbnail(request, id):
    try:
        video_file = VideoFile.objects.get(pk=id)
    except VideoFile.DoesNotExist:
        raise Http404

    fn = video_file.thumbnail_filename

    if os.path.isfile(fn):
        with open(fn, 'rb') as f:
            return HttpResponse(f.read(), content_type="image/jpeg")

    raise Http404


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

    return redirect(ticket_stream, secret=ticket.secret)


def ticket_stream(request, secret):
    try:
        ticket = StreamingTicket.objects.get(secret=secret)
    except StreamingTicket.DoesNotExist:
        raise Http404

    if not ticket.is_valid(request.META['REMOTE_ADDR']):
        return HttpResponseForbidden()

    video_file = ticket.video_file
    filename = ticket.create_symlink()
    return sendfile(request, filename, mimetype=video_file.mimetype,
                    accept_ranges=True)
