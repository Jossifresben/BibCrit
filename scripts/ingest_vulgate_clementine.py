#!/usr/bin/env python3
"""Download Clementine Vulgate from scrollmapper/bible_databases and split into per-book CSVs.

Usage:
    python scripts/ingest_vulgate_clementine.py --out data/corpora/vul_clementine/

Writes one CSV per book, e.g. genesis.csv, matthew.csv.
Schema: book_order,book,chapter,verse,reference,position,word_text,lemma,morph,strong,manuscript,tradition
"""

import argparse
import csv
import io
import os
import sys
import ssl
import urllib.request

VUL_CSV_URL = (
    'https://raw.githubusercontent.com/scrollmapper/'
    'bible_databases/master/formats/csv/VulgClementine.csv'
)

# Book mapping: scrollmapper book name → (canonical_name, our_book_order)
# Deuterocanonicals are skipped (not in our MT/LXX reference set)
BOOK_MAP = {
    'Genesis':            ('Genesis',         1),
    'Exodus':             ('Exodus',          2),
    'Leviticus':          ('Leviticus',       3),
    'Numbers':            ('Numbers',         4),
    'Deuteronomy':        ('Deuteronomy',     5),
    'Joshua':             ('Joshua',          6),
    'Judges':             ('Judges',          7),
    'Ruth':               ('Ruth',            8),
    'I Samuel':           ('1 Samuel',        9),
    'II Samuel':          ('2 Samuel',       10),
    'I Kings':            ('1 Kings',        11),
    'II Kings':           ('2 Kings',        12),
    'I Chronicles':       ('1 Chronicles',   13),
    'II Chronicles':      ('2 Chronicles',   14),
    'Ezra':               ('Ezra',           15),
    'Nehemiah':           ('Nehemiah',       16),
    'Esther':             ('Esther',         17),
    'Job':                ('Job',            18),
    'Psalms':             ('Psalms',         19),
    'Proverbs':           ('Proverbs',       20),
    'Ecclesiastes':       ('Ecclesiastes',   21),
    'Song of Solomon':    ('Song of Songs',  22),
    'Isaiah':             ('Isaiah',         23),
    'Jeremiah':           ('Jeremiah',       24),
    'Lamentations':       ('Lamentations',   25),
    'Ezekiel':            ('Ezekiel',        26),
    'Daniel':             ('Daniel',         27),
    'Hosea':              ('Hosea',          28),
    'Joel':               ('Joel',           29),
    'Amos':               ('Amos',           30),
    'Obadiah':            ('Obadiah',        31),
    'Jonah':              ('Jonah',          32),
    'Micah':              ('Micah',          33),
    'Nahum':              ('Nahum',          34),
    'Habakkuk':           ('Habakkuk',       35),
    'Zephaniah':          ('Zephaniah',      36),
    'Haggai':             ('Haggai',         37),
    'Zechariah':          ('Zechariah',      38),
    'Malachi':            ('Malachi',        39),
    # NT
    'Matthew':            ('Matthew',        41),
    'Mark':               ('Mark',           42),
    'Luke':               ('Luke',           43),
    'John':               ('John',           44),
    'Acts':               ('Acts',           45),
    'Romans':             ('Romans',         46),
    'I Corinthians':      ('1 Corinthians',  47),
    'II Corinthians':     ('2 Corinthians',  48),
    'Galatians':          ('Galatians',      49),
    'Ephesians':          ('Ephesians',      50),
    'Philippians':        ('Philippians',    51),
    'Colossians':         ('Colossians',     52),
    'I Thessalonians':    ('1 Thessalonians',53),
    'II Thessalonians':   ('2 Thessalonians',54),
    'I Timothy':          ('1 Timothy',      55),
    'II Timothy':         ('2 Timothy',      56),
    'Titus':              ('Titus',          57),
    'Philemon':           ('Philemon',       58),
    'Hebrews':            ('Hebrews',        59),
    'James':              ('James',          60),
    'I Peter':            ('1 Peter',        61),
    'II Peter':           ('2 Peter',        62),
    'I John':             ('1 John',         63),
    'II John':            ('2 John',         64),
    'III John':           ('3 John',         65),
    'Jude':               ('Jude',           66),
    'Revelation of John': ('Revelation',     67),
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong',
    'manuscript', 'tradition',
]


def book_slug(name: str) -> str:
    return name.lower().replace(' ', '_').replace("'", '')


def main():
    parser = argparse.ArgumentParser(description='Ingest Clementine Vulgate from scrollmapper')
    parser.add_argument('--out', default='data/corpora/vul_clementine',
                        help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print(f'Downloading {VUL_CSV_URL} …')
    # Use unverified SSL context to work around macOS Python cert issues
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(VUL_CSV_URL, timeout=60, context=ctx) as resp:
        raw_bytes = resp.read()

    print(f'Downloaded {len(raw_bytes):,} bytes. Parsing…')

    # Group rows by scrollmapper book name
    book_rows: dict[str, list] = {}
    reader = csv.DictReader(io.StringIO(raw_bytes.decode('utf-8')))

    for row in reader:
        src_book = row.get('Book', '').strip()
        if src_book not in BOOK_MAP:
            continue

        try:
            c = int(row.get('Chapter', 0))
            v = int(row.get('Verse', 0))
        except (ValueError, KeyError):
            continue

        t = row.get('Text', '').strip()
        book_rows.setdefault(src_book, []).append({'c': c, 'v': v, 't': t})

    total_words = 0
    files_written = 0

    # Sort by our book_order
    sorted_src_books = sorted(book_rows.keys(), key=lambda b: BOOK_MAP[b][1])

    for src_book in sorted_src_books:
        rows = book_rows[src_book]
        book_name, book_order = BOOK_MAP[src_book]
        slug = book_slug(book_name)
        out_path = os.path.join(args.out, f'{slug}.csv')
        word_count = 0

        with open(out_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in rows:
                verse_text = row['t']
                if not verse_text:
                    continue
                reference = f"{book_name} {row['c']}:{row['v']}"
                words = verse_text.split()
                for pos, word in enumerate(words, start=1):
                    writer.writerow({
                        'book_order': book_order,
                        'book':       book_name,
                        'chapter':    row['c'],
                        'verse':      row['v'],
                        'reference':  reference,
                        'position':   pos,
                        'word_text':  word,
                        'lemma':      '',
                        'morph':      '',
                        'strong':     '',
                        'manuscript': 'Clementine',
                        'tradition':  'VUL',
                    })
                    word_count += 1

        print(f'  {slug}.csv — {word_count} words')
        total_words += word_count
        files_written += 1

    print(f'\nDone. {files_written} CSV files, {total_words:,} total words.')


if __name__ == '__main__':
    main()
