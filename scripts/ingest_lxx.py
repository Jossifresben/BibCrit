"""Ingest STEPBible LXXM into BibCrit word-level CSV format.

STEPBible LXXM source:
  https://github.com/STEPBible/STEPBible-Data

Usage:
  python scripts/ingest_lxx.py \
      --src path/to/LXXM-LXX.txt \
      --out data/corpora/lxx_stepbible/
"""

import argparse
import csv
import os
import re

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong', 'manuscript', 'tradition',
]

BOOK_MAP = {
    'Gen': ('Genesis', 1), 'Exod': ('Exodus', 2), 'Lev': ('Leviticus', 3),
    'Num': ('Numbers', 4), 'Deut': ('Deuteronomy', 5), 'Josh': ('Joshua', 6),
    'Judg': ('Judges', 7), 'Ruth': ('Ruth', 8), '1Sam': ('1 Samuel', 9),
    '2Sam': ('2 Samuel', 10), '1Kgs': ('1 Kings', 11), '2Kgs': ('2 Kings', 12),
    'Isa': ('Isaiah', 23), 'Jer': ('Jeremiah', 24), 'Ps': ('Psalms', 19),
}


def ingest(src_path: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    current_book = None
    writer = None
    fh = None
    verse_word_count: dict = {}

    with open(src_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 4:
                continue

            ref_raw = parts[0].strip()
            greek = parts[1].strip()
            strong = parts[2].strip() if len(parts) > 2 else ''
            morph = parts[3].strip() if len(parts) > 3 else ''
            lemma = parts[4].strip() if len(parts) > 4 else greek

            m = re.match(r'(\w+)\.(\d+)\.(\d+)', ref_raw)
            if not m:
                continue
            abbrev, ch_str, v_str = m.group(1), m.group(2), m.group(3)
            if abbrev not in BOOK_MAP:
                continue

            book_name, book_order = BOOK_MAP[abbrev]
            ch_num = int(ch_str)
            v_num = int(v_str)
            reference = f'{book_name} {ch_num}:{v_num}'

            if book_name != current_book:
                if fh:
                    fh.close()
                safe_name = book_name.lower().replace(' ', '_')
                out_path = os.path.join(out_dir, f'{safe_name}.csv')
                fh = open(out_path, 'w', newline='', encoding='utf-8')
                writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
                writer.writeheader()
                current_book = book_name
                verse_word_count.clear()
                print(f'  Writing {out_path}')

            verse_word_count[reference] = verse_word_count.get(reference, 0) + 1
            pos = verse_word_count[reference]

            writer.writerow({
                'book_order': book_order,
                'book': book_name,
                'chapter': ch_num,
                'verse': v_num,
                'reference': reference,
                'position': pos,
                'word_text': greek,
                'lemma': lemma,
                'morph': morph,
                'strong': strong,
                'manuscript': 'Vaticanus',
                'tradition': 'LXX',
            })

    if fh:
        fh.close()
    print('LXX ingestion complete.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest STEPBible LXXM into BibCrit CSV format')
    parser.add_argument('--src', required=True, help='Path to STEPBible LXXM .txt file')
    parser.add_argument('--out', default='data/corpora/lxx_stepbible/', help='Output directory')
    args = parser.parse_args()
    ingest(args.src, args.out)
