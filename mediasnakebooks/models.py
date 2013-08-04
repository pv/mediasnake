import os

from django.db import models

from mediasnakefiles.scanner import register_scanner, scan_message
from mediasnakebooks.epubtools import open_epub

UNKNOWN = 5
WELL_KNOWN = 1
IGNORED = 0


class Language(models.Model):
    code = models.CharField(max_length=3, help_text="3-letter ISO language code", null=False, primary_key=True)

    stardict = models.TextField(null=True, blank=True,
                                help_text="Full file name of a Stardict format dictionary (on the server)")
    dict_url = models.TextField(null=True, blank=True,
                                help_text="Dictionary URL: @WORD@ is replaced by the word to search for")

    def __unicode__(self):
        return u"%s" % (self.code,)


class Word(models.Model):
    language = models.ForeignKey(Language)

    base_form = models.TextField(null=False, help_text="Base form of the word")
    alt_form = models.TextField(null=True, help_text="Alternative word form (e.g. )")
    notes = models.TextField(null=True)
    known = models.IntegerField(default=5, help_text="Knowledge level: 5 - unknown, ..., 1 - well known, 0 - ignored")


class Ebook(models.Model):
    filename = models.TextField()
    title = models.TextField()
    author = models.TextField()


@register_scanner
def _book_scan(files):
    book_files = set()

    for filename, mimetype in files.iteritems():
        ok = (mimetype in ("application/epub+zip",)
              or filename.endswith('.epub')
              or filename.endswith('.txt')
              or filename.endswith('.txt.gz')
              or filename.endswith('.txt.bz2'))
        if ok:
            book_files.add(filename)


    files_in_db = set(Ebook.objects.values_list('filename', flat=True))

    # Add files not yet in DB
    to_add = book_files.difference(files_in_db)
    for filename in to_add:
        title = os.path.splitext(os.path.basename(filename))[0]
        author = None

        try:
            pub = open_epub(filename)

            try:
                title = pub.title
            except (IndexError, AttributeError):
                pass

            try:
                author = pub.author
            except (IndexError, AttributeError):
                pass
        except:
            # Failed to parse
            scan_message("Failed to open Epub file %r" % (filename,))
            return False

        scan_message("Adding book: %r" % (filename,))

        ebook = Ebook(filename=filename, title=title, author=author)
        ebook.save()

    # Remove non-existent entries
    scan_message("Cleaning up non-existing books...")
    to_remove = files_in_db.difference(book_files)
    for filename in to_remove:
        Ebook.objects.get(filename=filename).delete()
