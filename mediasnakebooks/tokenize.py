# -*- coding: utf-8 -*-
import re
import unicodedata
from HTMLParser import HTMLParser

from django.utils.html import escape

from mediasnakebooks._stardict import Stardict
from mediasnakebooks import _mecab


def is_period(token):
    return token in u"。."


def is_punctuation(token):
    return all(unicodedata.category(c).startswith('P') for c in token)


def _token_to_src(token):
    if is_punctuation(token):
        token = u""
    return escape(token)


def _pad(x):
    if is_punctuation(x):
        return x
    else:
        return u" " + x


def _tokenize_eng(paragraphs, stardict):
    html = []
    words = set()

    for j, para in enumerate(paragraphs):
        para = para.replace(u"\u2019", u"'")

        p = para.split()
        bases = [u"".join(z for z in x if z.isalpha() or z == "'") for x in p]
        bases = [b.lower() for b, x in zip(bases, p)]

        words.update(x for x in bases if x)
        p = ["<span data-src=\"%s\">%s</span>" % (_token_to_src(b), escape(_pad(x)))
             if _token_to_src(b) else escape(_pad(x))
             for b, x in zip(bases, p)]
        html.append((u"<p data-line=\"%d\">" % j) + u"".join(p).strip() + u"</p>")

    return list(words), u"\n".join(html)


def _tokenize_jpn(paragraphs, stardict):
    mecab = _mecab.Mecab()

    html = []
    words = set()

    def tohtml(x):
        if x.base and x.base.isalpha():
            base = x.base
            if x.base_reading and x.base_reading != x.base:
                base += u"[" + x.base_reading + u"]"
            return u"<span data-src=\"%s\">%s</span>" % (escape(_token_to_src(base)), escape(x.surface))
        else:
            return escape(x.surface)

    for j, para in enumerate(paragraphs):
        para = re.sub(u"《.*?》", u"", para)
        para = re.sub(u"｜", u"", para)
        parts = mecab.dict_collapse(mecab.parse(para), stardict, reading_check=False)
        words.update(x.base + u"[" + x.base_reading + u"]" 
                     if x.base_reading and x.base_reading != x.base else x.base
                     for x in parts if x.base and x.base.isalpha())
        p = [tohtml(x) for x in parts]
        html.append((u"<p data-line=\"%d\">" % j) + u"".join(p) + u"</p>")

    return list(words), u"\n".join(html)


def _tokenize_cmn(paragraphs, stardict):
    html = []
    words = set()

    for j, para in enumerate(paragraphs):
        parts = stardict_split(para, stardict)
        bases = [p if stardict.lookup(p) else None for p in parts]

        words.update(x for x in bases if x)
        p = ["<span data-src=\"%s\">%s</span>" % (escape(b), escape(x))
             if b else escape(x)
             for b, x in zip(bases, parts)]
        html.append((u"<p data-line=\"%d\">" % j) + u"".join(p).strip() + u"</p>")

    return list(words), u"\n".join(html)


def tokenize(paragraphs, language):
    if language.stardict is not None:
        stardict = Stardict(language.stardict)
    else:
        stardict = None

    if language.code == "jpn":
        return _tokenize_jpn(paragraphs, stardict)
    elif language.code == "cmn":
        return _tokenize_cmn(paragraphs, stardict)
    else:
        return _tokenize_eng(paragraphs, stardict)


class ContextParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.parts = []
        self.cur_word = None
    def handle_starttag(self, tag, attrs):
        self.cur_word = None
        attrs = dict(attrs)
        if tag == 'span' and 'data-src' in attrs:
            self.cur_word = attrs['data-src']
    def handle_endtag(self, tag):
        self.cur_word = None
    def handle_data(self, data):
        self.parts.append((data, self.cur_word))


def tokenize_context_all(word, paragraph):
    p = ContextParser()
    p.feed(paragraph)

    word_start = None
    word_end = None

    filtered = []
    for text, text_word in p.parts:
        if text_word == word:
            if word_start is None:
                word_start = len(u"".join(filtered))
                word_end = word_start + 7 + len(text)
            filtered.append(u"<b>" + text + u"</b>")
        else:
            filtered.append(text)

    if word_start is None:
        return None

    filtered = u"".join(filtered)

    if len(filtered) > 30:
        # break at next comma etc.
        for j in range(word_end + 5, len(filtered) - 3, 1):
            if unicodedata.category(filtered[j]) == 'Po':
                if is_period(filtered[j]):
                    filtered = filtered[:j+1]
                else:
                    filtered = filtered[:j+1] + u"..."
                break

        # break at previous comma etc.
        for j in range(word_start - 5, 3, -1):
            if unicodedata.category(filtered[j]) == 'Po':
                if is_period(filtered[j]):
                    filtered = filtered[j+1:]
                else:
                    filtered = u"..." + filtered[j:]
                break

    return filtered


def tokenize_context(word, paragraph, language):
    return tokenize_context_all(word, paragraph)



def stardict_split(text, stardict):
    new_parts = []

    while text:
        prefix = stardict.longest_prefix(text)
        if prefix is None:
            new_parts.append(text[0])
            text = text[1:]
        else:
            new_parts.append(prefix)
            text = text[len(prefix):]

    return new_parts
