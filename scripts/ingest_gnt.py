"""Ingest MorphGNT (SBLGNT) Greek New Testament into BibCrit CSV format.

Prerequisites:
  No Python packages required — uses stdlib only (curl for downloads).

Usage:
  python scripts/ingest_gnt.py --out data/corpora/gnt_opengnt/

Output:
  27 per-book CSVs (matthew.csv … revelation.csv) with schema:
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition

Sources:
  MorphGNT morphological data: CC BY-SA 3.0
    https://github.com/morphgnt/sblgnt
    James Tauber et al., MorphGNT

  SBLGNT text: CC BY 4.0
    Society of Biblical Literature Greek New Testament
    Michael W. Holmes, ed. (2010)
    http://sblgnt.com/license/

MorphGNT line format (space-separated, 7 fields):
  BBCCVV  POS  PARSE  text  word  normalized  lemma
  e.g.: 010101 N- ----NSF- Βίβλος Βίβλος βίβλος βίβλος

Field mapping:
  normalized (col 6) → word_text   (lowercase, accent-normalized, no punctuation)
  lemma      (col 7) → lemma
  POS.PARSE          → morph       (e.g. 'N-.----NSF-' or 'V-.3AAI-S--')
  manuscript         = 'SBLGNT'
  tradition          = 'GNT'
"""

import argparse
import csv
import os
import subprocess

BASE_URL = 'https://raw.githubusercontent.com/morphgnt/sblgnt/master'

# (filename, two-digit book prefix used in BBCCVV references)
MORPHGNT_FILES = [
    ('61-Mt-morphgnt.txt',  '01'),
    ('62-Mk-morphgnt.txt',  '02'),
    ('63-Lk-morphgnt.txt',  '03'),
    ('64-Jn-morphgnt.txt',  '04'),
    ('65-Ac-morphgnt.txt',  '05'),
    ('66-Ro-morphgnt.txt',  '06'),
    ('67-1Co-morphgnt.txt', '07'),
    ('68-2Co-morphgnt.txt', '08'),
    ('69-Ga-morphgnt.txt',  '09'),
    ('70-Eph-morphgnt.txt', '10'),
    ('71-Php-morphgnt.txt', '11'),
    ('72-Col-morphgnt.txt', '12'),
    ('73-1Th-morphgnt.txt', '13'),
    ('74-2Th-morphgnt.txt', '14'),
    ('75-1Ti-morphgnt.txt', '15'),
    ('76-2Ti-morphgnt.txt', '16'),
    ('77-Tit-morphgnt.txt', '17'),
    ('78-Phm-morphgnt.txt', '18'),
    ('79-Heb-morphgnt.txt', '19'),
    ('80-Jas-morphgnt.txt', '20'),
    ('81-1Pe-morphgnt.txt', '21'),
    ('82-2Pe-morphgnt.txt', '22'),
    ('83-1Jn-morphgnt.txt', '23'),
    ('84-2Jn-morphgnt.txt', '24'),
    ('85-3Jn-morphgnt.txt', '25'),
    ('86-Jud-morphgnt.txt', '26'),
    ('87-Re-morphgnt.txt',  '27'),
]

# MorphGNT book prefix → (canonical name, BibCrit book_order)
# NT books start at 40 (continuing from OT's 1–39)
BOOK_MAP = {
    '01': ('Matthew',         40),
    '02': ('Mark',            41),
    '03': ('Luke',            42),
    '04': ('John',            43),
    '05': ('Acts',            44),
    '06': ('Romans',          45),
    '07': ('1 Corinthians',   46),
    '08': ('2 Corinthians',   47),
    '09': ('Galatians',       48),
    '10': ('Ephesians',       49),
    '11': ('Philippians',     50),
    '12': ('Colossians',      51),
    '13': ('1 Thessalonians', 52),
    '14': ('2 Thessalonians', 53),
    '15': ('1 Timothy',       54),
    '16': ('2 Timothy',       55),
    '17': ('Titus',           56),
    '18': ('Philemon',        57),
    '19': ('Hebrews',         58),
    '20': ('James',           59),
    '21': ('1 Peter',         60),
    '22': ('2 Peter',         61),
    '23': ('1 John',          62),
    '24': ('2 John',          63),
    '25': ('3 John',          64),
    '26': ('Jude',            65),
    '27': ('Revelation',      66),
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong', 'manuscript', 'tradition',
]


def download(url: str, cache_dir: str) -> str:
    """Download url to cache_dir if not already cached. Returns local path."""
    filename = url.split('/')[-1]
    local = os.path.join(cache_dir, filename)
    if not os.path.exists(local):
        print(f'  Downloading {filename} …')
        subprocess.run(['curl', '-fsSL', '-o', local, url], check=True)
    return local


def parse_line(line: str) -> dict | None:
    """Parse one MorphGNT line into a dict of fields. Returns None to skip."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    parts = line.split(' ')
    if len(parts) < 7:
        return None

    ref    = parts[0]   # BBCCVV
    pos    = parts[1]   # POS code e.g. 'N-', 'V-', 'RA'
    parse  = parts[2]   # PARSE code e.g. '----NSF-'
    # parts[3] = text (punctuation attached)
    # parts[4] = word (punctuation stripped, original case)
    normalized = parts[5]  # best surface form: lowercase, no punctuation
    lemma      = parts[6]

    bb = ref[0:2]
    cc = int(ref[2:4])
    vv = int(ref[4:6])

    morph = f'{pos}.{parse}'

    return {
        'bb': bb,
        'chapter': cc,
        'verse': vv,
        'word_text': normalized,
        'lemma': lemma,
        'morph': morph,
    }


def ingest(out_dir: str, cache_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    total_words = 0

    for filename, book_prefix in MORPHGNT_FILES:
        book_name, book_order = BOOK_MAP[book_prefix]
        url = f'{BASE_URL}/{filename}'
        local = download(url, cache_dir)

        safe_name = book_name.lower().replace(' ', '_')
        out_path = os.path.join(out_dir, f'{safe_name}.csv')
        book_words = 0
        verse_pos: dict = {}

        with (
            open(local, encoding='utf-8') as src,
            open(out_path, 'w', newline='', encoding='utf-8') as fh,
        ):
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()

            for line in src:
                parsed = parse_line(line)
                if parsed is None:
                    continue

                ch = parsed['chapter']
                vs = parsed['verse']
                reference = f'{book_name} {ch}:{vs}'

                verse_pos[reference] = verse_pos.get(reference, 0) + 1
                pos_in_verse = verse_pos[reference]

                writer.writerow({
                    'book_order': book_order,
                    'book':       book_name,
                    'chapter':    ch,
                    'verse':      vs,
                    'reference':  reference,
                    'position':   pos_in_verse,
                    'word_text':  parsed['word_text'],
                    'lemma':      parsed['lemma'],
                    'morph':      parsed['morph'],
                    'strong':     '',
                    'manuscript': 'SBLGNT',
                    'tradition':  'GNT',
                })
                book_words += 1

        print(f'  {book_name}: {book_words} words → {out_path}')
        total_words += book_words

    print(f'GNT ingestion complete: {total_words} words total')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Ingest MorphGNT SBLGNT into BibCrit CSV format'
    )
    parser.add_argument('--out',   default='data/corpora/gnt_opengnt/',
                        help='Output directory for CSV files')
    parser.add_argument('--cache', default='/tmp/morphgnt_cache/',
                        help='Directory to cache downloaded MorphGNT files')
    args = parser.parse_args()
    ingest(args.out, args.cache)
