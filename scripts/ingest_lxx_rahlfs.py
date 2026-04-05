"""Ingest eliranwong/LXX-Rahlfs-1935 into BibCrit word-level CSV format.

Source: https://github.com/eliranwong/LXX-Rahlfs-1935
License: CC BY-NC-SA 4.0

The repo stores the full LXX as parallel column files keyed by word_id (1-623685):
  text_accented.csv   word_id TAB greek_word
  E-verse.csv         word_start TAB word_end TAB verse_ref  (「Gen 1:1」)
  patched_623685.csv  word_id TAB morphology_code
  final_Strongs.csv   word_id TAB strong_number
  OSSP_lexemes.csv    word_id TAB lemma  (if available)

Usage:
  python scripts/ingest_lxx_rahlfs.py --out data/corpora/lxx_stepbible/

Output:
  One CSV per book with schema:
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition
"""

import argparse
import csv
import os
import subprocess

BASE_URL = 'https://raw.githubusercontent.com/eliranwong/LXX-Rahlfs-1935/master'

FILES = {
    'text':   f'{BASE_URL}/01_wordlist_unicode/text_accented.csv',
    'verse':  f'{BASE_URL}/01_wordlist_unicode/alignment_with_OSSP/E-verse.csv',
    'morph':  f'{BASE_URL}/03a_morphology_with_JTauber_patches/patched_623685.csv',
    'strong': f'{BASE_URL}/07_StrongNumber/final_Strongs.csv',
    'lemma':  f'{BASE_URL}/02_lexemes/OSSP_lexemes.csv',
}

# Map all LXX abbreviations → (canonical book name, book_order) or None (skip).
# None entries are kept so verse ranges are computed correctly but not written.
# LXX uses different abbreviations and ordering from MT.
BOOK_MAP = {
    'Gen':    ('Genesis', 1),       'Exod':   ('Exodus', 2),
    'Lev':    ('Leviticus', 3),     'Num':    ('Numbers', 4),
    'Deut':   ('Deuteronomy', 5),
    'JoshA':  ('Joshua', 6),        'JoshB':  None,   # use A recension only
    'JudgA':  ('Judges', 7),        'JudgB':  None,   # use A recension only
    'Ruth':   ('Ruth', 8),
    '1Sam/K': ('1 Samuel', 9),      '2Sam/K': ('2 Samuel', 10),
    '1/3Kgs': ('1 Kings', 11),      '2/4Kgs': ('2 Kings', 12),
    '1Chr':   ('1 Chronicles', 13), '2Chr':   ('2 Chronicles', 14),
    '1Esdr':  None,                 # Greek Esdras A (deuterocanonical)
    '2Esdr':  ('Ezra', 15),         # Greek Esdras B = Hebrew Ezra+Neh
    'Esth':   ('Esther', 17),       'Job':    ('Job', 18),
    'Ps':     ('Psalms', 19),       'Prov':   ('Proverbs', 20),
    'Qoh':    ('Ecclesiastes', 21), 'Cant':   ('Song of Songs', 22),
    'Isa':    ('Isaiah', 23),       'Jer':    ('Jeremiah', 24),
    'Lam':    ('Lamentations', 25), 'Ezek':   ('Ezekiel', 26),
    'Dan':    None,                 # Old Greek Daniel (differs significantly)
    'DanTh':  ('Daniel', 27),       # Theodotion Daniel (standard LXX)
    'Sus':    None,  'SusTh': None, # Susanna additions
    'Bel':    None,  'BelTh': None, # Bel additions
    'Hos':    ('Hosea', 28),        'Joel':   ('Joel', 29),
    'Amos':   ('Amos', 30),         'Obad':   ('Obadiah', 31),
    'Jonah':  ('Jonah', 32),        'Mic':    ('Micah', 33),
    'Nah':    ('Nahum', 34),        'Hab':    ('Habakkuk', 35),
    'Zeph':   ('Zephaniah', 36),    'Hag':    ('Haggai', 37),
    'Zech':   ('Zechariah', 38),    'Mal':    ('Malachi', 39),
    # Deuterocanonical — skip
    '1Mac': None, '2Mac': None, '3Mac': None, '4Mac': None,
    'Jdt': None, 'TobBA': None, 'TobS': None,
    'Bar': None, 'EpJer': None, 'Wis': None, 'Sir': None,
    'PsSol': None, 'Od': None,
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong', 'manuscript', 'tradition',
]


