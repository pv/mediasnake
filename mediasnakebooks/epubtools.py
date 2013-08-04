import os
import re
import textwrap
import gzip
import bz2

import epub

from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

class HTMLToParagraphs(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.content = []
        self._para = []

    def _flush(self):
        if self._para:
            p = u"".join(self._para).strip()
            self.content.append(p)
            self._para = []

    def handle_starttag(self, tag, attrs):
        if tag in ('div', 'p'):
            self._flush()

    def handle_data(self, data):
        self._para.append(data)

    def handle_entityref(self, name):
        try:
            c = unichr(name2codepoint[name])
            self._para.append(c)
        except (KeyError, ValueError):
            pass

    def handle_charref(self, name):
        try:
            if name.startswith('x'):
                c = unichr(int(name[1:], 16))
            else:
                c = unichr(int(name))
            self._para.append(c)
        except ValueError:
            pass

    def close(self):
        HTMLParser.close(self)
        self._flush()

def html_to_paragraphs(html):
    p = HTMLToParagraphs()
    p.feed(html)
    p.close()
    return p.content


class BaseEpub(object):
    def _mangle_author(self, name):
        if ',' not in name:
            parts = name.split()
            j = len(parts) - 1
            while j > 0:
                if parts[j] and parts[j][0].isupper():
                    break
            forename = parts[:j]
            surname = parts[j:]
            if forename:
                name = u" ".join(surname) + u", " + u" ".join(forename)
            else:
                name = u" ".join(surname)
        return name

    def _mangle_title(self, title):
        prefixes = (u"The ", u"A ")
        for p in prefixes:
            if title.startswith(p):
                return title[len(p):] + u", " + p.strip()
        return title


class Epub(BaseEpub):
    def __init__(self, filename):
        self.pub = epub.open_epub(filename)

    def chapters(self):
        return [x[0] for x in self.pub.opf.spine.itemrefs]

    @property
    def author(self):
        try:
            return u"\n".join(self._mangle_author(x[0]) for x in self.pub.opf.metadata.creators
                              if x[1] == u'aut')
        except (IndexError, AttributeError):
            return u""

    @property
    def title(self):
        try:
            return u"\n".join(self._mangle_title(x[0])
                              for x in self.pub.opf.metadata.titles)
        except (IndexError, AttributeError):
            return u""

    def get(self, item):
        html = self.pub.read_item(self.pub.get_item(item))
        try:
            html = html.decode('utf-8')
        except UnicodeError:
            html = html.decode('latin1')
        return html_to_paragraphs(html)


class TxtFile(BaseEpub):

    FILE_RES = [
        re.compile(r"^(?P<auth>[^-\[\]]+) - (?P<titl>[^\[\]]+) \[(?P<lang>.*)\]$"),
        re.compile(r"^(?P<auth>[^-]+) - (?P<titl>.+)$"),
        re.compile(r"^(?P<titl>[^\[\]]+) \[(?P<lang>.+)\]$"),
        re.compile(r"^(?P<titl>.+)$")
    ]

    CHAPTER_SIZE = 200

    def __init__(self, filename):
        self.filename = filename
        self._chapters = []
        self._content = {}

        base, ext = os.path.splitext(os.path.basename(filename))
        if ext in ('.gz', '.bz2'):
            base, ext = os.path.splitext(base)

        self.author = u""
        self.title = self._mangle_title(base)

        for reg in TxtFile.FILE_RES:
            m = reg.match(base)
            if m:
                g = m.groupdict()
                if 'titl' in g:
                    self.title = self._mangle_title(g['titl'])
                if 'auth' in g:
                    self.author = self._mangle_author(g['auth'])
                break

    def chapters(self):
        self._load()
        return self._chapters

    def get(self, item):
        self._load()
        return self._content[item]

    def _load(self):
        if self._content:
            return

        filename = self.filename

        basefn, ext = os.path.splitext(filename)
        if ext == '.gz':
            f = gzip.open(filename, 'rb')
            filename = basefn
        elif ext == '.bz2':
            f = bz2.BZ2File(filename, 'rb')
            filename = basefn
        else:
            f = open(filename, 'rb')

        paragraphs = self._load_plain_text(f).splitlines()

        self._chapters = []
        self._content = {}

        for j in range(0, len(paragraphs), TxtFile.CHAPTER_SIZE):
            chunk = paragraphs[j:j+TxtFile.CHAPTER_SIZE]
            key = "%d" % (j,)
            self._content[key] = chunk
            self._chapters.append(key)

    def _load_plain_text(self, f):
        if isinstance(f, str):
            text = str
        else:
            text = f.read()

        for encoding in self._detect_encoding(text):
            try:
                text = unicode(text, encoding)
                break
            except UnicodeError:
                pass

        return self._rewrap(text)

    def _detect_encoding(self, text):
        encodings = ['utf-8']
        if '\x92' in text:
            encodings.append('windows-1250')
        else:
            encodings.append('latin1')
        return encodings

    def _rewrap(self, text):
        if not text:
            return

        # remove lines
        text = re.sub(r'-{10,}', '', text)
        text = re.sub(r'={10,}', '', text)

        text = text.replace(u'\r', u'')
        text = textwrap.dedent(text)

        sample = text[:80*1000]
        if len([x for x in sample.split('\n') if x.startswith(' ')]) > 20:
            # Paragraphs separated by indent
            text = re.sub(u'\n(?!\\s)', u' ', text)
        elif max(map(len, sample.split("\n"))) < 100 and sample.count('\n\n') > 5:
            # Paragraphs separated by empty lines
            text = re.sub(u'\n(?!\n)', u' ', text)
        else:
            # Paragraphs on a single line -- or couldn't determine formatting
            pass

        text = re.sub(u'\s{10,}', u'\n', text)
        text = re.sub(u'\n[ \t]+', u'\n', text)
        return text


def open_epub(filename):
    if filename.endswith('.epub'):
        return Epub(filename)
    elif (filename.endswith('.txt')
          or filename.endswith('.txt.gz')
          or filename.endswith('.txt.bz2')):
        return TxtFile(filename)
    else:
        raise IOError("Unsupported file format")
