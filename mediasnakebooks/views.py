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

from mediasnakebooks.models import Ebook, Word, Language
from mediasnakebooks.epubtools import Epub
from mediasnakebooks.tokenize import tokenize
from mediasnakebooks._stardict import Stardict

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

    languages = [dict(code=lang.code, dict_url=lang.dict_url)
                 for lang in Language.objects.all()]

    context = {
        'ebook': ebook,
        'paragraphs': paragraphs,
        'chapters': chapters,
        'pos': pos,
        'next': pos + 1 if pos + 1 < len(chapters) else None,
        'prev': pos - 1 if pos > 0 else None,
        'languages': languages,
        }

    return render(request, "mediasnakebooks/ebook.html", context)


@login_required
@cache_control(private=True, max_age=30*60)
@cache_page(30*60)
def tokens(request, id, pos, language):
    ebook, epub, chapters, paragraphs, pos = _get_epub(id, pos)
    words, html = tokenize(paragraphs, language)

    html = re.sub(u' </span>', u'</span> ', html)
    html = re.sub(u'(<span[^>]*>) ', ur' \1', html)
    content = json.dumps(dict(html=html, words=words))
    return HttpResponse(content, content_type="application/json")


@login_required
def word_dict(request, language, word):
    try:
        lang = Language.objects.get(code=language)
    except Language.DoesNotExist:
        raise Http404

    text = u"<No dictionary -- see admin page>"
    error = True

    if lang.stardict is not None:
        try:
            sd = Stardict(lang.stardict)
            text = u"\n\n".join(sd.lookup(word))
            if text:
                error = False
            else:
                text = u"<No results for '%s'>" % (word,)
        except IOError:
            text = u"<Stardict dictionary file not found!>"

    content = json.dumps(dict(text=text, error=error))
    return HttpResponse(content, content_type="application/json")


@login_required
def words(request, language):
    if request.method != 'POST':
        raise Http404

    try:
        lang = Language.objects.get(code=language)
    except Language.DoesNotExist:
        raise Http404

    words = request.POST.getlist('words[]')
    known = [5]*len(words)

    chunksize = 50
    for j in range(0, len(words), chunksize):
        word_objs = Word.objects.filter(base_form__in=words[j:j+chunksize], language=lang)
        for w in word_objs:
            j = words.index(w.base_form)
            known[j] = w.known

    content = json.dumps(dict(words=words, known=known))
    return HttpResponse(content, content_type="application/json")


@login_required
def word_adjust(request, language, word):
    if request.method != 'POST':
        raise Http404

    try:
        lang = Language.objects.get(code=language)
    except Language.DoesNotExist:
        raise Http404

    try:
        level = int(request.POST['level'])
        if level < 0 or level > 5:
            raise ValueError
    except ValueError:
        return HttpResponse("400 Bad request", status=400)

    word, created = Word.objects.get_or_create(base_form=word, language=lang)
    word.known = level
    word.save()

    content = json.dumps(dict(word=word.base_form, level=level))
    return HttpResponse(content, content_type="application/json")
