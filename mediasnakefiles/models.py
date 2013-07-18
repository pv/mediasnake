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
import json

from django.db import models, transaction
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.urlresolvers import reverse

import django.utils.timezone

from mediasnakefiles.lockfile import LockFile, LockFileError

import logging

logger = logging.getLogger('mediasnake')

SCAN_LOCKFILE = os.path.join(settings.DATA_DIR, 'rescan.lock')
SCAN_STATUS = os.path.join(settings.DATA_DIR, 'rescan.txt')


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
        cls.objects.filter(timestamp__lt=StreamingTicket._threshold())
        

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
    fn = os.path.join(settings.MEDIASNAKEFILES_STREAM_ROOT, instance.secret)
    if os.path.islink(fn):
        os.unlink(fn)


def scan():
    """
    Scan the video directories for files.
    """
    try:
        return _scan()
    except:
        import traceback
        msg = traceback.format_exc()
        logger.error(msg)
        set_scan_status(None)
        raise

def _scan():
    try:
        with LockFile(SCAN_LOCKFILE, fail_if_active=True):
            with transaction.commit_on_success():
                existing_files = set()

                for root in settings.MEDIASNAKEFILES_DIRS:
                    for path, dirs, files in os.walk(root):
                        msg = "Scanning directory: '%s'" % os.path.join(root, path)
                        logger.info(msg)
                        set_scan_status(msg)

                        # Insert new files
                        for basename in files:
                            filename = os.path.normpath(os.path.join(root, path, basename))
                            mimetype = get_mime_type(filename)

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
                                continue

                            existing_files.add(filename)

                            # Check if the file is already there
                            try:
                                video_file = VideoFile.objects.get(filename=filename)
                                continue
                            except VideoFile.DoesNotExist:
                                pass

                            # Create it
                            video_file = VideoFile(filename=filename, mimetype=mimetype)
                            video_file.save()

            # Remove non-existing files
            msg = "Cleaning up non-existing video entries..."
            logger.info(msg)
            set_scan_status(msg)

            files_in_db = set(VideoFile.objects.values_list('filename', flat=True))
            to_remove = files_in_db.difference(existing_files)
            for filename in to_remove:
                VideoFile.objects.get(filename=filename).delete()

            # Create thumbnails, if missing
            objects = VideoFile.objects.all()
            for video_file in objects:
                if video_file.create_thumbnail():
                    msg = "Creating thumbnails: %r" % (video_file.filename,)
                    logger.info(msg)
                    set_scan_status(msg)

            msg = "Scan complete"
            logger.info(msg)
            set_scan_status(None)

            return True
    except LockFileError:
        return False


def set_scan_status(status):
    if status is None:
        try:
            os.unlink(SCAN_STATUS)
        except OSError:
            pass
        return

    now = django.utils.timezone.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S %Z')

    with open(SCAN_STATUS, 'wb') as f:
        obj = {'status': status, 'timestamp': timestamp}
        json.dump(obj, f)


def get_scan_status():
    if LockFile.check(SCAN_LOCKFILE):
        with open(SCAN_STATUS, 'rb') as f:
            return f.read()
    return None
  

def get_thumbnail_filename(thumbnail):
    thumbnail = re.sub('[^a-f0-9]', '', thumbnail)
    return os.path.join(settings.SENDFILE_ROOT, thumbnail) + ".jpg"


def get_mime_type(filename):
    p = subprocess.Popen(['file', '-b', '--mime-type', filename],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        return u""
    else:
        return out.strip()


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


def spawn_rescan():
    base_dir = os.path.abspath(os.path.join(settings.PROJECT_DIR, '..'))
    manage_py = os.path.join(base_dir, 'manage.py')

    devnull_w = open('/dev/null', 'wb')
    devnull_r = open('/dev/null', 'wb')

    python = sys.executable
    env_python = os.path.join(base_dir, 'env', 'bin', 'python')
    if os.path.isfile(env_python):
        python = env_python

    subprocess.Popen([python, manage_py, 'rescan'],
                     stdin=devnull_r, stdout=devnull_w, stderr=devnull_r,
                     cwd=base_dir, close_fds=True)