def download(url: str, cache_dir: str) -> str:
    """Download a file to cache_dir using curl and return the local path."""
    filename = url.rsplit('/', 1)[-1]
    local = os.path.join(cache_dir, filename)
    if os.path.exists(local):
        print(f'  Using cached {filename}')
        return local
    print(f'  Downloading {filename} ...')
    subprocess.run(['curl', '-fsSL', '-o', local, url], check=True)
    print(f'  Done ({os.path.getsize(local) // 1024} KB)')
    return local


def _lxx_psalm_ch_vs_to_mt(lxx_ch: int, lxx_vs: int) -> tuple:
    """Map LXX/Greek Psalm (ch, vs) to MT/Hebrew numbering.

    LXX Psalms differ from MT in chapter numbering:
      LXX  1–8   → MT  1–8   (identical)
      LXX  9     → MT  9:1-21 / MT 10:1-18  (merged in LXX)
      LXX 10–112 → MT 11–113 (+1)
      LXX 113    → MT 114:1-8 / MT 115:1-18 (merged in LXX)
      LXX 114    → MT 116:1-9
      LXX 115    → MT 116:10-19
      LXX 116–145→ MT 117–146 (+1)
      LXX 146    → MT 147:1-11
      LXX 147    → MT 147:12-20
      LXX 148–151→ MT 148–150 (identical; 151 is extra LXX psalm)
    """
    if lxx_ch <= 8:
        return (lxx_ch, lxx_vs)
    elif lxx_ch == 9:
        # LXX 9 has 39 verses: 1-21 = MT 9, 22-39 = MT 10
        if lxx_vs <= 21:
            return (9, lxx_vs)
        else:
            return (10, lxx_vs - 21)
    elif 10 <= lxx_ch <= 112:
        return (lxx_ch + 1, lxx_vs)
    elif lxx_ch == 113:
        # LXX 113 has 26 verses: 1-8 = MT 114, 9-26 = MT 115
        if lxx_vs <= 8:
            return (114, lxx_vs)
        else:
            return (115, lxx_vs - 8)
    elif lxx_ch == 114:
        return (116, lxx_vs)           # MT 116:1-9
    elif lxx_ch == 115:
        return (116, lxx_vs + 9)       # MT 116:10-19
    elif 116 <= lxx_ch <= 145:
        return (lxx_ch + 1, lxx_vs)
    elif lxx_ch == 146:
        return (147, lxx_vs)           # MT 147:1-11
    elif lxx_ch == 147:
        return (147, lxx_vs + 11)      # MT 147:12-20
    else:
        return (lxx_ch, lxx_vs)        # 148-151 unchanged


def parse_verse_ref(raw: str):
    """Parse 「Gen 1:1」 → (book_name_or_None, book_order, ch, vs, ref) or None.

    Returns a tuple even for skipped books (where book_name is None) so that
    verse ranges are computed correctly across all LXX books including
    deuterocanonical ones.  Callers must check result[0] before writing.
    """
    raw = raw.strip().strip('「」').strip()
    # Format: "Gen 1:1" — split on space and colon
    parts = raw.replace(':', ' ').split()
    if len(parts) < 3:
        return None
    abbrev = parts[0]
    if abbrev not in BOOK_MAP:
        return None  # truly unknown — skip entirely
    canonical = BOOK_MAP[abbrev]
    try:
        ch = int(parts[1])
        vs = int(parts[2])
    except (ValueError, IndexError):
        return None
    if canonical is None:
        return (None, None, ch, vs, None)  # known but skipped book
    book_name, book_order = canonical
    # Remap LXX Psalm numbers to MT/Hebrew numbering
    if book_name == 'Psalms':
        ch, vs = _lxx_psalm_ch_vs_to_mt(ch, vs)
    return (book_name, book_order, ch, vs, f'{book_name} {ch}:{vs}')


