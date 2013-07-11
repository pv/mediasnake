import os

from django.conf import settings
from django.http import HttpResponse, Http404, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

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

    ticket = StreamingTicket.new_for_video(video_file)
    ticket.save()

    return redirect(stream_ticket, secret=ticket.secret)


def stream_ticket(request, secret):
    try:
        ticket = StreamingTicket.objects.get(secret=secret)
    except StreamingTicket.DoesNotExist:
        raise Http404

    ticket.create_symlink()

    url = settings.MEDIASNAKEFILES_STREAM_URL + ticket.secret
    response = redirect(url)
    response['X-Accel-Redirect'] = url
    return response


def _file_reader_generator(fn, start=None, stop=None):
    BLOCK_SIZE = 131072
    with open(fn, 'rb') as f:

        if start is not None:
            f.seek(start)

        pos = f.tell()
        while True:
            if stop is not None:
                block_size = min(BLOCK_SIZE, stop - pos)
                if block_size <= 0:
                    return
            else:
                block_size = BLOCK_SIZE

            block = f.read(block_size)
            pos += len(block)
            if not block:
                break
            yield block
