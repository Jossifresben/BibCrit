#!/usr/bin/env python3
"""Ingest ETCBC Peshitta (Syriac OT) into BibCrit CSV format.

Source: ETCBC/peshitta via Text-Fabric (SEDRA-based, LinkSyr project).
License: CC-BY-NC (ETCBC / Eep Talstra Centre for Bible and Computer)

Prerequisites:
  pip install text-fabric
  python -c "from tf.app import use; use('ETCBC/peshitta', hoist=globals())"
  # ^ downloads ETCBC Peshitta TF data to ~/text-fabric-data/

Usage:
  python scripts/ingest_peshitta.py --out data/corpora/pesh_etcbc/

Output:
  One CSV per canonical OT book (e.g. genesis.csv, isaiah.csv) with schema:
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition

  Deuterocanonical / apocryphal books present in the Peshitta corpus
  (Wisdom of Solomon, Sirach, Judith, Baruch, etc.) are skipped — BibCrit
  currently covers only the Hebrew Bible canon.

Data license: CC-BY-NC (ETCBC/peshitta via SEDRA / Beth Mardutho)
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong', 'manuscript', 'tradition',
]

# TF section name → (BibCrit canonical name, book_order, output filename stem)
# Only books present in BibCrit's Hebrew Bible canon are included.
BOOK_MAP: dict[str, tuple[str, int, str]] = {
    'Genesis':       ('Genesis',        1,  'genesis'),
    'Exodus':        ('Exodus',         2,  'exodus'),
    'Leviticus':     ('Leviticus',      3,  'leviticus'),
    'Numbers':       ('Numbers',        4,  'numbers'),
    'Deuteronomy':   ('Deuteronomy',    5,  'deuteronomy'),
    'Joshua':        ('Joshua',         6,  'joshua'),
    'Judges':        ('Judges',         7,  'judges'),
    'Ruth':          ('Ruth',           8,  'ruth'),
    'Samuel_1':      ('1 Samuel',       9,  '1_samuel'),
    'Samuel_2':      ('2 Samuel',      10,  '2_samuel'),
    'Kings_1':       ('1 Kings',       11,  '1_kings'),
    'Kings_2':       ('2 Kings',       12,  '2_kings'),
    'Chronicles_1':  ('1 Chronicles',  13,  '1_chronicles'),
    'Chronicles_2':  ('2 Chronicles',  14,  '2_chronicles'),
    'Ezra':          ('Ezra',          15,  'ezra'),
    'Nehemia':       ('Nehemiah',      16,  'nehemiah'),
    'Esther':        ('Esther',        17,  'esther'),
    'Job':           ('Job',           18,  'job'),
    'Psalms':        ('Psalms',        19,  'psalms'),
    'Proverbs':      ('Proverbs',      20,  'proverbs'),
    'Ecclesiastes':  ('Ecclesiastes',  21,  'ecclesiastes'),
    'Song_of_Songs': ('Song of Songs', 22,  'song_of_songs'),
    'Isaiah':        ('Isaiah',        23,  'isaiah'),
    'Jeremiah':      ('Jeremiah',      24,  'jeremiah'),
    'Lamentations':  ('Lamentations',  25,  'lamentations'),
    'Ezekiel':       ('Ezekiel',       26,  'ezekiel'),
    'Daniel':        ('Daniel',        27,  'daniel'),
    'Hosea':         ('Hosea',         28,  'hosea'),
    'Joel':          ('Joel',          29,  'joel'),
    'Amos':          ('Amos',          30,  'amos'),
    'Obadiah':       ('Obadiah',       31,  'obadiah'),
    'Jonah':         ('Jonah',         32,  'jonah'),
    'Micah':         ('Micah',         33,  'micah'),
    'Nahum':         ('Nahum',         34,  'nahum'),
    'Habakkuk':      ('Habakkuk',      35,  'habakkuk'),
    'Zephaniah':     ('Zephaniah',     36,  'zephaniah'),
    'Haggai':        ('Haggai',        37,  'haggai'),
    'Zechariah':     ('Zechariah',     38,  'zechariah'),
    'Malachi':       ('Malachi',       39,  'malachi'),
}


def ingest(out_dir: str) -> None:
    import os as _os
    from tf.fabric import Fabric

    tf_path = _os.path.expanduser(
        '~/text-fabric-data/github/ETCBC/peshitta/tf/0.2'
    )
    if not _os.path.isdir(tf_path):
        sys.exit(
            f'ERROR: ETCBC/peshitta TF data not found at {tf_path}\n'
            'Run: python -c "from tf.app import use; '
            'use(\'ETCBC/peshitta\', hoist=globals())"'
        )

    print(f'Loading ETCBC/peshitta TF data from {tf_path}…')
    TF = Fabric(locations=[tf_path])
    api = TF.load('book chapter verse word', silent=True)
    if not api:
        sys.exit('ERROR: Failed to load ETCBC/peshitta TF features.')

    F = api.F
    T = api.T
    L = api.L

    os.makedirs(out_dir, exist_ok=True)

    # ── One CSV per book ──────────────────────────────────────────────────────
    total_words  = 0
    books_written = 0
    books_skipped = 0

    book_nodes = list(F.otype.s('book'))
    print(f'  {len(book_nodes)} books in Peshitta corpus')

    for book_node in book_nodes:
        # Get all words in this book and derive the section name from the first
        words_in_book = L.d(book_node, otype='word')
        if not words_in_book:
            continue

        sec = T.sectionFromNode(words_in_book[0])
        tf_book_name = sec[0] if sec else None

        if tf_book_name not in BOOK_MAP:
            books_skipped += 1
            continue  # deuterocanonical / apocryphal

        canonical, book_order, stem = BOOK_MAP[tf_book_name]
        out_path = os.path.join(out_dir, f'{stem}.csv')

        verse_pos: dict[str, int] = {}
        rows = 0

        with open(out_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()

            for word_node in words_in_book:
                sec_w = T.sectionFromNode(word_node)
                if not sec_w or len(sec_w) < 3:
                    continue
                _, ch, vs = sec_w
                if not ch or not vs:
                    continue

                word_text = (F.word.v(word_node) or '').strip()
                if not word_text:
                    continue

                reference = f'{canonical} {ch}:{vs}'
                verse_pos[reference] = verse_pos.get(reference, 0) + 1

                writer.writerow({
                    'book_order': book_order,
                    'book':       canonical,
                    'chapter':    ch,
                    'verse':      vs,
                    'reference':  reference,
                    'position':   verse_pos[reference],
                    'word_text':  word_text,
                    'lemma':      '',   # SEDRA lemma not available in this TF module
                    'morph':      '',
                    'strong':     '',
                    'manuscript': 'Peshitta',
                    'tradition':  'PESH',
                })
                rows += 1

        total_words  += rows
        books_written += 1
        print(f'  {canonical:<20} → {stem}.csv  ({rows} words)')

    print()
    print(f'Peshitta ingestion complete:')
    print(f'  {books_written} OT books written → {out_dir}')
    print(f'  {books_skipped} deuterocanonical books skipped')
    print(f'  {total_words:,} total word tokens')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--out', default='data/corpora/pesh_etcbc/',
        help='Output directory (default: data/corpora/pesh_etcbc/)',
    )
    args = parser.parse_args()
    ingest(args.out)


if __name__ == '__main__':
    main()
