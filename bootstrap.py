#!/usr/bin/env python
import os
import subprocess

def run(*a, **kw):
    ret = subprocess.call(*a, **kw)
    if ret != 0:
        print("Error runnning: %r" % a)
        raise SystemExit(1)

def main():
    run(['virtualenv', 'env'])
    print("\n\n" + "-"*79)
    print("Downloading and installing requirements")
    print("\n\n")
    run(['./env/bin/pip', 'install', '-r', 'requirements.txt'])
    print("\n\n" + "-"*79)
    print("Answer 'yes' to whether you want to create a superuser")
    print("\n\n")
    run(['./env/bin/python', 'manage.py', 'syncdb'])
    run(['./env/bin/python', 'manage.py', 'migrate'])
    print("\n\n" + "-"*79)
    print("Answer 'yes' to the question")
    print("\n\n")
    run(['./env/bin/python', 'manage.py', 'collectstatic'])
    print("\n\n" + "-"*79)
    print("Database + environment setup done!")
    print("\n\n")

if __name__ == "__main__":
    main()
