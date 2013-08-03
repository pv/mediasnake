# -*- coding: utf-8 -*-
from django.utils.html import escape

import _mecab

INTRA_PUNCT = u"'"

def _token_to_src(token):
    if token in u'。!?.':
        token = '.'
    return escape(token)


def _tokenize_other(paragraphs):
    html = []
    words = set()

    for para in paragraphs:
        para = para.replace(u"\u2019", u"'")

        p = para.split()
        bases = [u"".join(z for z in x if z.isalpha() or z in INTRA_PUNCT) for x in p]
        bases = [b.lower() if b == x else u"" for b, x in zip(bases, p)]

        words.update(x for x in bases if x)
        p = ["<span data-src=\"%s\">%s</span>" % (_token_to_src(b), escape(x))
             if b else escape(x)
             for b, x in zip(bases, p)]
        html.append(u"<p>" + u" ".join(p) + u"</p>")

    return list(words), u"\n".join(html)


def _tokenize_jpn(paragraphs):
    mecab = _mecab.Mecab()

    html = []
    words = set()

    for para in paragraphs:
        parts = mecab.collapse(mecab.parse(para))
        words.update(x.base for x in parts if x.base)
        p = [u"<span data-src=\"%s\">%s</span>" % (_token_to_src(x.base), escape(x.surface)) if x.base else escape(x.surface)
             for x in parts]
        html.append(u"<p>" + u" ".join(p) + u"</p>")

    return list(words), u"\n".join(html)


def tokenize(paragraphs, language):
    if language == "jpn":
        return _tokenize_jpn(paragraphs)
    else:
        return _tokenize_other(paragraphs)
