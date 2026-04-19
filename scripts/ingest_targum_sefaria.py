#!/usr/bin/env python3
"""Download Targum Onkelos (Torah) and Targum Jonathan (Prophets) from Sefaria.

Usage:
    python scripts/ingest_targum_sefaria.py --out data/corpora/targ_sefaria/

Writes one CSV per book, e.g. genesis_onkelos.csv, isaiah_jonathan.csv.
Schema: book_order,book,chapter,verse,reference,position,word_text,lemma,morph,strong,manuscript,tradition
"""

import argparse
import csv
import os
import ssl
import sys
import time
import urllib.request
import urllib.parse
import json

# On macOS the system Python often lacks the correct CA bundle.
# Use certifi if available, otherwise fall back to an unverified context.
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

# Targum Onkelos: Torah (5 books)
ONKELOS_BOOKS = [
    ('Genesis',     1,  50, 'genesis_onkelos'),
    ('Exodus',      2,  40, 'exodus_onkelos'),
    ('Leviticus',   3,  27, 'leviticus_onkelos'),
    ('Numbers',     4,  36, 'numbers_onkelos'),
    ('Deuteronomy', 5,  34, 'deuteronomy_onkelos'),
]

# Targum Jonathan: Former + Latter Prophets (21 books)
JONATHAN_BOOKS = [
    ('Joshua',      6,  24, 'joshua_jonathan'),
    ('Judges',      7,  21, 'judges_jonathan'),
    ('1 Samuel',    9,  31, '1samuel_jonathan'),
    ('2 Samuel',    10, 24, '2samuel_jonathan'),
    ('1 Kings',     11, 22, '1kings_jonathan'),
    ('2 Kings',     12, 25, '2kings_jonathan'),
    ('Isaiah',      23, 66, 'isaiah_jonathan'),
    ('Jeremiah',    24, 52, 'jeremiah_jonathan'),
    ('Ezekiel',     26, 48, 'ezekiel_jonathan'),
    ('Hosea',       28, 14, 'hosea_jonathan'),
    ('Joel',        29, 3,  'joel_jonathan'),
    ('Amos',        30, 9,  'amos_jonathan'),
    ('Obadiah',     31, 1,  'obadiah_jonathan'),
    ('Jonah',       32, 4,  'jonah_jonathan'),
    ('Micah',       33, 7,  'micah_jonathan'),
    ('Nahum',       34, 3,  'nahum_jonathan'),
    ('Habakkuk',    35, 3,  'habakkuk_jonathan'),
    ('Zephaniah',   36, 3,  'zephaniah_jonathan'),
    ('Haggai',      37, 2,  'haggai_jonathan'),
    ('Zechariah',   38, 14, 'zechariah_jonathan'),
    ('Malachi',     39, 4,  'malachi_jonathan'),
]

SEFARIA_API = 'https://www.sefaria.org/api/texts'

SEFARIA_SLUGS = {
    'Genesis': 'Onkelos_Genesis',
    'Exodus': 'Onkelos_Exodus',
    'Leviticus': 'Onkelos_Leviticus',
    'Numbers': 'Onkelos_Numbers',
    'Deuteronomy': 'Onkelos_Deuteronomy',
    'Joshua': 'Targum_Jonathan_on_Joshua',
    'Judges': 'Targum_Jonathan_on_Judges',
    '1 Samuel': 'Targum_Jonathan_on_I_Samuel',
    '2 Samuel': 'Targum_Jonathan_on_II_Samuel',
    '1 Kings': 'Targum_Jonathan_on_I_Kings',
    '2 Kings': 'Targum_Jonathan_on_II_Kings',
    'Isaiah': 'Targum_Jonathan_on_Isaiah',
    'Jeremiah': 'Targum_Jonathan_on_Jeremiah',
    'Ezekiel': 'Targum_Jonathan_on_Ezekiel',
    'Hosea': 'Targum_Jonathan_on_Hosea',
    'Joel': 'Targum_Jonathan_on_Joel',
    'Amos': 'Targum_Jonathan_on_Amos',
    'Obadiah': 'Targum_Jonathan_on_Obadiah',
    'Jonah': 'Targum_Jonathan_on_Jonah',
    'Micah': 'Targum_Jonathan_on_Micah',
    'Nahum': 'Targum_Jonathan_on_Nahum',
    'Habakkuk': 'Targum_Jonathan_on_Habakkuk',
    'Zephaniah': 'Targum_Jonathan_on_Zephaniah',
    'Haggai': 'Targum_Jonathan_on_Haggai',
    'Zechariah': 'Targum_Jonathan_on_Zechariah',
    'Malachi': 'Targum_Jonathan_on_Malachi',
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong',
    'manuscript', 'tradition',
]