def ingest(out_dir: str, cache_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    # Download all source files
    paths = {k: download(v, cache_dir) for k, v in FILES.items()}

    print('Loading word text...')
    word_text = {}  # word_id → greek_word
    with open(paths['text'], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Format: word_id TAB word_id TAB greek_word  (first two cols identical)
            parts = line.split('\t')
            if len(parts) >= 3:
                try:
                    word_text[int(parts[0])] = parts[2]
                except ValueError:
                    pass

    print('Loading morphology...')
    word_morph = {}  # word_id → morph_code
    with open(paths['morph'], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t', 1)
            if len(parts) == 2:
                try:
                    word_morph[int(parts[0])] = parts[1]
                except ValueError:
                    pass

    print('Loading Strong\'s numbers...')
    word_strong = {}  # word_id → strong
    with open(paths['strong'], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t', 1)
            if len(parts) == 2:
                try:
                    word_strong[int(parts[0])] = parts[1]
                except ValueError:
                    pass

    print('Loading lemmas...')
    word_lemma = {}  # word_id → lemma
    with open(paths['lemma'], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t', 1)
            if len(parts) == 2:
                try:
                    word_lemma[int(parts[0])] = parts[1]
                except ValueError:
                    pass

    print('Building verse ranges...')
    # E-verse.csv format: first_word_id TAB first_word_id TAB 「Book Ch:Vs」
    # Both columns are identical — each row marks the START word of a verse.
    # Verse N spans words [row_N.word_id, row_{N+1}.word_id - 1].
    verse_starts = []  # list of (word_id, parsed_ref)
    with open(paths['verse'], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            try:
                start = int(parts[0])
            except ValueError:
                continue
            parsed = parse_verse_ref(parts[2])
            if parsed:
                verse_starts.append((start, parsed))

    verse_starts.sort(key=lambda x: x[0])
    max_word_id = max(word_text.keys()) if word_text else 0

    # Build ranges: verse N spans [start_N, start_{N+1} - 1]
    verse_ranges = []
    for i, (start, parsed) in enumerate(verse_starts):
        end = verse_starts[i + 1][0] - 1 if i + 1 < len(verse_starts) else max_word_id
        verse_ranges.append((start, end, parsed))

    print(f'  {len(verse_ranges)} verses found')

    print('Writing per-book CSV files...')
    # Build a mapping: word_id → parsed tuple (only for non-skipped books)
    word_verse = {}
    for (start, end, parsed) in verse_ranges:
        if parsed[0] is None:  # skipped book (deuterocanonical, B recension, etc.)
            continue
        for wid in range(start, end + 1):
            word_verse[wid] = parsed

    # Group by book
    books: dict = {}  # book_name → list of (wid, position_in_verse, parsed)
    verse_pos: dict = {}  # ref → running word position
    for wid in sorted(word_verse.keys()):
        parsed = word_verse[wid]
        book_name = parsed[0]
        ref = parsed[4]
        verse_pos[ref] = verse_pos.get(ref, 0) + 1
        pos = verse_pos[ref]
        if book_name not in books:
            books[book_name] = []
        books[book_name].append((wid, pos, parsed))

    for book_name, entries in books.items():
        safe = book_name.lower().replace(' ', '_')
        out_path = os.path.join(out_dir, f'{safe}.csv')
        print(f'  Writing {out_path} ({len(entries)} words)')
        with open(out_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()
            for (wid, pos, parsed) in entries:
                book_name_out, book_order, ch, vs, ref = parsed
                greek = word_text.get(wid, '')
                if not greek.strip():
                    continue
                writer.writerow({
                    'book_order': book_order,
                    'book': book_name_out,
                    'chapter': ch,
                    'verse': vs,
                    'reference': ref,
                    'position': pos,
                    'word_text': greek,
                    'lemma': word_lemma.get(wid, ''),
                    'morph': word_morph.get(wid, ''),
                    'strong': word_strong.get(wid, ''),
                    'manuscript': 'Rahlfs',
                    'tradition': 'LXX',
                })

    print(f'LXX ingestion complete. {len(books)} books written.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest eliranwong LXX-Rahlfs-1935 into BibCrit CSV format')
    parser.add_argument('--out', default='data/corpora/lxx_stepbible/', help='Output directory')
    parser.add_argument('--cache', default='/tmp/lxx_rahlfs_cache/', help='Cache dir for downloaded source files')
    args = parser.parse_args()
    ingest(args.out, args.cache)
