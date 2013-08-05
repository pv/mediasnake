import os
import re
import time
import json

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

from mediasnakebooks.models import Ebook, Word, Language, Bookmark
from mediasnakebooks.epubtools import open_epub
from mediasnakebooks.tokenize import tokenize
from mediasnakebooks._stardict import Stardict


@login_required
def index(request):
    query = Ebook.objects

    search_str = request.GET.get('search')
    if search_str:
        query = query.filter(Q(author__icontains=search_str) | Q(title__icontains=search_str))
    else:
        search_str = u''

    books = query.order_by('author', 'title').values('id', 'author', 'title')
    paginator = Paginator(books, 50)

    page = request.GET.get('page')
    try:
        books = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        books = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        books = paginator.page(paginator.num_pages)

    recent = Bookmark.objects.all()[:5]

    context = {'books': books,
               'pages': range(1, paginator.num_pages+1),
               'search_str': search_str,
               'recent': recent,
               }
    return render(request, "mediasnakebooks/index.html", context)


@login_required
def recent(request):
    query = Bookmark.objects

    search_str = request.GET.get('search')
    if search_str:
        query = query.filter(Q(ebook__author__icontains=search_str) | Q(ebook__title__icontains=search_str))
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
    return render(request, "mediasnakebooks/recent.html", context)


def _get_epub(id, chapter):
    try:
        ebook = Ebook.objects.get(pk=id)
    except Ebook.DoesNotExist:
        raise Http404

    epub = open_epub(ebook.filename)
    chapters = epub.chapters()

    try:
        chapter = int(chapter)
        chapter_name = chapters[chapter]
    except (IndexError, ValueError):
        raise Http404

    paragraphs = epub.get(chapter_name)

    return ebook, epub, chapters, paragraphs, chapter


@login_required
@cache_page(30*24*60*60)
def ebook(request, id, chapter):
    ebook, epub, chapters, paragraphs, chapter = _get_epub(id, chapter)

    languages = [dict(code=lang.code, dict_url=lang.dict_url)
                 for lang in Language.objects.order_by('code').all()]

    context = {
        'ebook': ebook,
        'paragraphs': paragraphs,
        'chapters': chapters,
        'chapter': chapter,
        'next': chapter + 1 if chapter + 1 < len(chapters) else None,
        'prev': chapter - 1 if chapter > 0 else None,
        'languages': languages,
        }

    try:
        bookmark = Bookmark.objects.get(ebook=ebook)
    except Bookmark.DoesNotExist:
        if chapter != 0:
            bookmark = Bookmark(ebook=ebook)
            bookmark.chapter = 0
            bookmark.paragraph = 0
            bookmark.save()

    return render(request, "mediasnakebooks/ebook.html", context)


@login_required
def ebook_start(request, id):
    try:
        ebook = Ebook.objects.get(pk=id)
    except Ebook.DoesNotExist:
        raise Http404

    try:
        bookmark = Bookmark.objects.get(ebook=ebook)
        chapter = bookmark.chapter
    except Bookmark.DoesNotExist:
        chapter = 0

    return redirect('ebook-chapter', id, chapter)


@login_required
def bookmark(request, id, chapter):
    try:
        ebook = Ebook.objects.get(pk=id)
    except Ebook.DoesNotExist:
        raise Http404

    if request.method == 'POST':
        try:
            paragraph = int(request.POST['paragraph'])
        except (ValueError, KeyError):
            return HttpResponse("400 Bad request", status=400)

        try:
            bookmark = Bookmark.objects.get(ebook=ebook)
        except Bookmark.DoesNotExist:
            bookmark = Bookmark(ebook=ebook)

        bookmark.chapter = chapter
        bookmark.paragraph = paragraph
        bookmark.save()
    else:
        try:
            bookmark = Bookmark.objects.get(ebook=ebook, chapter=chapter)
        except Bookmark.DoesNotExist:
            raise Http404

    content = json.dumps(dict(paragraph=bookmark.paragraph, error=False))
    return HttpResponse(content, content_type="application/json")


@login_required
@cache_page(30*24*60*60)
def tokens(request, id, chapter, language):
    ebook, epub, chapters, paragraphs, chapter = _get_epub(id, chapter)
    words, html = tokenize(paragraphs, language)

    html = re.sub(u' </span>', u'</span> ', html)
    html = re.sub(u'(<span[^>]*>) ', ur' \1', html)
    content = json.dumps(dict(html=html, words=words))
    return HttpResponse(content, content_type="application/json")


@login_required
@cache_page(30*24*60*60)
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

    content = json.dumps(dict(word=word, text=text, error=error))
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
    notes = [u""]*len(words)

    chunksize = 50
    for j in range(0, len(words), chunksize):
        word_objs = Word.objects.filter(base_form__in=words[j:j+chunksize], language=lang)
        for w in word_objs:
            j = words.index(smart_text(w.base_form))
            known[j] = w.known
            notes[j] = w.notes

    content = json.dumps(dict(words=words, known=known, notes=notes))
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
        known = int(request.POST['known'])
        if known < 0 or known > 5:
            raise ValueError
        notes = unicode(request.POST['notes'])
    except (ValueError, KeyError):
        return HttpResponse("400 Bad request", status=400)

    word, created = Word.objects.get_or_create(base_form=word, language=lang)
    word.known = known
    word.notes = notes
    word.save()

    content = json.dumps(dict(error=False))
    return HttpResponse(content, content_type="application/json")


@login_required
def words_export(request, language):
    try:
        lang = Language.objects.get(code=language)
    except Language.DoesNotExist:
        raise Http404

    words = Word.objects.filter(language=lang).all()

    rows = []
    for w in words:
        if w.known in (0, 5):
            continue

        m = re.match(ur'^(.*?)\s*\[(.*)\]\s*$', smart_text(w.base_form))
        if m:
            base_form = m.group(1)
            alt_form = m.group(2)
        else:
            base_form = smart_text(w.base_form)
            alt_form = u""

        notes = w.notes
        if notes:
            notes = notes.replace(u"\n", u" ").replace(u"\t", u" ").strip()
        else:
            notes = u""

        rows.append(u"\t".join(
            [base_form, alt_form, unicode(w.known), notes]))

    response = HttpResponse(u"\n".join(rows), content_type="text/csv")
    response['Content-Disposition'] = "attachment; filename=\"words-%s.csv\"" % (lang.code)
    return response
