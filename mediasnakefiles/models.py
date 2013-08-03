import os
import sys
import re
import hmac
import subprocess
import tempfile
import hashlib
import datetime
import fnmatch
import random

from django.db import models, transaction
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.urlresolvers import reverse

import django.utils.timezone

import logging

from mediasnakefiles.scanner import register_file_scanner, register_post_scanner, scan_message

logger = logging.getLogger('mediasnake')


class VideoFile(models.Model):
    filename = models.TextField()

    mimetype = models.CharField(max_length=256)
    thumbnail = models.CharField(max_length=256)

    @property
    def basename(self):
        return os.path.basename(self.filename)

    @property
    def extension(self):
        return os.path.splitext(self.filename)[1].lstrip('.')

    @property
    def relative_dirname(self):
        for dn in settings.MEDIASNAKEFILES_DIRS:
            dn = os.path.normpath(dn)
            if self.filename.startswith(dn + os.path.sep):
                root = dn
                break
        else:
            dn = settings.MEDIASNAKEFILES_DIRS[0]
            root = os.path.normpath(dn)

        return os.path.relpath(os.path.dirname(self.filename),
                               root)

    @property
    def title(self):
        title = os.path.splitext(self.basename)[0]
        title = re.sub(r'\[.*?\]', '', title)
        title = re.sub(r'\(.*?\)', '', title)
        title = re.sub(r'{.*?}', '', title)
        title = re.sub(r'[_-]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        title = title.strip()
        
        if title:
            return title[0].upper() + title[1:]
        else:
            return self.basename

    @property
    def thumbnail_filename(self):
        if not self.thumbnail:
            return None
        return get_thumbnail_filename(self.thumbnail)

    def create_thumbnail(self):
        if not os.path.isfile(self.filename):
            raise RuntimeError("Not a file")

        # Create a deterministic thumbnail name
        thumbnail = hash_content(self.filename)
        thumbnail_filename = get_thumbnail_filename(thumbnail)

        if self.thumbnail != thumbnail:
            self.thumbnail = thumbnail
            self.save()

        if os.path.isfile(thumbnail_filename):
            return False

        if not os.path.isdir(settings.SENDFILE_ROOT):
            os.makedirs(settings.SENDFILE_ROOT)

        fd, tmpfn = tempfile.mkstemp(dir=settings.SENDFILE_ROOT, prefix='tmp-', suffix=".jpg")
        try:
            os.close(fd)
            p = subprocess.Popen([settings.MEDIASNAKEFILES_FFMPEGTHUMBNAILER,
                                  "-cjpeg", "-s320",
                                  "-i" + self.filename,
                                  "-o" + tmpfn],
                                 stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 stdout=subprocess.PIPE)
            p.communicate()
            if p.returncode != 0:
                return False

            os.rename(tmpfn, thumbnail_filename)
        except:
            os.unlink(tmpfn)

        return True

    def get_all_versions(self):
        base, ext = os.path.splitext(self.basename)
        rel_base = os.path.sep + os.path.join(self.relative_dirname, base + '.')
        return [x for x in VideoFile.objects.filter(filename__contains=rel_base)
                if x.relative_dirname == self.relative_dirname and x.basename.startswith(base + '.')]

    def __str__(self):
        return "VideoFile: '%s/%s'" % (self.relative_dirname, self.basename)

class StreamingTicket(models.Model):
    secret = models.CharField(max_length=128, null=False, unique=True)
    video_file = models.ForeignKey(VideoFile, null=False)
    timestamp = models.DateTimeField()
    remote_address = models.IPAddressField()

    @classmethod
    def new_for_video(cls, video_file, remote_address):
        secret = get_secret_128(video_file.filename)
        return StreamingTicket(secret=secret, video_file=video_file,
                               remote_address=remote_address,
                               timestamp=django.utils.timezone.now())

    @property
    def dummy_name(self):
        return "file" + os.path.splitext(self.video_file.filename)[1]

    @property
    def url(self):
        if settings.MEDIASNAKEFILE_HTTP_ADDRESS:
            url = (settings.MEDIASNAKEFILE_HTTP_ADDRESS.rstrip('/')
                   + settings.URL_PREFIX.rstrip('/')
                   + '/ticket/' + self.secret + '/'
                   + self.dummy_name)
        else:
            url = (reverse('ticket', args=[self.secret]).rstrip('/')
                   + '/' + self.dummy_name)
        return url

    def is_valid(self, remote_address):
        return (self.timestamp >= StreamingTicket._threshold() and
                self.remote_address == remote_address)

    def create_symlink(self):
        path = settings.SENDFILE_ROOT
        dst = os.path.join(path, self.secret)
        if not os.path.islink(dst):
            if not os.path.isdir(path):
                os.makedirs(path)
            os.symlink(self.video_file.filename, dst)
        return dst

    @staticmethod
    def _threshold():
        delta = datetime.timedelta(seconds=int(3600*settings.MEDIASNAKEFILES_TICKET_LIFETIME_HOURS))
        return django.utils.timezone.now() - delta

    @classmethod
    def cleanup(cls):
        cls.objects.filter(timestamp__lt=StreamingTicket._threshold()).delete()
        

@receiver(post_delete, sender=VideoFile)
def _video_file_cleanup_thumbnails(sender, instance, using, **kwargs):
    """
    Remove thumbnails when the video is removed from the database.
    """
    fn = instance.thumbnail_filename
    if not fn:
        return
    if os.path.isfile(fn):
        os.unlink(fn)


@receiver(post_delete, sender=StreamingTicket)
def _streaming_ticket_cleanup_symlink(sender, instance, using, **kwargs):
    """
    Remove thumbnails when the video is removed from the database.
    """
    fn = os.path.join(settings.SENDFILE_ROOT, instance.secret)
    if os.path.islink(fn):
        os.unlink(fn)


@register_file_scanner
def _video_file_scanner(filename, mimetype):
    basename = os.path.basename(filename)
    
    # Check that the extension and mime type
    # are indicative of a video file
    for file_pattern, mime_pattern, replacement_mimetype in \
            settings.MEDIASNAKEFILES_ACCEPTED_FILE_TYPES:
        if (fnmatch.fnmatch(mimetype, mime_pattern) and
            fnmatch.fnmatch(basename, file_pattern)):
            if replacement_mimetype is not None:
                mimetype = replacement_mimetype
            break
    else:
        return False

    # Check if the file is already there
    try:
        video_file = VideoFile.objects.get(filename=filename)
    except VideoFile.DoesNotExist:
        video_file = VideoFile(filename=filename, mimetype=mimetype)
        video_file.save()

    return True


@register_post_scanner
def _video_file_post_scan(existing_files):
    # Remove non-existent entries
    files_in_db = set(VideoFile.objects.values_list('filename', flat=True))
    to_remove = files_in_db.difference(existing_files)
    for filename in to_remove:
        VideoFile.objects.get(filename=filename).delete()

    # Create thumbnails, if missing
    objects = VideoFile.objects.all()
    for video_file in objects:
        if video_file.create_thumbnail():
            scan_message("Creating thumbnails: %r" % (video_file.filename,))
  

def get_thumbnail_filename(thumbnail):
    thumbnail = re.sub('[^a-f0-9]', '', thumbnail)
    return os.path.join(settings.SENDFILE_ROOT, thumbnail) + ".jpg"


def hash_content(filename):
    """
    Create a hex digest based on filename and (partial) file contents
    """
    block_size = 65536

    content_hash = hashlib.sha1()

    with open(filename, 'rb') as f:
        block = f.read(block_size)
        content_hash.update(block)

        f.seek(0, 2)
        f.seek(f.tell() - block_size)
        block = f.read(65536)
        content_hash.update(block)

        f.seek(f.tell()//2)
        block = f.read(65536)
        content_hash.update(block)

    return content_hash.hexdigest()


def get_secret_128(salt=""):
    x = hmac.HMAC(settings.SECRET_KEY + salt)
    x.update(get_random_bytes(128))

    secret = x.hexdigest()
    for k in range(3):
        x.update(secret)
        x.update(get_random_bytes(128))
        secret += x.hexdigest()

    return secret


def get_random_bytes(nbytes):
    return "".join(chr(random.getrandbits(8)) for _ in range(nbytes))