def fetch_chapter(slug: str, chapter: int) -> list[str] | None:
    """Fetch one chapter from Sefaria. Returns list of verse strings (Aramaic)."""
    url = f'{SEFARIA_API}/{urllib.parse.quote(slug)}.{chapter}?lang=he&context=0'
    try:
        with urllib.request.urlopen(url, timeout=30, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode())
        # 'he' field = Aramaic text array (one string per verse)
        verses = data.get('he', [])
        if isinstance(verses, str):
            return [verses]
        return verses if isinstance(verses, list) else []
    except Exception as e:
        print(f'    WARN fetch failed for {slug}.{chapter}: {e}', file=sys.stderr)
        return None


def strip_html(text: str) -> str:
    """Remove simple HTML tags from Sefaria text."""
    import re
    return re.sub(r'<[^>]+>', '', text).strip()


def process_book(book: str, book_order: int, num_chapters: int,
                 filename: str, manuscript: str, out_dir: str) -> int:
    """Download all chapters of a book and write CSV. Returns word count."""
    slug = SEFARIA_SLUGS[book]
    out_path = os.path.join(out_dir, f'{filename}.csv')
    word_count = 0

    with open(out_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()

        for chapter in range(1, num_chapters + 1):
            verses = fetch_chapter(slug, chapter)
            if verses is None:
                # retry once after a short wait
                time.sleep(2)
                verses = fetch_chapter(slug, chapter)
            if not verses:
                continue

            for verse_idx, verse_text in enumerate(verses, start=1):
                cleaned = strip_html(verse_text)
                if not cleaned:
                    continue
                reference = f'{book} {chapter}:{verse_idx}'
                words = cleaned.split()
                for pos, word in enumerate(words, start=1):
                    writer.writerow({
                        'book_order': book_order,
                        'book':       book,
                        'chapter':    chapter,
                        'verse':      verse_idx,
                        'reference':  reference,
                        'position':   pos,
                        'word_text':  word,
                        'lemma':      '',
                        'morph':      '',
                        'strong':     '',
                        'manuscript': manuscript,
                        'tradition':  'TARG',
                    })
                    word_count += 1

            time.sleep(0.15)  # be polite to Sefaria API

    print(f'  {filename}.csv — {word_count} words')
    return word_count


def main():
    parser = argparse.ArgumentParser(description='Ingest Targum corpus from Sefaria')
    parser.add_argument('--out', default='data/corpora/targ_sefaria',
                        help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    total = 0

    print('Downloading Targum Onkelos (Torah)...')
    for book, order, chapters, fname in ONKELOS_BOOKS:
        total += process_book(book, order, chapters, fname, 'Onkelos', args.out)

    print('Downloading Targum Jonathan (Prophets)...')
    for book, order, chapters, fname in JONATHAN_BOOKS:
        total += process_book(book, order, chapters, fname, 'Jonathan', args.out)

    print(f'\nDone. Total tokens: {total:,}')
    csv_count = len([f for f in os.listdir(args.out) if f.endswith('.csv')])
    print(f'CSV files written: {csv_count}')


if __name__ == '__main__':
    main()
