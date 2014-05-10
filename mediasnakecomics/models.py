import os
import random

import django.utils.timezone
from django.db import models
from django.utils.encoding import smart_text
from django.db import connection

from mediasnakefiles.scanner import register_scanner, scan_message


class Comic(models.Model):
    filename = models.TextField(null=False)
    title = models.CharField(max_length=128)
    path = models.CharField(max_length=128)

    class Meta:
        index_together = (('path', 'title'),)


class Bookmark(models.Model):
    comic = models.ForeignKey(Comic, unique=True)
    page = models.IntegerField()
    timestamp = models.DateTimeField(auto_now=True, auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


@register_scanner
def _comic_scan(existing_files, mime_cache):
    files_in_db = set(Comic.objects.values_list('filename', flat=True))
    to_add = existing_files.difference(files_in_db)
    to_remove = files_in_db.difference(existing_files)

    # Add files not yet in DB
    scan_message("Adding comics...")
    for filename in to_add:
        ok = (filename.endswith('.cbz')
              or filename.endswith('.zip')
              or filename.endswith('.rar'))
        if not ok:
            continue

        title = os.path.splitext(os.path.basename(filename))[0]
        path = os.path.basename(os.path.dirname(filename))

        scan_message("Adding comic: %r" % (filename,))

        comic = Comic(filename=filename, title=title, path=path)
        comic.save()

    # Remove non-existent entries
    scan_message("Cleaning up non-existing comics...")
    for filename in to_remove:
        Comic.objects.filter(filename=filename).delete()
