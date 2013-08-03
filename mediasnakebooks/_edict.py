import re

def parse_edict(popular_only=False, xref_word=False, xref_reading=False):
    """
    Load EDICT dictionary
    """

    edict = {}

    edict_fn = '/usr/share/edict/edict'
    edict_codec = 'euc-jp'

    with open(edict_fn, 'rb') as f:
        f.readline() # skip header
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                continue
            line = unicode(line, edict_codec)
            key, rest = re.split(u'[ \t]+', line, 1)
            key = key.strip()

            if not key:
                continue

            # only consider (P) meanings
            if popular_only and u'/(P)/' not in rest:
                continue
            # never take archaic meanings...
            if '/(arch)/' in rest:
                continue

            m = re.match(ur'^\[([^\]]*)\] (.*)$', rest)
            if m:
                reading = m.group(1)
                meaning = m.group(2)
            else:
                reading = key
                meaning = rest

            is_katakana = re.match(u'^[\u30a0-\u31ff]*$', key) is not None
            is_hiragana = re.match(u'^[\u3041-\u309f]*$', key) is not None
            if is_katakana or is_hiragana:
                # no reading needed
                reading = None

            ref = (key, reading, meaning)
            edict[(key, reading)] = ref
            if xref_word:
                edict.setdefault(key, set()).add(ref)
            if xref_reading:
                edict.setdefault(reading, set()).add(ref)

    return edict
