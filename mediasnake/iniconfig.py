from __future__ import print_function

import os
import sys

from io import BytesIO
from configobj import ConfigObj, flatten_errors
from validate import Validator

SPEC = """\
url_prefix = string()
data_dir = string()
file_serving = option(default, nginx)
hostnames = list()
video_dirs = list()
secret_key = string()
debug = boolean()
http_streaming_address = string()
"""

CONFIG_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'config.ini'))

if not os.path.isfile(CONFIG_FILE):
    print("-"*79, file=sys.stderr)
    print("Configuration file '%s' is missing" % CONFIG_FILE, file=sys.stderr)
    print("-"*79, file=sys.stderr)
    raise SystemExit(1)

spec = ConfigObj(BytesIO(SPEC))
ini = ConfigObj(CONFIG_FILE, configspec=BytesIO(SPEC))

for key in ['video_dirs', 'hostnames']:
    if key in ini and isinstance(ini[key], str):
        ini[key] = (ini[key],)

extra_errors = []
for item, value in sorted(ini.items()):
    if item not in spec:
        extra_errors.append("- '%s': unknown setting" % (item,))
        continue
    
val = Validator()
validation = ini.validate(val, preserve_errors=True)

if validation != True or extra_errors:
    print("-"*79, file=sys.stderr)
    print("Configuration file '%s' has the following errors:\n" % CONFIG_FILE, file=sys.stderr)
    for error in extra_errors:
        print(error, file=sys.stderr)
    for sections, key, error in sorted(flatten_errors(ini, validation)):
        if error is False:
            error = "missing"
        print("- '%s': %s" % (key, error), file=sys.stderr)
    print("-"*79, file=sys.stderr)
    raise SystemExit(1)
