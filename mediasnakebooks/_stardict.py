import os
import re
import struct
import ctypes
import subprocess
import tempfile
import numpy as np

class Stardict(object):
    """
    Read dictionary files in StarDict format.

    Parameters
    ----------
    basename : str
        Basename for files. Will produce files basename.ifo/.idx/.dict/.dict.dz

    Methods
    -------
    lookup

    """

    def __init__(self, basename):
        self.ifo_file = basename + ".ifo"
        self.idx_file = basename + ".idx"
        self.dict_file = basename + ".dict"
        self.dict_dz_file = basename + ".dict.dz"

        self.dict_file_obj = None
        self.index = {}

        self._read_index()

    def _read_index(self):
        if not os.path.isfile(self.dict_file):
            if os.path.isfile(self.dict_dz_file):
                self.dict_file_obj = tempfile.TemporaryFile()
                subprocess.call(['dictunzip', "-d", "-k", "-c", self.dict_dz_file],
                                stdout=self.dict_file_obj)

        if self.dict_file_obj is None:
            self.dict_file_obj = open(self.dict_file, 'rb')

        with open(self.idx_file, 'rb') as idx:
            keys_b = []
            offsets_b = []
            sizes_b = []

            key_re = re.compile("([^\0]+)\0(....)(....)", re.S)

            for key_b, offset_b, size_b in key_re.findall(idx.read()):
                keys_b.append(key_b)
                offsets_b.append(offset_b)
                sizes_b.append(size_b)

            self.keys = "\0".join(keys_b).decode('utf-8').split(u"\0")

            offsets_b = "".join(offsets_b)
            self.offsets = np.fromstring(offsets_b, '>u4') # struct.unpack("!%dI" % (len(offsets_b)//4,), offsets_b)

            sizes_b = "".join(sizes_b)
            self.sizes = np.fromstring(sizes_b, '>u4') # struct.unpack("!%dI" % (len(sizes_b)//4,), sizes_b)

    def lookup(self, key):
        try:
            j1 = self.keys.index(key)
        except IndexError:
            return []

        j2 = j1
        while j2 < len(self.keys) and self.keys[j2] == self.keys[j1]:
            j2 += 1

        items = []
        for j in range(j1, j2):
            offset = self.offsets[j]
            size = self.sizes[j]

            self.dict_file_obj.seek(offset)
            items.append(self.dict_file_obj.read(size).decode('utf-8'))

        return items
