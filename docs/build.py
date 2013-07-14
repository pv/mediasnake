#!/usr/bin/env python
"""
build.py html|github|man

Build the documentation. The 'github' option additionally uploads the
pages to Github gh-pages.

"""
import os
import re
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
                   choices=('html', 'github', 'man'))
    args = p.parse_args()

    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    builder = {'html': 'html',
               'github': 'html',
               'man': 'man'}[args.format]
    run(['sphinx-build', '-b', builder,
         '.', os.path.join('_build', builder)])

    if args.format == 'man':
        shutil.copyfile(os.path.join('build', 'man', 'mediasnake.1'),
                        'mediasnake.1')
    elif args.format == 'github':
        # Build and upload to Github
        pages_repo = os.path.join('_build', 'gh-pages')
        html_dir = os.path.join('_build', 'html')

        if os.path.exists(pages_repo):
            shutil.rmtree(pages_repo)

        run(['git', 'clone', '--reference', os.path.abspath('..'),
             '-o', 'github',
             'git@github.com:pv/mediasnake.git', pages_repo])
        run(['git', 'checkout', '--orphan', 'gh-pages'], cwd=pages_repo)
        run(['git', 'rm', '-rf', '.'], cwd=pages_repo)

        for fn in os.listdir(html_dir):
            if fn in ('.doctrees', '_sources', '.buildinfo'):
                continue
            if re.match(r'.*(\.1|\.bak|~|#)', fn):
                continue
            src = os.path.join(html_dir, fn)
            dst = os.path.join(pages_repo, fn)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copyfile(src, dst)

        with open(os.path.join(pages_repo, '.nojekyll'), 'wb'):
            pass

        run(['git', 'add', '.'], cwd=pages_repo)
        run(['git', 'commit', '-m', 'Rebuild HTML'], cwd=pages_repo)
        run(['git', 'push', '-f', 'github', 'gh-pages'], cwd=pages_repo)

    sys.exit(0)

if __name__ == "__main__":
    main()

