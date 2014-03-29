# -*- coding: utf-8 -*-

import re
import subprocess
import collections

MecabPart = collections.namedtuple('MecabPart', [
    'surface', 'form', 'base', 'reading', 'base_reading'
])

class Mecab(object):
    def __init__(self):
        self.pipe = None
        self.encoding = None
        self.args = []

        self._detect_encoding()
        self._detect_fields()

        self.pipe = self._pipe(self.args)

    def __del__(self):
        self.close()

    def close(self):
        if self.pipe:
            self.pipe.communicate()
            self.pipe = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _pipe(self, args):
        args = ["mecab"] + list(args)
        try:
            return subprocess.Popen(args, bufsize=-1,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        except OSError:
            raise RuntimeError("Please install mecab")

    def _detect_encoding(self):
        p = subprocess.Popen(['mecab', '-D'],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        for line in out.splitlines():
            if line.startswith('charset:'):
                self.encoding = line[8:].strip()
                break
        else:
            raise RuntimeError("Failed to determine mecab charset")

    def _detect_fields(self):
        """
        Detect in which fields the mecab dictionary provides which information
        """

        pipe = self._pipe(["--node-format=%H\n", "--unk-format=%H\n"])
        inp = (u"守ります").encode(self.encoding)
        out, err = pipe.communicate(inp)

        lines = out.decode(self.encoding).splitlines()
        fields = lines[0].split(",")

        form_idx = None
        reading_idx = None
        base_idx = None

        for j, field in enumerate(fields):
            if base_idx is None:
                if u"守る" in field:
                    base_idx = j

            if reading_idx is None:
                if kata2hira(field) == u"まもり":
                    reading_idx = j

            if form_idx is None:
                if field == u"動詞":
                    form_idx = j

        fmt = '%%m\01%%f[%d]\01%%f[%d]\01%%f[%d]\n' % (
            form_idx, base_idx, reading_idx)

        self.args = [
            '--eos-format=EOS\n',
            '--node-format=' + fmt,
            '--unk-format=%m\01\01\01\n',
        ]

    def parse(self, expr):
        expr = expr.replace(u"\n", u" ")
        expr = expr.replace(u'\uff5e', u"~")

        self.pipe.stdin.write(expr.encode(self.encoding, "ignore") + '\n')
        self.pipe.stdin.flush()

        out = []
        while True:
            try:
                line = self.pipe.stdout.readline().decode(self.encoding).strip()
            except UnicodeDecodeError:
                continue
            if line == u"EOS":
                break

            item = line.split("\01")

            surface = item[0]
            if item[1]:
                form = item[1]
            else:
                form = None

            if item[2]:
                base = re.sub(ur'^.*:', ur'', item[2])
                # strip unnecessary copula
                if base.endswith(u"だ") and not surface.endswith(u"だ"):
                    base = base[:-1]
            else:
                base = None

            if item[3]:
                reading = kata2hira(item[3])
            else:
                reading = None

            if base is not None and is_kana_only(base):
                base_reading = kata2hira(base)
            elif form == u"名詞":
                base_reading = reading
            else:
                base_reading = None

            out.append(MecabPart(surface, form, base, reading, base_reading))

        return out

    def collapse(self, items, auxiliary=True):
        new_item = [u"", None, None, None, None]
        new_items = []

        def flush():
            if new_item[0]:
                new_items.append(MecabPart(*new_item))
                new_item[:] = [u"", None, None, None, None]

        AUX_VERBS = (u"れる", u"られる", u"いる", u"おる")
        NO_JOIN = (u"という", u"と", u"が", u"の", u"に", u"は", u"から")

        in_conjugation = False
        for w in items:
            join_it = True
            join_it = join_it and in_conjugation
            join_it = join_it and w.form and (w.form.startswith(u'助') or (
                w.form == u"動詞" and w.base in AUX_VERBS)) and auxiliary
            join_it = join_it and w.base not in NO_JOIN

            if join_it:
                new_item[0] += w.surface
                if new_item[3] is not None:
                    new_item[3] += w.reading
            else:
                in_conjugation = w.form in (u"動詞", u"形容詞", u"助動詞")
                flush()
                new_item[:] = list(w)
        flush()

        return new_items

    def dict_collapse(self, items, edict, max_distance=5, auxiliary=True, reading_check=True):
        parts = self.collapse(list(items), auxiliary=auxiliary)
        new_parts = []

        while parts:
            part = parts.pop(0)

            if part.form and part.form.startswith(u'助') and auxiliary:
                new_parts.append(part)
                continue

            surface = part.surface
            form = part.form
            base = part.base
            reading = part.reading
            base_reading = part.base_reading

            # Try to grab base reading from edict
            if not base_reading and base and reading:
                res = edict.get((base, reading))
                if res:
                    base_reading = res[1]
            if not base_reading and base:
                res = edict_readings(edict, base)
                if len(res) == 1:
                    base_reading = list(res)[0]
            if not base_reading and reading:
                res = edict_readings(edict, reading)
                if res and len(res) == 1:
                    base_reading = list(res)[0]

            # Check for to-adv not recognized by mecab but in edict
            if (surface.endswith(u'と')
                and is_kana_only(surface)
                and (not base or base == surface)
                and not edict.get(surface)
                and edict.get(surface[:-1])):
                base = surface[:-1]
                base_reading = surface[:-1]

            # Check how long words can be found in edict 
            good_j = -1
            trial = surface
            trial_reading = reading
            for j in range(0, max_distance):
                if j >= len(parts):
                    break

                trial_reading2 = None
                if parts[j].base:
                    trial2 = trial + parts[j].base
                    if trial_reading and parts[j].base_reading:
                        trial_reading2 = trial_reading  + parts[j].base_reading
                else:
                    trial2 = None

                trial += parts[j].surface
                if not parts[j].reading:
                    trial_reading = None
                if trial_reading is not None:
                    trial_reading += parts[j].reading

                res = edict.get(trial)
                if res is None and trial2 is not None:
                    res = edict.get(trial2)

                if trial_reading and res and reading_check:
                    # pick only dictionary entries with matching reading
                    new_res = []
                    for dictitem in res:
                        z = dictitem[1] or dictitem[0]
                        if z in (trial_reading, trial_reading2):
                            new_res.append(dictitem)
                    res = new_res

                if res:
                    if parts[j].form == u"動詞" and parts[j].base == u"する":
                        # don't join suru to suru-verbs
                        continue

                    # refuse to guess between multiple possibilities
                    if len(res) == 1:
                        res = list(res)[0]
                    else:
                        res_popular = [x for x in res if u"/(P)/" in x[2]]
                        if len(res_popular) == 1:
                            res = res_popular[0]
                        else:
                            continue

                    # substitute
                    surface = trial
                    form = parts[j].form
                    base = res[0]
                    reading = trial_reading
                    base_reading = res[1]
                    good_j = j

            if not reading and is_kana_only(surface):
                reading = kata2hira(surface)

            if good_j >= 0:
                del parts[:good_j+1]
            new_parts.append(MecabPart(surface, form, base, reading,
                                       base_reading))

        return new_parts


def edict_readings(edict, lookup):
    res = edict.get(lookup)
    if res:
        readings = set()
        for _, reading, _ in res:
            readings.add(reading)
        return readings
    return set()


def kata2hira(s):
    """Convert katakana to hiragana"""
    kata_start = 0x30a1
    kata_end = 0x30fa
    hira_start = 0x3041
    return u"".join(unichr(ord(x) + hira_start - kata_start)
                    if ord(x) >= kata_start and ord(x) <= kata_end else x
                    for x in s)


def is_kana_only(s):
    m = re.match(u'^[\u3041-\u309f\u30a1-\u30ff]*$', s)
    return bool(m)
