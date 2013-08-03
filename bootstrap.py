#!/usr/bin/env python
import os
import re
import subprocess
import random

def main():
    set_secret_key()
    run(['virtualenv', '--system-site-packages', 'env'])
    print("\n\n" + "-"*79)
    print("Downloading and installing requirements")
    print("\n\n")
    run(['./env/bin/pip', 'install', '-r', 'requirements.txt', '--use-mirrors'])
    print("\n\n" + "-"*79)
    print("Answer 'yes' to whether you want to create a superuser")
    print("\n\n")
    run(['./env/bin/python', 'manage.py', 'syncdb'])
    run(['./env/bin/python', 'manage.py', 'migrate'])
    run(['./env/bin/python', 'manage.py', 'loaddata', 'base'])
    print("\n\n" + "-"*79)
    print("Answer 'yes' to the question")
    print("\n\n")
    run(['./env/bin/python', 'manage.py', 'collectstatic'])
    print("\n\n" + "-"*79)
    print("Database + environment setup done!")
    print("\n\n")

def run(*a, **kw):
    ret = subprocess.call(*a, **kw)
    if ret != 0:
        print("Error runnning: %r" % a)
        raise SystemExit(1)

def set_secret_key():
    """Try to be helpful and fill secret_key with random data"""
    key = "".join([chr(random.randint(33, 125)) for _ in range(64)])
    key = key.replace('"', "'")
    key = key.replace("\\", "\\\\")

    try:
        with open('config.ini', 'rb') as f:
            ini = f.read()

        ini2 = re.sub(r'^\s*secret_key\s*=\s*"[^"]*"\s*$',
                      r'secret_key = "%s"' % key,
                      ini,
                      0,
                      re.M)

        with open('config.ini', 'w') as f:
            f.write(ini2)
    except (OSError, IOError):
        # permission error or something, just fail quietly
        pass

if __name__ == "__main__":
    main()
