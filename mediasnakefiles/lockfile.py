import os
import time
import errno


class LockFileError(RuntimeError):
    pass


class LockFile(object):
    """
    Lock file (Unix-only), implemented via symlinks.
    """

    def __init__(self, filename, timeout=0.05, fail_if_active=False):
        self.filename = filename
        self.timeout = timeout
        self.fd = None
        self.fail_if_active = fail_if_active

    @classmethod
    def check(self, filename):
        # Check if the lockfile exists
        try:
            pid = int(os.readlink(filename))
        except OSError as err:
            if err.errno == errno.ENOENT:
                return False
            raise

        # Check if the process is still alive
        try:
            os.kill(pid, 0)
        except OSError as err:
            if err.errno == errno.ESRCH:
                # no such process
                return False
            raise

        # Seems to be still around
        return True

    def __enter__(self):
        tries = 0
        while True:
            if tries > 0:
                if self.fail_if_active:
                    raise LockFileError("Process is already running")
                else:
                    time.sleep(self.timeout)

            try:
                os.symlink(str(os.getpid()), self.filename)
                break
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise

                try:
                    pid = int(os.readlink(self.filename))
                except OSError as err:
                    if err.errno == errno.ENOENT:
                        continue
                    raise

                # Check if it's still alive
                try:
                    os.kill(pid, 0)
                except OSError as err:
                    if err.errno == errno.ESRCH:
                        # no such process
                        os.unlink(self.filename)
                        continue
                    raise

            tries += 1

    def __exit__(self, type, value, traceback):
        os.unlink(self.filename)
