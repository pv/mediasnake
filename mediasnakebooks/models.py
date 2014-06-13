import os
import random

import django.utils.timezone
from django.db import models
from django.utils.encoding import smart_text
from django.db import connection

from mediasnakefiles.scanner import register_scanner, scan_message, asfsunicode
from mediasnakebooks.epubtools import open_epub

UNKNOWN = 5
WELL_KNOWN = 1
IGNORED = 0

MAX_CONTEXT = 3

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

    @classmethod
    def get_known_with_context(cls, language, context_separator=""):
        """
        Get a list of known words, with concatenated context entries.

        Returns items as (base_form, known, notes, context)
        """
        cursor = connection.cursor()
        lang = Language.objects.get(code=language)
        cursor.execute("""
        SELECT w.base_form AS base_form,
               w.known AS known,
               w.notes AS notes,
               GROUP_CONCAT(c.context, %s) AS context
        FROM mediasnakebooks_word AS w
        LEFT JOIN mediasnakebooks_wordcontext AS c ON w.id = c.word_id
        WHERE w.known != 0 AND w.known != 5 AND w.language_id = %s
        GROUP BY w.id
        """, [context_separator, lang.pk])
        return cursor.fetchall()


class WordContext(models.Model):
    word = models.ForeignKey(Word, null=False)
    context = models.TextField(null=False, blank=False)
    timestamp = models.DateTimeField(auto_now=True, auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    @classmethod
    def add(cls, word, context):
        try:
            # avoid inserting duplicates
            ctx_obj = cls.objects.get(word=word, context=context)
            ctx_obj.timestamp = django.utils.timezone.now()
            ctx_obj.save()
            return
        except cls.DoesNotExist:
            pass

        obj = cls(word=word, context=context)
        obj.save()
        cls.cleanup(word, MAX_CONTEXT)

    @classmethod
    def cleanup(cls, word, n):
        """
        Remove entries, keeping at most `n`. Try to maintain a
        specific age distribution.
        """
        if n < 0:
            raise ValueError("n must be positive")

        while True:
            subset = cls.objects.filter(word=word).all()
            count = len(subset)
            if count <= n:
                break
            elif count == 1:
                subset.delete()
                break

            baseline = subset[0].timestamp + (subset[0].timestamp - subset[1].timestamp)
            sum_weight = 0
            cmf = []
            for x in subset:
                weight = 1/(1 + abs((baseline - x.timestamp).total_seconds()))
                sum_weight += weight
                cmf.append(sum_weight)
            cmf = [w/sum_weight for w in cmf]

            p = random.random()
            for j, w in enumerate(cmf):
                if p <= w:
                    subset[j].delete()
                    break
            else:
                raise AssertionError("This can never occur")

    def __unicode__(self):
        c = smart_text(self.context)
        if len(c) > 15:
            return u"%s -- \"%s...\"" % (smart_text(self.word.base_form), c[:15])
        else:
            return u"%s -- \"%s\"" % (smart_text(self.word.base_form), c)


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
    files_in_db = set(asfsunicode(x) for x in Ebook.objects.values_list('filename', flat=True))
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
