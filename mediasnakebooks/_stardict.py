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

            if j > 0:
                key2 = self.index[j-1][0].decode('utf-8')
            else:
                key2 = None
            if j < len(self.index):
                key3 = self.index[j][0].decode('utf-8')
            else:
                key3 = None

            if not (key2 or key3):
                return None

            if key == key2:
                return key2
            elif key == key3:
                return key3

            if key2:
                prefix2 = os.path.commonprefix([key, key2])
            else:
                prefix2 = u""

            if key3:
                prefix3 = os.path.commonprefix([key, key3])
            else:
                prefix3 = u""

            if len(prefix2) < len(key) and len(prefix2) > len(prefix3):
                key = prefix2
            elif len(prefix3) < len(key):
                key = prefix3
            else:
                key = key[:-1]

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
