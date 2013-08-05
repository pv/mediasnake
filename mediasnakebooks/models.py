import os

from django.db import models

from mediasnakefiles.scanner import register_scanner, scan_message
from mediasnakebooks.epubtools import open_epub

UNKNOWN = 5
WELL_KNOWN = 1
IGNORED = 0


class Language(models.Model):
    code = models.CharField(max_length=3, help_text="3-letter ISO language code",
        null=False, primary_key=True, unique=True)
    stardict = models.TextField(null=True, blank=True,
        help_text="Full file name of a Stardict format dictionary (on the server)")
    dict_url = models.TextField(null=True, blank=True,
        help_text="Dictionary URL: @WORD@ is replaced by the word to search for")

    def __unicode__(self):
        return u"%s" % (self.code,)


class Word(models.Model):
    language = models.ForeignKey(Language, null=False)
    base_form = models.CharField(max_length=128, null=False, help_text="Base form of the word",
                                 db_index=True)

    notes = models.TextField(null=True, blank=True)
    known = models.IntegerField(default=5, null=False, blank=False,
        help_text="Knowledge level: 5 - unknown, ..., 1 - well known, 0 - ignored")

    class Meta:
        unique_together = (('language', 'base_form'),)

    def __unicode__(self):
        return u"%s: %s" % (self.language.code, self.base_form)


class Ebook(models.Model):
    filename = models.TextField(null=False)
    title = models.CharField(max_length=128)
    author = models.CharField(max_length=128)

    class Meta:
        index_together = (('author', 'title'),)


class Bookmark(models.Model):
    ebook = models.ForeignKey(Ebook, unique=True)

    chapter = models.IntegerField()
    paragraph = models.IntegerField()

    timestamp = models.DateTimeField(auto_now=True, auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


@register_scanner
def _book_scan(existing_files, mime_cache):
    files_in_db = set(Ebook.objects.values_list('filename', flat=True))
    to_add = existing_files.difference(files_in_db)
    to_remove = files_in_db.difference(existing_files)

    # Add files not yet in DB
    scan_message("Adding books...")
    for filename in to_add:
        ok = (filename.endswith('.epub')
              or filename.endswith('.txt')
              or filename.endswith('.txt.gz')
              or filename.endswith('.txt.bz2'))
        if not ok:
            continue

        title = os.path.splitext(os.path.basename(filename))[0]
        author = None

        try:
            pub = open_epub(filename)
            title = pub.title[:128]
            author = pub.author[:128]
        except:
            # Failed to parse
            scan_message("Failed to open Epub file %r" % (filename,))
            continue

        scan_message("Adding book: %r" % (filename,))

        ebook = Ebook(filename=filename, title=title, author=author)
        ebook.save()

    # Remove non-existent entries
    scan_message("Cleaning up non-existing books...")
    for filename in to_remove:
        Ebook.objects.filter(filename=filename).delete()
