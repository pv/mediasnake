#!/usr/bin/env python
"""
build.py

Build the documentation.

"""
import os
import sys
import shutil
import subprocess
import argparse

def run(cmd, *a, **kw):
    ret = subprocess.call(cmd, *a, **kw)
    if ret != 0:
        print "Running %r failed!" % cmd
        sys.exit(1)

def main():
    p = argparse.ArgumentParser(usage=__doc__.strip())
    p.add_argument('format', metavar='FORMAT', type=str, default='html',
                   choices=('html', 'singlehtml', 'man', 'texinfo'))
    args = p.parse_args()

    run(['sphinx-build', '-b', args.format,
         '.', os.path.join('_build', args.format)])

    if args.format == 'man':
        shutil.copyfile(os.path.join('build', 'man', 'mediasnake.1'),
                        'mediasnake.1')
    
    sys.exit(0)

if __name__ == "__main__":
    main()

