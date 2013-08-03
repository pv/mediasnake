import os
import sys
import logging
import json
import subprocess

from django.db import transaction
from django.conf import settings

import django.utils.timezone

from mediasnakefiles.lockfile import LockFile, LockFileError

logger = logging.getLogger('mediasnake')

SCAN_LOCKFILE = os.path.join(settings.DATA_DIR, 'rescan.lock')
SCAN_STATUS = os.path.join(settings.DATA_DIR, 'rescan.txt')

SCAN_HOOKS = []
SCAN_POST_HOOKS = []

def register_file_scanner(func):
    if func not in SCAN_HOOKS:
        SCAN_HOOKS.append(func)

def register_post_scanner(func):
    if func not in SCAN_POST_HOOKS:
        SCAN_POST_HOOKS.append(func)

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
            existing_files = set()

            with transaction.commit_on_success():
                for root in settings.MEDIASNAKEFILES_DIRS:
                    for path, dirs, files in os.walk(root):
                        msg = "Scanning directory: '%s'" % os.path.join(root, path)
                        logger.info(msg)
                        set_scan_status(msg)

                        # Insert new files
                        for basename in files:
                            filename = os.path.normpath(os.path.join(root, path, basename))
                            mimetype = get_mime_type(filename)

                            existing_files.add(filename)

                            for hook in SCAN_HOOKS:
                                if hook(filename, mimetype):
                                    break

            # Remove non-existing files
            scan_message("Cleaning up non-existing entries...")

            with transaction.commit_on_success():
                for hook in SCAN_POST_HOOKS:
                    hook(existing_files)

            scan_message("Scan complete")
            set_scan_status(None)
            return True
    except LockFileError:
        return False


def scan_message(msg):
    logger.info(msg)
    set_scan_status(msg)


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
  

def get_mime_type(filename):
    p = subprocess.Popen(['file', '-b', '--mime-type', filename],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        return u""
    else:
        return out.strip()


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
