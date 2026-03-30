"""Ingest ETCBC BHSA into BibCrit word-level CSV format.

Prerequisites:
  pip install text-fabric
  python -c "from tf.app import use; use('ETCBC/bhsa', hoist=globals())"
  # ^ downloads ~600MB of BHSA data to ~/text-fabric-data/

Usage:
  python scripts/ingest_mt.py --out data/corpora/mt_etcbc/

Output:
  One CSV per book (e.g., genesis.csv, isaiah.csv) with schema:
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition
"""

import argparse
import csv
import os

BOOK_ORDER = {
    'Genesis': 1, 'Exodus': 2, 'Leviticus': 3, 'Numbers': 4, 'Deuteronomy': 5,
    'Joshua': 6, 'Judges': 7, 'Ruth': 8, '1_Samuel': 9, '2_Samuel': 10,
    '1_Kings': 11, '2_Kings': 12, '1_Chronicles': 13, '2_Chronicles': 14,
    'Ezra': 15, 'Nehemiah': 16, 'Esther': 17, 'Job': 18, 'Psalms': 19,
    'Proverbs': 20, 'Ecclesiastes': 21, 'Song_of_songs': 22, 'Isaiah': 23,
    'Jeremiah': 24, 'Lamentations': 25, 'Ezekiel': 26, 'Daniel': 27,
    'Hosea': 28, 'Joel': 29, 'Amos': 30, 'Obadiah': 31, 'Jonah': 32,
    'Micah': 33, 'Nahum': 34, 'Habakkuk': 35, 'Zephaniah': 36,
    'Haggai': 37, 'Zechariah': 38, 'Malachi': 39,
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong', 'manuscript', 'tradition',
]


def ingest(out_dir: str) -> None:
    from tf.app import use
    A = use('ETCBC/bhsa', hoist=globals(), silence='deep')  # noqa: F821

    os.makedirs(out_dir, exist_ok=True)

    current_book = None
    writer = None
    fh = None

    for book_node in F.otype.s('book'):  # noqa: F821
        book_name_raw = T.bookName(book_node)  # noqa: F821
        book_name = book_name_raw.replace('_', ' ')
        book_order = BOOK_ORDER.get(book_name_raw, 99)

        if book_name != current_book:
            if fh:
                fh.close()
            out_path = os.path.join(out_dir, f"{book_name_raw.lower()}.csv")
            fh = open(out_path, 'w', newline='', encoding='utf-8')
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()
            current_book = book_name
            print(f'  Writing {out_path}')

        for chapter_node in L.d(book_node, otype='chapter'):  # noqa: F821
            ch_num = T.sectionFromNode(chapter_node)[1]  # noqa: F821

            for verse_node in L.d(chapter_node, otype='verse'):  # noqa: F821
                v_num = T.sectionFromNode(verse_node)[2]  # noqa: F821
                reference = f'{book_name} {ch_num}:{v_num}'

                for pos, word_node in enumerate(L.d(verse_node, otype='word'), 1):  # noqa: F821
                    word_text = T.text(word_node, fmt='text-orig-full')  # noqa: F821
                    lemma = F.lex.v(word_node)  # noqa: F821
                    sp = F.sp.v(word_node)  # noqa: F821
                    vs = F.vs.v(word_node)  # noqa: F821
                    vt = F.vt.v(word_node)  # noqa: F821
                    morph = f'{sp}.{vs}.{vt}' if vs and vt else sp

                    writer.writerow({
                        'book_order': book_order,
                        'book': book_name,
                        'chapter': ch_num,
                        'verse': v_num,
                        'reference': reference,
                        'position': pos,
                        'word_text': word_text.strip(),
                        'lemma': lemma or '',
                        'morph': morph or '',
                        'strong': '',
                        'manuscript': 'Leningrad',
                        'tradition': 'MT',
                    })

    if fh:
        fh.close()
    print('MT ingestion complete.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest ETCBC BHSA into BibCrit CSV format')
    parser.add_argument('--out', default='data/corpora/mt_etcbc/', help='Output directory')
    args = parser.parse_args()
    ingest(args.out)
