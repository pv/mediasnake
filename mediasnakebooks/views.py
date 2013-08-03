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
        'pos': pos,
        'next': pos + 1 if pos + 1 < len(chapters) else None,
        'prev': pos - 1 if pos > 0 else None,
        'languages': ['eng', 'jpn', 'other'],
        }

    return render(request, "mediasnakebooks/ebook.html", context)


@login_required
@cache_control(private=True, max_age=30*60)
@cache_page(30*60)
def tokens(request, id, pos, language):
    ebook, epub, chapters, paragraphs, pos = _get_epub(id, pos)
    words, html = tokenize(paragraphs, language)

    known = []
    for w in words:
        try:
            word_obj = Word.objects.get(base_form=words)
            known.append(word_obj.known)
        except Word.DoesNotExist:
            known.append(5)

    html = re.sub(u' </span>', u'</span> ', html)
    html = re.sub(u'(<span[^>]*>) ', ur' \1', html)
    content = json.dumps(dict(html=html, words=words, known=known))
    return HttpResponse(content, content_type="application/json")
