"""
Routines for dealing with reading zip etc. files
"""

import re
import os
import tempfile
import shutil

import zipfile
import tarfile
import subprocess


def numeric_file_sort(filelist):
    """Return the given list, sorted by file name, not heeding
       leading zeroes in numbers."""
    
    def sort_key(filename):
        key = ""
        lastend = 0
        for match in re.finditer("\d+", filename):
            key += filename[lastend:match.start()]
            lastend = match.end()
            key += "%08d" % (int(match.group()))
        return key

    lst = list(filelist)
    lst.sort(key=sort_key)
    return lst


class ExtensionMap(dict):
    def __init__(self, dictionary=None):
        dict.__init__(self)
        self.update(dictionary)
        
    def has_key(self, string):
        for key in self.iterkeys():
            if string.lower().endswith(key):
                return True
        return False

    def get(self, string, default=None):
        for key in self.iterkeys():
            if string.lower().endswith(key):
                return dict.__getitem__(self, key)
        return default

    def __contains__(self, string):
        return self.has_key(string)

    def __getitem__(self, string):
        for key in self.iterkeys():
            if string.lower().endswith(key):
                return dict.__getitem__(self, key)
        raise KeyError(string)


class DummyUnpacker(object):
    def __init__(self, archive_filename):
        self.archive = archive_filename
        self._files = None

    @property
    def files(self):
        """Return a list of full pathnames to the archive"""
        if self._files is None:
            self._files = self._get_files()
        return self._files

    def _get_files(self):
        return [self.archive]

    def read_file(self, name):
        """Read contents of a file in the archive"""
        with open(self.archive, 'rb') as f:
            return f.read()

    def _prefix_archive(self, lst):
        return [os.path.join(self.archive, fn) for fn in lst]

    def _unprefix_archive(self, name):
        if not os.path.commonprefix([name, self.archive]) == self.archive:
            raise ValueError("File not in archive!")
        return name[len(self.archive)+1:]
    

class ZipUnpacker(DummyUnpacker):
    def _get_files(self):
        f = zipfile.ZipFile(self.archive, 'r')
        try:
            return self._prefix_archive(f.namelist())
        finally:
            f.close()

    def read_file(self, name):
        name = self._unprefix_archive(name)
        f = zipfile.ZipFile(self.archive, 'r')
        try:
            return f.read(name)
        finally:
            f.close()


class TarUnpacker(DummyUnpacker):
    def _get_files(self):
        f = tarfile.open(self.archive_filename, 'r')
        try:
            return self._prefix_archive(f.getnames())
        finally:
            f.close()

    def read_file(self, name):
        name = self._unprefix_archive(name)
        f = tarfile.open(self.archive_filename, 'r')
        try:
            return f.extractfile(name).read()
        except:
            f.close()


class RarUnpacker(DummyUnpacker):
    def _get_files(self):
        p = subprocess.Popen(["unrar", "vb", self.archive],
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        out, err = p.communicate()
        lst = [fn.strip() for fn in out.split("\n") if fn.strip()]
        return self._prefix_archive(lst)
    
    def read_file(self, name):
        tmpdir = tempfile.mkdtemp()
        name = self._unprefix_archive(name)

        p = subprocess.Popen(["unrar", "e", self.archive, name,
                              tmpdir + os.path.sep],
                             stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        p.communicate()
        
        try:
            basename = os.path.basename(name)
            with open(os.path.join(tmpdir, basename), 'rb') as f:
                return f.read()
        finally:
            shutil.rmtree(tmpdir)


class SevenZipUnpacker(DummyUnpacker):
    def _get_files(self):
        p = subprocess.Popen(["7z", "l", self.archive],
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        out, err = p.communicate()
        begun = False
        lst = []
        for line in out.split("\n"):
            if not begun:
                if line.startswith('-------'):
                    begun = True
                continue
            if line.startswith('------'): break
            lst.append(line[53:])
        return self._prefix_archive(lst)
    
    def read_file(self, name):
        tmpdir = tempfile.mkdtemp()
        name = self._unprefix_archive(name)

        p = subprocess.Popen(["7z", "e", "-o%s" % tmpdir, self.archive, name],
                             stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        p.communicate()
        
        try:
            basename = os.path.basename(name)
            with open(os.path.join(tmpdir, basename), 'rb') as f:
                return f.read()
        finally:
            shutil.rmtree(tmpdir)


def recursive_find(dirname, unpackers, progress_queue=None):
    """
    Return all files under dirname, with associated unpackers (if any).
    """

    pathlist = [os.path.abspath(dirname)]
    files = []
    file_unpackers = {}
    
    while len(pathlist) > 0:
        path = pathlist[0]
        del pathlist[0]

        if os.path.isdir(path):
            if progress_queue:
                progress_queue.put(os.path.basename(path))

            for fn in reversed(numeric_file_sort([os.path.join(path, i)
                                                  for i in os.listdir(path)])):
                pathlist.insert(0, fn)
        elif os.path.isfile(path) and path in unpackers:
            if progress_queue:
                progress_queue.put(os.path.basename(path))

            unpacker = unpackers[path](os.path.abspath(path))

            add_list = numeric_file_sort(unpacker.files)
            for fn in add_list:
                file_unpackers[fn] = unpacker
            files += add_list
        else:
            files.append(path)

    return files, file_unpackers


class PackedFile(object):
    """Get a list of files in given sources, including contents of archives,
    which will be recursively unpacked."""
    
    zip_extension_map = ExtensionMap({
        '.zip': ZipUnpacker,
        '.cbz': ZipUnpacker,
        '.tar': TarUnpacker,
        '.tar.gz': TarUnpacker,
        '.tar.bz2': TarUnpacker,
        '.tbz': TarUnpacker,
        '.tb2': TarUnpacker,
        '.tgz': TarUnpacker,
        '.rar': RarUnpacker,
        '.cbr': RarUnpacker,
        '.7z': SevenZipUnpacker,
        })

    def __init__(self, filename, extensionlist=None, progress_queue=None,
                 accept_ext=None):
        self._files = []
        self._file_unpackers = {}

        if not os.path.isfile(filename):
            raise IOError("not a file")

        fns, ups = recursive_find(filename, PackedFile.zip_extension_map,
                                  progress_queue)
        if accept_ext is not None:
            fns = [fn for fn in fns if os.path.splitext(fn)[1].lower() in accept_ext]
        self._files += fns
        self._file_unpackers.update(ups)

        if extensionlist:
            self._files = [i for i in self._files
                           if os.path.splitext(i)[1].lower() in extensionlist]

    def __repr__(self):
        return "<PackedFile: {}>".format(repr(self._files))

    def __str__(self):
        return str(self._files)

    def __getitem__(self, i):
        return self._files[i]

    def __len__(self):
        return len(self._files)

    def read_file(self, fn):
        unpacker = self._file_unpackers.get(fn)
        if unpacker:
            return unpacker.read_file(fn)
        else:
            return open(fn, 'rb')


class ImagePack(PackedFile):
    extensions = ('.png', '.jpg', '.jpeg', '.gif')

    def __init__(self, filename):
        PackedFile.__init__(self, filename, accept_ext=ImagePack.extensions)
