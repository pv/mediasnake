import os
import re
import time
import json

from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseForbidden, StreamingHttpResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import cache_control
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from mediasnakebooks.models import Ebook, Word
from mediasnakebooks.epubtools import Epub
from mediasnakebooks.tokenize import tokenize


@login_required
def index(request):
    books = Ebook.objects.order_by('author', 'title').all()
    context = {'books': books}
    return render(request, "mediasnakebooks/index.html", context)


def _get_epub(id, pos):
    try:
        ebook = Ebook.objects.get(pk=id)
    except Ebook.DoesNotExist:
        raise Http404

    epub = Epub(ebook.filename)
    chapters = epub.chapters()

    try:
        pos = int(pos)
        chapter = chapters[pos]
    except (IndexError, ValueError):
        raise Http404

    paragraphs = epub.get(chapter)

    return ebook, epub, chapters, paragraphs, pos


@login_required
def ebook(request, id, pos):
    ebook, epub, chapters, paragraphs, pos = _get_epub(id, pos)

    context = {
        'ebook': ebook,
        'paragraphs': paragraphs,
        'chapters': chapters,
        'next': pos + 1 if pos + 1 < len(chapters) else None,
        'prev': pos - 1 if pos > 0 else None,
        }

    return render(request, "mediasnakebooks/ebook.html", context)


@login_required
def tokens(request, id, pos, language):
    ebook, epub, chapters, paragraphs, pos = _get_epub(id, pos)
    words, html = tokenize(paragraphs, language)

    content = json.dumps(dict(html=html, words=words))
    return HttpResponse(content, content_type="application/json")
