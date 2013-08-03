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


class Epub(object):
    def __init__(self, filename):
        self.pub = epub.open_epub(filename)

    def chapters(self):
        return [x[0] for x in self.pub.opf.spine.itemrefs]

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

    @property
    def author(self):
        return u"\n".join(self._mangle_author(x[0]) for x in self.pub.opf.metadata.creators
                          if x[1] == u'aut')

    def _mangle_title(self, title):
        prefixes = (u"The ", u"A ")
        for p in prefixes:
            if title.startswith(p):
                return title[len(p):] + u", " + p.strip()
        return title

    @property
    def title(self):
        return u"\n".join(self._mangle_title(x[0])
                          for x in self.pub.opf.metadata.titles)

    def get(self, item):
        html = self.pub.read_item(self.pub.get_item(item))
        try:
            html = html.decode('utf-8')
        except UnicodeError:
            html = html.decode('latin1')
        return html_to_paragraphs(html)
