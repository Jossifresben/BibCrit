"""Ingest DT-UCPH Samaritan Pentateuch into BibCrit CSV format.

Prerequisites:
  pip install text-fabric
  python -c "from tf.app import use; use('dt-ucph/sp', hoist=globals())"
  # ^ downloads SP data to ~/text-fabric-data/

Usage:
  python scripts/ingest_sp.py --out data/corpora/sp_etcbc/

Output:
  5 per-book CSVs (genesis.csv … deuteronomy.csv) with schema:
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition

Corpus:
  MS Dublin Chester Beatty Library 751 (Hebrew/square script)
  Primary manuscript: Chester Beatty 751
  Data license: CC BY-NC 4.0 (DT-UCPH/sp, Zenodo 10.5281/zenodo.7734632)

Note on morphology:
  The SP dataset has no `vs` (verbal stem: qal/nifal/piel) feature,
  unlike BHSA/MT. The morph field is `sp.vt` (e.g. `verb.perf`) or
  just `sp` for non-verbal words. This is less detailed than MT's
  `sp.vs.vt` but sufficient for display and comparison purposes.
"""

import argparse
import csv
import os

BOOK_ORDER = {
    'Genesis':     1,
    'Exodus':      2,
    'Leviticus':   3,
    'Numbers':     4,
    'Deuteronomy': 5,
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong', 'manuscript', 'tradition',
]


def ingest(out_dir: str) -> None:
    from tf.app import use
    A = use('dt-ucph/sp', hoist=globals(), silence='deep')  # noqa: F821

    os.makedirs(out_dir, exist_ok=True)

    total_words = 0

    for book_node in F.otype.s('book'):  # noqa: F821
        book_name = F.book.v(book_node)  # noqa: F821
        if book_name not in BOOK_ORDER:
            print(f'  Skipping unexpected book: {book_name!r}')
            continue

        book_order = BOOK_ORDER[book_name]
        out_path = os.path.join(out_dir, f'{book_name.lower()}.csv')
        book_words = 0

        with open(out_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()

            for chapter_node in L.d(book_node, otype='chapter'):  # noqa: F821
                ch_num = T.sectionFromNode(chapter_node)[1]  # noqa: F821

                for verse_node in L.d(chapter_node, otype='verse'):  # noqa: F821
                    v_num = T.sectionFromNode(verse_node)[2]  # noqa: F821
                    reference = f'{book_name} {ch_num}:{v_num}'

                    for pos, word_node in enumerate(
                        L.d(verse_node, otype='word'), 1  # noqa: F821
                    ):
                        # Surface form: consonantal Hebrew (square script)
                        word_text = F.g_cons_utf8.v(word_node) or ''  # noqa: F821
                        if not word_text.strip():
                            continue

                        # Lexeme / lemma (ETCBC transliteration)
                        lemma = F.lex.v(word_node) or ''  # noqa: F821

                        # Morphology: part-of-speech + verbal tense (no verbal stem in SP)
                        sp_val = F.sp.v(word_node) or ''   # noqa: F821
                        vt_val = F.vt.v(word_node) or ''   # noqa: F821
                        if vt_val and vt_val != 'NA':
                            morph = f'{sp_val}.{vt_val}'
                        else:
                            morph = sp_val

                        writer.writerow({
                            'book_order': book_order,
                            'book': book_name,
                            'chapter': ch_num,
                            'verse': v_num,
                            'reference': reference,
                            'position': pos,
                            'word_text': word_text.strip(),
                            'lemma': lemma,
                            'morph': morph,
                            'strong': '',
                            'manuscript': 'Chester Beatty 751',
                            'tradition': 'SP',
                        })
                        book_words += 1

        print(f'  {book_name}: {book_words} words → {out_path}')
        total_words += book_words

    print(f'SP ingestion complete: {total_words} words total')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Ingest DT-UCPH Samaritan Pentateuch into BibCrit CSV format'
    )
    parser.add_argument('--out', default='data/corpora/sp_etcbc/', help='Output directory')
    args = parser.parse_args()
    ingest(args.out)
