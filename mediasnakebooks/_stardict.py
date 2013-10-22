import os
import re
import struct
import subprocess
import tempfile
import bisect

_INDEX_CACHE = {}
_INDEX_CACHE_SIZE = 2

class Stardict(object):
    """
    Read dictionary files in StarDict format.

    Parameters
    ----------
    basename : str
        Basename for files. Will use files basename.idx/.dict/.dict.dz

    Methods
    -------
    lookup

    """

    def __init__(self, basename):
        b, ext = os.path.splitext(basename)
        if ext in ('.ifo', '.idx', '.dict', '.dict.dz'):
            basename = b

        self.ifo_file = basename + ".ifo"
        self.idx_file = basename + ".idx"
        self.dict_file = basename + ".dict"
        self.dict_dz_file = basename + ".dict.dz"

        self.dict_file_obj = None
        self.index = []
        self._index_one = None

        self._read_index()

    def __del__(self):
        self.close()

    def close(self):
        if self.dict_file_obj is not None:
            self.dict_file_obj.close()
            self.dict_file_obj = None

    def _read_index(self):
        if not os.path.isfile(self.dict_file):
            if os.path.isfile(self.dict_dz_file):
                self.dict_file_obj = tempfile.TemporaryFile()
                subprocess.call(['dictunzip', "-d", "-k", "-c", self.dict_dz_file],
                                stdout=self.dict_file_obj)

        if self.dict_file_obj is None:
            self.dict_file_obj = open(self.dict_file, 'rb')

        try:
            self.index = _INDEX_CACHE[self.idx_file]
            return
        except KeyError:
            pass

        with open(self.idx_file, 'rb') as idx:
            key_re = re.compile("([^\0]+)\0(........)", re.S)
            self.index = key_re.findall(idx.read())
            self.index.sort()

        if len(_INDEX_CACHE) > _INDEX_CACHE_SIZE:
            _INDEX_CACHE.clear()
        _INDEX_CACHE[self.idx_file] = self.index

    def longest_prefix(self, key):
        """
        Find longest key in dictionary that the given key starts with
        """
        if not isinstance(key, unicode):
            key = key.decode('utf-8')

        while key:
            k = key.encode('utf-8')

            j = bisect.bisect_left(self.index, (k, ""))
            try:
                key2 = self.index[j][0].decode('utf-8')
            except IndexError:
                key = key[:-1]
                continue

            if key == key2:
                return key2

            if key2.startswith(key):
                key = key[:-1]
            else:
                key = os.path.commonprefix([key, key2])

        return None

    def contains(self, key):
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if self._index_one is None:
            self._index_one = dict(self.index)
        return key in self._index_one

    def lookup(self, key):
        if isinstance(key, unicode):
            key = key.encode('utf-8')

        items = []

        j0 = bisect.bisect_left(self.index, (key, ""))
        for j in range(j0, len(self.index)):
            k, data = self.index[j]
            if k != key:
                break

            offset, size = struct.unpack("!2I", data)
            self.dict_file_obj.seek(offset)
            items.append(self.dict_file_obj.read(size).decode('utf-8'))
            j += 1

        return items

    def get(self, key):
        if not isinstance(key, (unicode, str)):
            return None
        if not self.contains(key):
            return None
        r = self.lookup(key)
        if not r:
            return None
        return [(key, None, x) for x in r]
