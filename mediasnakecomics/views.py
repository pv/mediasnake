import os
import re
import time
import json
import base64

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseForbidden, StreamingHttpResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import cache_control
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.encoding import smart_text
from django.core.urlresolvers import reverse

from mediasnakecomics.models import Comic, Bookmark

from mediasnakecomics.ziptools import ImagePack


@login_required
def index(request):
    query = Comic.objects

    search_str = request.GET.get('search')
    if search_str:
        query = query.filter(Q(path__icontains=search_str) | Q(title__icontains=search_str))
    else:
        search_str = u''

    comics = query.order_by('path', 'title').values('id', 'path', 'title')
    paginator = Paginator(comics, 50)

    page = request.GET.get('page')
    try:
        comics = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        comics = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        comics = paginator.page(paginator.num_pages)

    recent = Bookmark.objects.all()[:5]

    context = {'comics': comics,
               'pages': range(1, paginator.num_pages+1),
               'search_str': search_str,
               'recent': recent,
               }
    return render(request, "mediasnakecomics/index.html", context)


@login_required
def recent(request):
    query = Bookmark.objects

    search_str = request.GET.get('search')
    if search_str:
        query = query.filter(Q(comic__path__icontains=search_str) | Q(comic__title__icontains=search_str))
    else:
        search_str = u''

    recent = query.all()
    paginator = Paginator(recent, 50)

    page = request.GET.get('page')
    try:
        recent = paginator.page(page)
    except PageNotAnInteger:
        recent = paginator.page(1)
    except EmptyPage:
        recent = paginator.page(paginator.num_pages)

    context = {'recent': recent,
               'pages': range(1, paginator.num_pages+1),
               'search_str': search_str,
               }
    return render(request, "mediasnakecomics/recent.html", context)


def _get_comic(id):
    try:
        comic = Comic.objects.get(pk=id)
    except Comic.DoesNotExist:
        raise Http404
    try:
        pages = ImagePack(comic.filename)
    except IOError:
        raise Http404
    return comic, pages


@login_required
def comic(request, id):
    comic, pages = _get_comic(id)

    try:
        bookmark = Bookmark.objects.get(comic=comic)
    except Bookmark.DoesNotExist:
        bookmark = Bookmark(comic=comic)
        bookmark.page = 0
        bookmark.save()

    active_page = bookmark.page

    context = {
        'comic': comic,
        'active_page': active_page,
        'num_pages': len(pages),
    }

    return render(request, "mediasnakecomics/comic.html", context)


@login_required
@cache_page(30*24*60*60)
def image(request, id, page):
    page = int(page)
    comic, pages = _get_comic(id)

    mimetypes = {
        '.gif': 'image/gif',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
    }

    image_data = pages.read_file(pages[page])
    image_mime = mimetypes[os.path.splitext(pages[page])[1]]

    return HttpResponse(image_data, mimetype=image_mime)


@login_required
def bookmark(request, id):
    if request.method != 'POST':
        raise Http404

    try:
        page = int(request.POST['page'])
    except (ValueError, KeyError):
        return HttpResponse("400 Bad request", status=400)

    comic, pages = _get_comic(id)

    if page < 0 or page >= len(pages):
        return HttpResponse("400 Bad request", status=400)

    try:
        bookmark = Bookmark.objects.get(comic=comic)
    except Bookmark.DoesNotExist:
        bookmark = Bookmark(comic=comic)

    bookmark.page = page
    bookmark.save()

    content = json.dumps(True)
    return HttpResponse(content, content_type="application/json")
