#!/usr/bin/env python3
"""Ingest additional ETCBC DSS scrolls into BibCrit CSV format.

Scrolls ingested:
  4Q51  — 4QSamᵃ        (1/2 Samuel fragments)
  11Q1  — 11QPaleoLev   (Leviticus in paleo-Hebrew script)
  4Q41  — 4QDeutn       (Deuteronomy fragments)

NOTE: 1QpHab is excluded — the ETCBC DSS dataset has no MT-aligned chapter/verse
coordinates for this scroll (all chapter/verse fields are None), so it cannot be
integrated into the verse-keyed corpus without significant additional alignment work.

Prerequisites:
  pip install text-fabric
  # ETCBC/dss already downloaded to ~/text-fabric-data/ (used for 1QIsaᵃ)

Usage:
  python scripts/ingest_dss_witnesses.py --out data/corpora/dss/

Output (appended to existing dss/ directory):
  4qsama.csv        — 4QSamᵃ words with 1/2 Samuel verse references
  11qpaleolev.csv   — 11QPaleoLev words with Leviticus verse references
  4qdeutn.csv       — 4QDeutn words with Deuteronomy verse references

Schema (same as 1qisaa.csv):
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition

Data license: CC-BY-NC (ETCBC/DSS)
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

# book_etcbc value → (canonical BibCrit book name, book_order)
BOOK_ETCBC_MAP: dict[str, tuple[str, int]] = {
    '1_Samuel':    ('1 Samuel',    9),
    '2_Samuel':    ('2 Samuel',   10),
    'Leviticus':   ('Leviticus',   3),
    'Deuteronomy': ('Deuteronomy', 5),
}

# Scroll definitions: (scroll_id, output_filename, manuscript_label)
SCROLLS: list[tuple[str, str, str]] = [
    ('4Q51',   '4qsama.csv',       '4QSamA'),
    ('11Q1',   '11qpaleolev.csv',  '11QPaleoLev'),
    ('4Q41',   '4qdeutn.csv',      '4QDeutn'),
]


def _find_scroll_node(scroll_id: str) -> int | None:
    """Return the scroll-level node for the given scroll identifier."""
    from tf.fabric import Fabric  # noqa: F401 — TF already loaded via use()
    try:
        F = globals()['F']  # noqa: F841 — populated by TF hoist
    except KeyError:
        pass

    import builtins
    F_api = builtins.__dict__.get('F') or globals().get('F')
    if F_api is None:
        raise RuntimeError('Text-Fabric API not initialised; call _load_tf() first.')

    for n in range(1, 3_000_000):
        try:
            sc = F_api.scroll.v(n)
            if sc == scroll_id:
                return n
        except Exception:
            break
    return None


# Module-level TF API handles (populated by _load_tf)
_F = None
_L = None


def _load_tf() -> None:
    global _F, _L
    import os as _os
    from tf.fabric import Fabric

    tf_path = _os.path.expanduser('~/text-fabric-data/github/ETCBC/dss/tf/1.9')
    if not _os.path.isdir(tf_path):
        sys.exit(
            f'ERROR: ETCBC/dss TF data not found at {tf_path}\n'
            'Run: python -c "from tf.app import use; use(\'ETCBC/dss\', hoist=globals())"'
        )
    TF = Fabric(locations=[tf_path])
    api = TF.load(
        'scroll book book_etcbc chapter verse glyph lex sp vs vt rec unc',
        silent=True,
    )
    if not api:
        sys.exit('ERROR: Failed to load ETCBC/dss TF features.')
    _F = api.F
    _L = api.L
    print(f'Loaded ETCBC/dss TF data from {tf_path}')


def _find_scroll_node_v2(scroll_id: str) -> int | None:
    """Return the scroll-type node for the given scroll identifier.

    Iterates only over scroll-otype nodes (not all integer nodes) to avoid
    hitting word-level nodes that share the same scroll feature value.
    """
    for n in _F.otype.s('scroll'):
        if _F.scroll.v(n) == scroll_id:
            return n
    return None


def ingest_scroll(scroll_id: str, out_filename: str, manuscript: str, out_dir: str) -> int:
    """Ingest one scroll into a CSV file. Returns number of rows written."""
    scroll_node = _find_scroll_node_v2(scroll_id)
    if scroll_node is None:
        print(f'  ERROR: scroll node not found for {scroll_id}')
        return 0

    word_nodes = _L.d(scroll_node, otype='word')
    print(f'  {scroll_id}: scroll_node={scroll_node}, {len(word_nodes)} word nodes')

    out_path = os.path.join(out_dir, out_filename)
    rows_written = 0
    skipped_no_ref = 0
    skipped_no_book = 0

    verse_pos: dict[str, int] = {}

    with open(out_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()

        for word_node in word_nodes:
            ch  = _F.chapter.v(word_node)
            vs  = _F.verse.v(word_node)
            bk  = _F.book_etcbc.v(word_node) or ''

            # Skip words without valid chapter/verse (non-aligned or commentary)
            if not ch or not vs:
                skipped_no_ref += 1
                continue
            try:
                ch_int = int(ch)
                vs_int = int(vs)
            except (TypeError, ValueError):
                skipped_no_ref += 1
                continue

            # Resolve book name
            if bk not in BOOK_ETCBC_MAP:
                skipped_no_book += 1
                continue
            book_name, book_order = BOOK_ETCBC_MAP[bk]

            reference = f'{book_name} {ch_int}:{vs_int}'
            verse_pos[reference] = verse_pos.get(reference, 0) + 1
            pos = verse_pos[reference]

            # Surface text — glyph is the original script representation
            word_text = (_F.glyph.v(word_node) or '').strip()
            if not word_text:
                rec = _F.rec.v(word_node) or ''
                unc = _F.unc.v(word_node) or ''
                if rec or unc:
                    word_text = '[...]'
                else:
                    continue  # skip empty words with no annotation

            # Lemma
            lemma = _F.lex.v(word_node) or ''

            # Morphology
            sp      = _F.sp.v(word_node)  or ''
            vs_feat = _F.vs.v(word_node)  or ''
            vt_feat = _F.vt.v(word_node)  or ''
            morph   = f'{sp}.{vs_feat}.{vt_feat}' if vs_feat and vt_feat else sp

            writer.writerow({
                'book_order': book_order,
                'book':       book_name,
                'chapter':    ch_int,
                'verse':      vs_int,
                'reference':  reference,
                'position':   pos,
                'word_text':  word_text,
                'lemma':      lemma,
                'morph':      morph,
                'strong':     '',
                'manuscript': manuscript,
                'tradition':  'DSS',
            })
            rows_written += 1

    print(f'  → {rows_written} rows written to {out_path}')
    if skipped_no_ref:
        print(f'    (skipped {skipped_no_ref} words without chapter/verse alignment)')
    if skipped_no_book:
        print(f'    (skipped {skipped_no_book} words with unrecognised book identifier)')
    return rows_written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='data/corpora/dss/',
                        help='Output directory (default: data/corpora/dss/)')
    args = parser.parse_args()

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    print('Loading ETCBC/dss Text-Fabric data…')
    _load_tf()
    print()

    total = 0
    for scroll_id, filename, manuscript in SCROLLS:
        print(f'Ingesting {scroll_id} ({manuscript}) → {filename}')
        n = ingest_scroll(scroll_id, filename, manuscript, out_dir)
        total += n
        print()

    print(f'Done. {total} total words written across {len(SCROLLS)} scrolls.')
    print(f'Output directory: {out_dir}')
    existing = [f for f in os.listdir(out_dir) if f.endswith('.csv')]
    print(f'DSS CSV files now: {sorted(existing)}')


if __name__ == '__main__':
    main()
