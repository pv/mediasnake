import os

from io import BytesIO
from configobj import ConfigObj, flatten_errors
from validate import Validator

SPEC = """\
url_prefix = string(default=/)
data_dir = string(default=data)
server = option('default', 'nginx', default='default')
video_dirs = list()
"""

CONFIG_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'config.ini'))

if not os.path.isfile(CONFIG_FILE):
    print("-"*79)
    print("Configuration file '%s' is missing" % CONFIG_FILE)
    print("-"*79)
    raise SystemExit(1)

spec = ConfigObj(BytesIO(SPEC))
ini = ConfigObj(CONFIG_FILE, configspec=BytesIO(SPEC))

if isinstance(ini['video_dirs'], str):
    ini['video_dirs'] = (ini['video_dirs'],)

extra_errors = []
for item, value in sorted(ini.items()):
    if item not in spec:
        extra_errors.append('- %s: unknown setting' % (item,))
        continue
    
val = Validator()
validation = ini.validate(val, preserve_errors=True)

if validation != True or extra_errors:
    print("-"*79)
    print("Configuration file '%s' has the following errors:" % CONFIG_FILE)
    for error in extra_errors:
        print error
    for sections, key, error in sorted(flatten_errors(ini, validation)):
        print "- %s: %s: %s" % (" ".join("[%s]" % x for x in sections),
                                key,
                                error)
    print("-"*79)
    raise SystemExit(1)
