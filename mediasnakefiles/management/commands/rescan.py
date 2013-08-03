from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache

from mediasnakefiles.scanner import scan, SCAN_LOCKFILE

class Command(BaseCommand):
    args = ''
    help = 'Rescans the video_dirs for videos'

    def handle(self, *args, **options):
        ok = scan()
        if not ok:
            raise CommandError(("Lock file %r exists -- another rescan is "
                                "already running") % SCAN_LOCKFILE)

        cache.clear()
