#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webm-transcode.py -o OUTDIR [INPUT...]

Transcode all video files in an input directory to WEBM, producing a
similar directory structure. Maximum bitrate can be specified.

Existing files are not overwritten.

Subtitles are hardcoded to the video output.

Uses ffmpeg/ffprobe + mkvmerge for transcoding.

"""
from __future__ import absolute_import, print_function, division

import os
import re
import shutil
import argparse
import tempfile
import datetime
import subprocess
import json
import time
import multiprocessing


def main():
    p = argparse.ArgumentParser(usage=__doc__.lstrip())
    p.add_argument("-o", type=str, dest="outdir", metavar="OUTDIR",
                   default=None, help="Output directory")
    p.add_argument("-b", type=float, default=600, dest="kbitrate",
                   metavar="RATE", help="Maximum total bitrate in kbit/s [default: 600]")
    p.add_argument("-j", "--jobs", type=int, default=1, dest="jobs",
                   metavar="N", help="Maximum number of jobs to run in parallel")
    p.add_argument("-f", "--fast", action="store_true", dest="fast",
                   help="Perform fast but lower-quality transcoding")
    p.add_argument("-l", '--language-select', dest="language_select",
                   default=None, metavar='LANG1,LANG2,...',
                   help=("Language selection order if there are more than one audio/video streams. "
                         "Use ISO-639-2 three-letter language codes. "
                         "If this option is not given, all streams are included."))
    p.add_argument("input", nargs='+', metavar='INPUT',
                   help="Input directories or files")
    args = p.parse_args()

    if args.outdir is None:
        p.error("No output directory specified")

    if args.jobs < 1:
        p.error("Number of parallel jobs must be >= 1")

    if not os.path.isdir(args.outdir):
        p.error("Output directory is not a directory")

    ext = '.webm'
    jobs = []

    for input_arg in args.input:
        if os.path.isdir(input_arg):
            for path, dirs, files in os.walk(input_arg):
                dirs.sort()
                files.sort()
                rpath = os.path.relpath(path, input_arg)
                for basename in files:
                    src = os.path.normpath(os.path.join(path, basename))
                    dst_basename = os.path.splitext(basename)[0] + ext
                    dst = os.path.normpath(os.path.join(args.outdir, rpath,
                                                        dst_basename))
                    jobs.append((src, dst, args))
        else:
            src = input_arg
            dst = os.path.join(args.outdir, os.path.basename(src))
            jobs.append((src, dst, args))

    pool = multiprocessing.Pool(args.jobs)
    try:
        for res in pool.imap_unordered(_process_file_mp, jobs):
            if not res:
                break
    except KeyboardInterrupt:
        pool.terminate()
        print("\n\nInterrupted!")
    finally:
        pool.close()
        pool.join()

def _process_file_mp(a):
    try:
        process_file(*a)
        return True
    except KeyboardInterrupt:
        return False

def process_file(src, dst, options):
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)

    print("\n")
    print("-"*79)
    print("Src:", src)
    print("Dst:", dst)
    print("")

    if os.path.exists(dst):
        print("Already exists, skipping")
        return

    _, ext = os.path.splitext(src)
    _, dst_ext = os.path.splitext(dst)

    if ext not in ('.avi', '.ogg', '.ogv', '.ogm', '.mp4', '.mpg',
                   '.mpeg', '.mkv', '.webm'):
        print("Probably not a video file -- skipping")
        return

    dst_dir = os.path.dirname(dst)
    if not os.path.isdir(dst_dir):
        try: os.makedirs(dst_dir)
        except OSError: pass

    tmpdir = tempfile.mkdtemp()
    fd, tmpfn = tempfile.mkstemp(dir=os.path.dirname(dst), suffix=dst_ext)
    try:
        os.close(fd)
        return _process_file(src, dst, options, tmpfn, tmpdir)
    finally:
        shutil.rmtree(tmpdir)
        if os.path.exists(tmpfn):
            os.unlink(tmpfn)


def _process_file(src, dst, options, tmpfn, tmpdir):
    assert os.path.isfile(src)

    # Remux: ffmpeg is very brittle
    if not src.endswith('.mkv'):
        tmp_src = os.path.join(tmpdir, 'tmp.mkv')
        try:
            run(['mkvmerge', '-o', tmp_src, src], echo=True)
            src = tmp_src
        except CommandError:
            pass

    try:
        info = VideoFileInfo(src)
    except VideoFileError:
        print("Video file error --- it is really broken: skipping")
        return

    if not info.video_streams:
        print("Doesn't contain a video stream -- skipping")
        return

    if info.kbitrate <= options.kbitrate and src.endswith('.webm'):
        print("File is already in WEBM format with correct bitrate! Copying...")
        shutil.copyfile(src, tmpfn)
        os.rename(tmpfn, dst) # atomic
        return

    audio_kbitrate = 100.0 # estimate only, it's really Vorbis VBR
    video_kbitrate = options.kbitrate - audio_kbitrate
    video_kbitrate = max(50, min(info.kbitrate - audio_kbitrate, video_kbitrate))

    if video_kbitrate < 0:
        raise RuntimeError("Bitrate is too small, needs to be > 128")

    map_option = []
    subtitle_streams = None
    if options.language_select:
        languages = [x.strip() for x in options.language_select.split(',')]

        def language_sort(stream):
            if stream.language in languages:
                if stream.codec == 'dvdsub':
                    return languages.index(stream.language), 0
                else:
                    return languages.index(stream.language), 1
            else:
                return len(languages), 1

        video_streams = list(sorted(info.video_streams, key=language_sort))
        audio_streams = list(sorted(info.audio_streams, key=language_sort))
        subtitle_streams = list(sorted(info.subtitle_streams, key=language_sort))

        if video_streams:
            map_option.extend(['-map', '0:' + video_streams[0].key])
        if audio_streams:
            map_option.extend(['-map', '0:' + audio_streams[0].key])


    num_threads = max(2, multiprocessing.cpu_count()//options.jobs) - 1

    codec_args = ['-filter:v', 'hqdn3d',
                  '-c:a', 'libvorbis',
                  '-qscale:a', '3',
                  '-c:v', 'libvpx',
                  '-crf', '14',
                  '-threads', str(num_threads),
                  '-b:v', '%dk' % (int(video_kbitrate),),
                  ]

    if options.fast:
        codec_args += ['-deadline', 'good', '-cpu-used', '5']

    cmd = (['ffmpeg',
            '-y',
            '-i', src]
           + map_option
           + codec_args
           )

    if options.language_select and subtitle_streams:
        for stream in subtitle_streams:
            if stream.codec in ('subrip', 'unknown'):
                # Guess: srt
                subfile = os.path.join(tmpdir, 'sub.srt')
                run(['mkvextract', 'tracks', src,
                     stream.key + ':' + subfile],
                    echo=True)
                cmd[0] = 'ffmpeg'
                cmd += ['-vf', 'subtitles=' + subfile]
                break
            else:
                print("Unknown subtitle format")
                continue

    tmp_outfn = os.path.join(tmpdir, 'out.webm')
    try:
        run(cmd + [tmp_outfn], echo=True)

        # Need to convert to webm using mkvmerge --- ffmpeg can produce
        # malformed containers
        run(['mkvmerge', '-o', tmpfn, tmp_outfn], echo=True)
    except CommandError:
        print("Conversion failed -- skipping file.")
        return

    os.rename(tmpfn, dst)

    print("\nDone!\n")


class VideoFileError(RuntimeError):
    pass


class VideoFileInfo(object):
    def __init__(self, filename):
        self.filename = filename

        self.duration = None
        self.kbitrate = None

        self.video_streams = []
        self.audio_streams = []
        self.subtitle_streams = []

        self._get_info(filename)

        if not self.kbitrate and self.duration:
            self.kbitrate = (os.path.getsize(filename) * 8
                             / (1000 * self.duration.total_seconds()))

    def _get_info(self, filename):
        try:
            out, err = run_get(['ffprobe', '-of', 'json', '-show_format', '-show_streams',
                                filename])
        except CommandError as err:
            raise VideoFileError(str(err))

        try:
            data = json.loads(out.decode('utf-8'))
        except UnicodeDecodeError:
            data = json.loads(out.decode('latin-1'))

        try:
            self.duration = datetime.timedelta(seconds=float(data['format']['duration']))
        except (ValueError, KeyError):
            pass

        try:
            self.kbitrate = float(data['format']['bit_rate']) / 1000.
        except (ValueError, KeyError):
            pass

        for d in data['streams']:
            tags = d.get('tags', {})
            if d['codec_type'] == 'video':
                stream = VideoStream(key=str(d['index']),
                                     codec=d['codec_name'],
                                     language=get_iso_639_2_code(tags.get('language', None)
                                                                 or tags.get('LANGUAGE', None)))
                self.video_streams.append(stream)
            elif d['codec_type'] == 'audio':
                stream = AudioStream(key=str(d['index']),
                                     codec=d['codec_name'],
                                     language=get_iso_639_2_code(tags.get('language', None)
                                                                 or tags.get('LANGUAGE', None)))
                self.audio_streams.append(stream)
            elif d['codec_type'] == 'subtitle':
                stream = SubtitleStream(key=str(d['index']),
                                        codec=d['codec_name'],
                                        language=get_iso_639_2_code(tags.get('language', None)
                                                                    or tags.get('LANGUAGE', None)))
                self.subtitle_streams.append(stream)

    def __repr__(self):
        rest = [repr(os.path.basename(self.filename))]
        for k in ['duration', 'kbitrate', 'video_streams', 'audio_streams', 'subtitle_streams']:
            s = getattr(self, k)
            if s:
                if k == 'duration':
                    s = '%d sec' % (s.total_seconds(),)
                rest.append("%s=%r" % (k, s))
        return "StreamInfo(%s)" % (", ".join(rest),)


class StreamInfo(object):
    def __init__(self, key, codec, language=None):
        self.key = key
        self.codec = codec
        if language == 'und':
            language = None
        self.language = language

    def __repr__(self):
        rest = [repr(self.key)]
        for k in ['codec', 'language']:
            if hasattr(self, k) and getattr(self, k):
                rest.append("%s=%r" % (k, getattr(self, k)))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(rest),)


class VideoStream(StreamInfo):
    stream_type = 'video'


class AudioStream(StreamInfo):
    stream_type = 'audio'


class SubtitleStream(StreamInfo):
    stream_type = 'subtitle'


class CommandError(RuntimeError):
    pass


def run(cmd, returncode=0, echo=False, **kw):
    if echo:
        print("$ " + shell_to_str(cmd))
    ret = subprocess.call(cmd, **kw)
    if ret != returncode:
        raise CommandError("Running %s failed" % (shell_to_str(cmd),))


def run_get(cmd, returncode=0, echo=False, **kw):
    if echo:
        print("$ " + shell_to_str(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         **kw)
    out, err = p.communicate()
    if p.returncode != returncode:
        raise CommandError("Running %s failed:\n%s\n%s" % (shell_to_str(cmd),
                                                           out,
                                                           err))
    return out, err


def shell_to_str(cmd):
    parts = ["\"%s\"" % x.replace("\"", "\\\"") if ' ' in x else x
             for x in cmd]
    return " ".join(parts)


#------------------------------------------------------------------------------
# ISO 639-2 language codes
#------------------------------------------------------------------------------

ISO_639_2_MAP = {}

def get_iso_639_2_code(s):
    """
    Convert a semi-free form language string to ISO 639 language code.
    If undetermined, return None.
    """
    try:
        s = ISO_639_2_MAP[s.lower()]
        if s == 'und':
            s = None
        return s
    except AttributeError:
        return None

ISO_639_2_RAW = u"""\
aar||aa|Afar|afar
abk||ab|Abkhazian|abkhaze
ace|||Achinese|aceh
ach|||Acoli|acoli
ada|||Adangme|adangme
ady|||Adyghe; Adygei|adyghé
afa|||Afro-Asiatic languages|afro-asiatiques, langues
afh|||Afrihili|afrihili
afr||af|Afrikaans|afrikaans
ain|||Ainu|aïnou
aka||ak|Akan|akan
akk|||Akkadian|akkadien
alb|sqi|sq|Albanian|albanais
ale|||Aleut|aléoute
alg|||Algonquian languages|algonquines, langues
alt|||Southern Altai|altai du Sud
amh||am|Amharic|amharique
ang|||English, Old (ca.450-1100)|anglo-saxon (ca.450-1100)
anp|||Angika|angika
apa|||Apache languages|apaches, langues
ara||ar|Arabic|arabe
arc|||Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE)|araméen d'empire (700-300 BCE)
arg||an|Aragonese|aragonais
arm|hye|hy|Armenian|arménien
arn|||Mapudungun; Mapuche|mapudungun; mapuche; mapuce
arp|||Arapaho|arapaho
art|||Artificial languages|artificielles, langues
arw|||Arawak|arawak
asm||as|Assamese|assamais
ast|||Asturian; Bable; Leonese; Asturleonese|asturien; bable; léonais; asturoléonais
ath|||Athapascan languages|athapascanes, langues
aus|||Australian languages|australiennes, langues
ava||av|Avaric|avar
ave||ae|Avestan|avestique
awa|||Awadhi|awadhi
aym||ay|Aymara|aymara
aze||az|Azerbaijani|azéri
bad|||Banda languages|banda, langues
bai|||Bamileke languages|bamiléké, langues
bak||ba|Bashkir|bachkir
bal|||Baluchi|baloutchi
bam||bm|Bambara|bambara
ban|||Balinese|balinais
baq|eus|eu|Basque|basque
bas|||Basa|basa
bat|||Baltic languages|baltes, langues
bej|||Beja; Bedawiyet|bedja
bel||be|Belarusian|biélorusse
bem|||Bemba|bemba
ben||bn|Bengali|bengali
ber|||Berber languages|berbères, langues
bho|||Bhojpuri|bhojpuri
bih||bh|Bihari languages|langues biharis
bik|||Bikol|bikol
bin|||Bini; Edo|bini; edo
bis||bi|Bislama|bichlamar
bla|||Siksika|blackfoot
bnt|||Bantu (Other)|bantoues, autres langues
bos||bs|Bosnian|bosniaque
bra|||Braj|braj
bre||br|Breton|breton
btk|||Batak languages|batak, langues
bua|||Buriat|bouriate
bug|||Buginese|bugi
bul||bg|Bulgarian|bulgare
bur|mya|my|Burmese|birman
byn|||Blin; Bilin|blin; bilen
cad|||Caddo|caddo
cai|||Central American Indian languages|amérindiennes de L'Amérique centrale, langues
car|||Galibi Carib|karib; galibi; carib
cat||ca|Catalan; Valencian|catalan; valencien
cau|||Caucasian languages|caucasiennes, langues
ceb|||Cebuano|cebuano
cel|||Celtic languages|celtiques, langues; celtes, langues
cha||ch|Chamorro|chamorro
chb|||Chibcha|chibcha
che||ce|Chechen|tchétchène
chg|||Chagatai|djaghataï
chi|zho|zh|Chinese|chinois
chk|||Chuukese|chuuk
chm|||Mari|mari
chn|||Chinook jargon|chinook, jargon
cho|||Choctaw|choctaw
chp|||Chipewyan; Dene Suline|chipewyan
chr|||Cherokee|cherokee
chu||cu|Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic|slavon d'église; vieux slave; slavon liturgique; vieux bulgare
chv||cv|Chuvash|tchouvache
chy|||Cheyenne|cheyenne
cmc|||Chamic languages|chames, langues
cop|||Coptic|copte
cor||kw|Cornish|cornique
cos||co|Corsican|corse
cpe|||Creoles and pidgins, English based|créoles et pidgins basés sur l'anglais
cpf|||Creoles and pidgins, French-based |créoles et pidgins basés sur le français
cpp|||Creoles and pidgins, Portuguese-based |créoles et pidgins basés sur le portugais
cre||cr|Cree|cree
crh|||Crimean Tatar; Crimean Turkish|tatar de Crimé
crp|||Creoles and pidgins |créoles et pidgins
csb|||Kashubian|kachoube
cus|||Cushitic languages|couchitiques, langues
cze|ces|cs|Czech|tchèque
dak|||Dakota|dakota
dan||da|Danish|danois
dar|||Dargwa|dargwa
day|||Land Dayak languages|dayak, langues
del|||Delaware|delaware
den|||Slave (Athapascan)|esclave (athapascan)
dgr|||Dogrib|dogrib
din|||Dinka|dinka
div||dv|Divehi; Dhivehi; Maldivian|maldivien
doi|||Dogri|dogri
dra|||Dravidian languages|dravidiennes, langues
dsb|||Lower Sorbian|bas-sorabe
dua|||Duala|douala
dum|||Dutch, Middle (ca.1050-1350)|néerlandais moyen (ca. 1050-1350)
dut|nld|nl|Dutch; Flemish|néerlandais; flamand
dyu|||Dyula|dioula
dzo||dz|Dzongkha|dzongkha
efi|||Efik|efik
egy|||Egyptian (Ancient)|égyptien
eka|||Ekajuk|ekajuk
elx|||Elamite|élamite
eng||en|English|anglais
enm|||English, Middle (1100-1500)|anglais moyen (1100-1500)
epo||eo|Esperanto|espéranto
est||et|Estonian|estonien
ewe||ee|Ewe|éwé
ewo|||Ewondo|éwondo
fan|||Fang|fang
fao||fo|Faroese|féroïen
fat|||Fanti|fanti
fij||fj|Fijian|fidjien
fil|||Filipino; Pilipino|filipino; pilipino
fin||fi|Finnish|finnois
fiu|||Finno-Ugrian languages|finno-ougriennes, langues
fon|||Fon|fon
fre|fra|fr|French|français
frm|||French, Middle (ca.1400-1600)|français moyen (1400-1600)
fro|||French, Old (842-ca.1400)|français ancien (842-ca.1400)
frr|||Northern Frisian|frison septentrional
frs|||Eastern Frisian|frison oriental
fry||fy|Western Frisian|frison occidental
ful||ff|Fulah|peul
fur|||Friulian|frioulan
gaa|||Ga|ga
gay|||Gayo|gayo
gba|||Gbaya|gbaya
gem|||Germanic languages|germaniques, langues
geo|kat|ka|Georgian|géorgien
ger|deu|de|German|allemand
gez|||Geez|guèze
gil|||Gilbertese|kiribati
gla||gd|Gaelic; Scottish Gaelic|gaélique; gaélique écossais
gle||ga|Irish|irlandais
glg||gl|Galician|galicien
glv||gv|Manx|manx; mannois
gmh|||German, Middle High (ca.1050-1500)|allemand, moyen haut (ca. 1050-1500)
goh|||German, Old High (ca.750-1050)|allemand, vieux haut (ca. 750-1050)
gon|||Gondi|gond
gor|||Gorontalo|gorontalo
got|||Gothic|gothique
grb|||Grebo|grebo
grc|||Greek, Ancient (to 1453)|grec ancien (jusqu'à 1453)
gre|ell|el|Greek, Modern (1453-)|grec moderne (après 1453)
grn||gn|Guarani|guarani
gsw|||Swiss German; Alemannic; Alsatian|suisse alémanique; alémanique; alsacien
guj||gu|Gujarati|goudjrati
gwi|||Gwich'in|gwich'in
hai|||Haida|haida
hat||ht|Haitian; Haitian Creole|haïtien; créole haïtien
hau||ha|Hausa|haoussa
haw|||Hawaiian|hawaïen
heb||he|Hebrew|hébreu
her||hz|Herero|herero
hil|||Hiligaynon|hiligaynon
him|||Himachali languages; Western Pahari languages|langues himachalis; langues paharis occidentales
hin||hi|Hindi|hindi
hit|||Hittite|hittite
hmn|||Hmong; Mong|hmong
hmo||ho|Hiri Motu|hiri motu
hrv||hr|Croatian|croate
hsb|||Upper Sorbian|haut-sorabe
hun||hu|Hungarian|hongrois
hup|||Hupa|hupa
iba|||Iban|iban
ibo||ig|Igbo|igbo
ice|isl|is|Icelandic|islandais
ido||io|Ido|ido
iii||ii|Sichuan Yi; Nuosu|yi de Sichuan
ijo|||Ijo languages|ijo, langues
iku||iu|Inuktitut|inuktitut
ile||ie|Interlingue; Occidental|interlingue
ilo|||Iloko|ilocano
ina||ia|Interlingua (International Auxiliary Language Association)|interlingua (langue auxiliaire internationale)
inc|||Indic languages|indo-aryennes, langues
ind||id|Indonesian|indonésien
ine|||Indo-European languages|indo-européennes, langues
inh|||Ingush|ingouche
ipk||ik|Inupiaq|inupiaq
ira|||Iranian languages|iraniennes, langues
iro|||Iroquoian languages|iroquoises, langues
ita||it|Italian|italien
jav||jv|Javanese|javanais
jbo|||Lojban|lojban
jpn||ja|Japanese|japonais
jpr|||Judeo-Persian|judéo-persan
jrb|||Judeo-Arabic|judéo-arabe
kaa|||Kara-Kalpak|karakalpak
kab|||Kabyle|kabyle
kac|||Kachin; Jingpho|kachin; jingpho
kal||kl|Kalaallisut; Greenlandic|groenlandais
kam|||Kamba|kamba
kan||kn|Kannada|kannada
kar|||Karen languages|karen, langues
kas||ks|Kashmiri|kashmiri
kau||kr|Kanuri|kanouri
kaw|||Kawi|kawi
kaz||kk|Kazakh|kazakh
kbd|||Kabardian|kabardien
kha|||Khasi|khasi
khi|||Khoisan languages|khoïsan, langues
khm||km|Central Khmer|khmer central
kho|||Khotanese; Sakan|khotanais; sakan
kik||ki|Kikuyu; Gikuyu|kikuyu
kin||rw|Kinyarwanda|rwanda
kir||ky|Kirghiz; Kyrgyz|kirghiz
kmb|||Kimbundu|kimbundu
kok|||Konkani|konkani
kom||kv|Komi|kom
kon||kg|Kongo|kongo
kor||ko|Korean|coréen
kos|||Kosraean|kosrae
kpe|||Kpelle|kpellé
krc|||Karachay-Balkar|karatchai balkar
krl|||Karelian|carélien
kro|||Kru languages|krou, langues
kru|||Kurukh|kurukh
kua||kj|Kuanyama; Kwanyama|kuanyama; kwanyama
kum|||Kumyk|koumyk
kur||ku|Kurdish|kurde
kut|||Kutenai|kutenai
lad|||Ladino|judéo-espagnol
lah|||Lahnda|lahnda
lam|||Lamba|lamba
lao||lo|Lao|lao
lat||la|Latin|latin
lav||lv|Latvian|letton
lez|||Lezghian|lezghien
lim||li|Limburgan; Limburger; Limburgish|limbourgeois
lin||ln|Lingala|lingala
lit||lt|Lithuanian|lituanien
lol|||Mongo|mongo
loz|||Lozi|lozi
ltz||lb|Luxembourgish; Letzeburgesch|luxembourgeois
lua|||Luba-Lulua|luba-lulua
lub||lu|Luba-Katanga|luba-katanga
lug||lg|Ganda|ganda
lui|||Luiseno|luiseno
lun|||Lunda|lunda
luo|||Luo (Kenya and Tanzania)|luo (Kenya et Tanzanie)
lus|||Lushai|lushai
mac|mkd|mk|Macedonian|macédonien
mad|||Madurese|madourais
mag|||Magahi|magahi
mah||mh|Marshallese|marshall
mai|||Maithili|maithili
mak|||Makasar|makassar
mal||ml|Malayalam|malayalam
man|||Mandingo|mandingue
mao|mri|mi|Maori|maori
map|||Austronesian languages|austronésiennes, langues
mar||mr|Marathi|marathe
mas|||Masai|massaï
may|msa|ms|Malay|malais
mdf|||Moksha|moksa
mdr|||Mandar|mandar
men|||Mende|mendé
mga|||Irish, Middle (900-1200)|irlandais moyen (900-1200)
mic|||Mi'kmaq; Micmac|mi'kmaq; micmac
min|||Minangkabau|minangkabau
mis|||Uncoded languages|langues non codées
mkh|||Mon-Khmer languages|môn-khmer, langues
mlg||mg|Malagasy|malgache
mlt||mt|Maltese|maltais
mnc|||Manchu|mandchou
mni|||Manipuri|manipuri
mno|||Manobo languages|manobo, langues
moh|||Mohawk|mohawk
mon||mn|Mongolian|mongol
mos|||Mossi|moré
mul|||Multiple languages|multilingue
mun|||Munda languages|mounda, langues
mus|||Creek|muskogee
mwl|||Mirandese|mirandais
mwr|||Marwari|marvari
myn|||Mayan languages|maya, langues
myv|||Erzya|erza
nah|||Nahuatl languages|nahuatl, langues
nai|||North American Indian languages|nord-amérindiennes, langues
nap|||Neapolitan|napolitain
nau||na|Nauru|nauruan
nav||nv|Navajo; Navaho|navaho
nbl||nr|Ndebele, South; South Ndebele|ndébélé du Sud
nde||nd|Ndebele, North; North Ndebele|ndébélé du Nord
ndo||ng|Ndonga|ndonga
nds|||Low German; Low Saxon; German, Low; Saxon, Low|bas allemand; bas saxon; allemand, bas; saxon, bas
nep||ne|Nepali|népalais
new|||Nepal Bhasa; Newari|nepal bhasa; newari
nia|||Nias|nias
nic|||Niger-Kordofanian languages|nigéro-kordofaniennes, langues
niu|||Niuean|niué
nno||nn|Norwegian Nynorsk; Nynorsk, Norwegian|norvégien nynorsk; nynorsk, norvégien
nob||nb|Bokmål, Norwegian; Norwegian Bokmål|norvégien bokmål
nog|||Nogai|nogaï; nogay
non|||Norse, Old|norrois, vieux
nor||no|Norwegian|norvégien
nqo|||N'Ko|n'ko
nso|||Pedi; Sepedi; Northern Sotho|pedi; sepedi; sotho du Nord
nub|||Nubian languages|nubiennes, langues
nwc|||Classical Newari; Old Newari; Classical Nepal Bhasa|newari classique
nya||ny|Chichewa; Chewa; Nyanja|chichewa; chewa; nyanja
nym|||Nyamwezi|nyamwezi
nyn|||Nyankole|nyankolé
nyo|||Nyoro|nyoro
nzi|||Nzima|nzema
oci||oc|Occitan (post 1500); Provençal|occitan (après 1500); provençal
oji||oj|Ojibwa|ojibwa
ori||or|Oriya|oriya
orm||om|Oromo|galla
osa|||Osage|osage
oss||os|Ossetian; Ossetic|ossète
ota|||Turkish, Ottoman (1500-1928)|turc ottoman (1500-1928)
oto|||Otomian languages|otomi, langues
paa|||Papuan languages|papoues, langues
pag|||Pangasinan|pangasinan
pal|||Pahlavi|pahlavi
pam|||Pampanga; Kapampangan|pampangan
pan||pa|Panjabi; Punjabi|pendjabi
pap|||Papiamento|papiamento
pau|||Palauan|palau
peo|||Persian, Old (ca.600-400 B.C.)|perse, vieux (ca. 600-400 av. J.-C.)
per|fas|fa|Persian|persan
phi|||Philippine languages|philippines, langues
phn|||Phoenician|phénicien
pli||pi|Pali|pali
pol||pl|Polish|polonais
pon|||Pohnpeian|pohnpei
por||pt|Portuguese|portugais
pra|||Prakrit languages|prâkrit, langues
pro|||Provençal, Old (to 1500)|provençal ancien (jusqu'à 1500)
pus||ps|Pushto; Pashto|pachto
qaa-qtz|||Reserved for local use|réservée à l'usage local
que||qu|Quechua|quechua
raj|||Rajasthani|rajasthani
rap|||Rapanui|rapanui
rar|||Rarotongan; Cook Islands Maori|rarotonga; maori des îles Cook
roa|||Romance languages|romanes, langues
roh||rm|Romansh|romanche
rom|||Romany|tsigane
rum|ron|ro|Romanian; Moldavian; Moldovan|roumain; moldave
run||rn|Rundi|rundi
rup|||Aromanian; Arumanian; Macedo-Romanian|aroumain; macédo-roumain
rus||ru|Russian|russe
sad|||Sandawe|sandawe
sag||sg|Sango|sango
sah|||Yakut|iakoute
sai|||South American Indian (Other)|indiennes d'Amérique du Sud, autres langues
sal|||Salishan languages|salishennes, langues
sam|||Samaritan Aramaic|samaritain
san||sa|Sanskrit|sanskrit
sas|||Sasak|sasak
sat|||Santali|santal
scn|||Sicilian|sicilien
sco|||Scots|écossais
sel|||Selkup|selkoupe
sem|||Semitic languages|sémitiques, langues
sga|||Irish, Old (to 900)|irlandais ancien (jusqu'à 900)
sgn|||Sign Languages|langues des signes
shn|||Shan|chan
sid|||Sidamo|sidamo
sin||si|Sinhala; Sinhalese|singhalais
sio|||Siouan languages|sioux, langues
sit|||Sino-Tibetan languages|sino-tibétaines, langues
sla|||Slavic languages|slaves, langues
slo|slk|sk|Slovak|slovaque
slv||sl|Slovenian|slovène
sma|||Southern Sami|sami du Sud
sme||se|Northern Sami|sami du Nord
smi|||Sami languages|sames, langues
smj|||Lule Sami|sami de Lule
smn|||Inari Sami|sami d'Inari
smo||sm|Samoan|samoan
sms|||Skolt Sami|sami skolt
sna||sn|Shona|shona
snd||sd|Sindhi|sindhi
snk|||Soninke|soninké
sog|||Sogdian|sogdien
som||so|Somali|somali
son|||Songhai languages|songhai, langues
sot||st|Sotho, Southern|sotho du Sud
spa||es|Spanish; Castilian|espagnol; castillan
srd||sc|Sardinian|sarde
srn|||Sranan Tongo|sranan tongo
srp||sr|Serbian|serbe
srr|||Serer|sérère
ssa|||Nilo-Saharan languages|nilo-sahariennes, langues
ssw||ss|Swati|swati
suk|||Sukuma|sukuma
sun||su|Sundanese|soundanais
sus|||Susu|soussou
sux|||Sumerian|sumérien
swa||sw|Swahili|swahili
swe||sv|Swedish|suédois
syc|||Classical Syriac|syriaque classique
syr|||Syriac|syriaque
tah||ty|Tahitian|tahitien
tai|||Tai languages|tai, langues
tam||ta|Tamil|tamoul
tat||tt|Tatar|tatar
tel||te|Telugu|télougou
tem|||Timne|temne
ter|||Tereno|tereno
tet|||Tetum|tetum
tgk||tg|Tajik|tadjik
tgl||tl|Tagalog|tagalog
tha||th|Thai|thaï
tib|bod|bo|Tibetan|tibétain
tig|||Tigre|tigré
tir||ti|Tigrinya|tigrigna
tiv|||Tiv|tiv
tkl|||Tokelau|tokelau
tlh|||Klingon; tlhIngan-Hol|klingon
tli|||Tlingit|tlingit
tmh|||Tamashek|tamacheq
tog|||Tonga (Nyasa)|tonga (Nyasa)
ton||to|Tonga (Tonga Islands)|tongan (Îles Tonga)
tpi|||Tok Pisin|tok pisin
tsi|||Tsimshian|tsimshian
tsn||tn|Tswana|tswana
tso||ts|Tsonga|tsonga
tuk||tk|Turkmen|turkmène
tum|||Tumbuka|tumbuka
tup|||Tupi languages|tupi, langues
tur||tr|Turkish|turc
tut|||Altaic languages|altaïques, langues
tvl|||Tuvalu|tuvalu
twi||tw|Twi|twi
tyv|||Tuvinian|touva
udm|||Udmurt|oudmourte
uga|||Ugaritic|ougaritique
uig||ug|Uighur; Uyghur|ouïgour
ukr||uk|Ukrainian|ukrainien
umb|||Umbundu|umbundu
und|||Undetermined|indéterminée
urd||ur|Urdu|ourdou
uzb||uz|Uzbek|ouszbek
vai|||Vai|vaï
ven||ve|Venda|venda
vie||vi|Vietnamese|vietnamien
vol||vo|Volapük|volapük
vot|||Votic|vote
wak|||Wakashan languages|wakashanes, langues
wal|||Walamo|walamo
war|||Waray|waray
was|||Washo|washo
wel|cym|cy|Welsh|gallois
wen|||Sorbian languages|sorabes, langues
wln||wa|Walloon|wallon
wol||wo|Wolof|wolof
xal|||Kalmyk; Oirat|kalmouk; oïrat
xho||xh|Xhosa|xhosa
yao|||Yao|yao
yap|||Yapese|yapois
yid||yi|Yiddish|yiddish
yor||yo|Yoruba|yoruba
ypk|||Yupik languages|yupik, langues
zap|||Zapotec|zapotèque
zbl|||Blissymbols; Blissymbolics; Bliss|symboles Bliss; Bliss
zen|||Zenaga|zenaga
zgh|||Standard Moroccan Tamazight|amazighe standard marocain
zha||za|Zhuang; Chuang|zhuang; chuang
znd|||Zande languages|zandé, langues
zul||zu|Zulu|zoulou
zun|||Zuni|zuni
zxx|||No linguistic content; Not applicable|pas de contenu linguistique; non applicable
zza|||Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki|zaza; dimili; dimli; kirdki; kirmanjki; zazaki
"""

for line in ISO_639_2_RAW.splitlines():
    parts = [x.strip() for x in re.split(u'[\\|;,]', line) if x.strip()]
    for p in parts:
        ISO_639_2_MAP[p.lower()] = parts[0].lower()

if __name__ == "__main__":
    main()
