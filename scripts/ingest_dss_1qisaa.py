"""Ingest ETCBC DSS 1QIsaᵃ (Great Isaiah Scroll) into BibCrit CSV format.

Prerequisites:
  pip install text-fabric
  python -c "from tf.app import use; use('ETCBC/dss', hoist=globals())"
  # ^ downloads ETCBC DSS data to ~/text-fabric-data/

Usage:
  python scripts/ingest_dss_1qisaa.py --out data/corpora/dss/

Output:
  1qisaa.csv with schema:
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition

Data license: CC-BY-NC (ETCBC/DSS)
"""

import argparse
import csv
import os

# 1QIsaᵃ uses book_order 23 (Isaiah) for sorting alongside MT/LXX Isaiah
BOOK_ORDER = 23
FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong', 'manuscript', 'tradition',
]

# Known scroll identifiers for 1QIsaᵃ in ETCBC DSS
# The scroll may appear under various IDs; we try all plausible names
SCROLL_NAMES = {'1QIsa', '1QIsaa', '1QIsa-a', '1QIsaA', '1Q8', 'Q1Isa'}


def ingest(out_dir: str) -> None:
    from tf.app import use
    A = use('ETCBC/dss', hoist=globals(), silence='deep')  # noqa: F821

    os.makedirs(out_dir, exist_ok=True)

    # Find the scroll node for 1QIsaᵃ
    # The `scroll` feature lives on scroll-level nodes, not word nodes.
    scroll_node = _find_scroll_node()
    if scroll_node is None:
        print('ERROR: Could not find 1QIsaᵃ scroll node in dataset.')
        print('Node types available:', list(F.otype.all))  # noqa: F821
        print('Sample scroll nodes (up to 20):')
        for node in list(F.otype.s('scroll'))[:20]:  # noqa: F821
            print(f'  node={node}  scroll={F.scroll.v(node)!r}')  # noqa: F821
        return

    scroll_id = F.scroll.v(scroll_node)  # noqa: F821
    print(f'Found 1QIsaᵃ scroll node {scroll_node} (scroll={scroll_id!r})')

    # Descend from scroll → word using the locality API
    word_nodes = L.d(scroll_node, otype='word')  # noqa: F821
    print(f'  {len(word_nodes)} word nodes in scroll')

    out_path = os.path.join(out_dir, '1qisaa.csv')
    rows_written = 0

    with open(out_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()

        # Track position within each verse
        verse_pos: dict = {}

        for word_node in word_nodes:
            # Get verse location (MT alignment)
            ch = F.chapter.v(word_node)   # noqa: F821
            vs = F.verse.v(word_node)     # noqa: F821

            # Skip words without valid chapter/verse (non-biblical sections)
            if not ch or not vs:
                continue
            try:
                ch_int = int(ch)
                vs_int = int(vs)
            except (TypeError, ValueError):
                continue

            reference = f'Isaiah {ch_int}:{vs_int}'

            # Word position within verse
            verse_pos[reference] = verse_pos.get(reference, 0) + 1
            pos = verse_pos[reference]

            # Surface text — use glyph (original script representation)
            word_text = F.glyph.v(word_node) or ''   # noqa: F821

            # Mark lacunae/damaged text
            if not word_text.strip():
                rec = F.rec.v(word_node) or ''   # noqa: F821
                unc = F.unc.v(word_node) or ''   # noqa: F821
                if rec or unc:
                    word_text = '[...]'  # reconstructed or uncertain
                else:
                    continue  # skip empty words with no annotation

            # Lexeme/lemma
            lemma = F.lex.v(word_node) or ''   # noqa: F821

            # Morphology: part of speech + verbal stem + verbal tense
            sp = F.sp.v(word_node) or ''    # noqa: F821
            vs_feat = F.vs.v(word_node) or ''  # noqa: F821
            vt_feat = F.vt.v(word_node) or ''  # noqa: F821
            morph = f'{sp}.{vs_feat}.{vt_feat}' if vs_feat and vt_feat else sp

            writer.writerow({
                'book_order': BOOK_ORDER,
                'book': 'Isaiah',
                'chapter': ch_int,
                'verse': vs_int,
                'reference': reference,
                'position': pos,
                'word_text': word_text.strip(),
                'lemma': lemma,
                'morph': morph,
                'strong': '',
                'manuscript': '1QIsaA',
                'tradition': 'DSS',
            })
            rows_written += 1

    print(f'DSS 1QIsaᵃ ingestion complete: {rows_written} words → {out_path}')


def _find_scroll_node():
    """Return the scroll node for 1QIsaᵃ in this dataset.

    The `scroll` feature is stored on scroll-type nodes, not word nodes.
    We match by feature value against known 1QIsaᵃ identifiers.
    """
    # Try direct name matching on scroll-level nodes
    for node in F.otype.s('scroll'):  # noqa: F821
        sid = F.scroll.v(node) or ''   # noqa: F821
        if sid in SCROLL_NAMES or sid.replace(' ', '') in SCROLL_NAMES:
            return node

    # Fall back: find the scroll node that has the most Isaiah-aligned words
    # (use L.d to descend from scroll nodes to words)
    best_node = None
    best_count = 0
    for scroll_node in F.otype.s('scroll'):  # noqa: F821
        words = L.d(scroll_node, otype='word')  # noqa: F821
        isa_count = 0
        for w in words[:200]:  # sample first 200 words
            bk = F.book.v(w) or ''   # noqa: F821
            if bk in ('Isaiah', 'Isa'):
                isa_count += 1
        if isa_count > best_count:
            best_count = isa_count
            best_node = scroll_node
    if best_node is not None:
        print(f'Fallback: best Isaiah scroll node={best_node} '
              f'scroll={F.scroll.v(best_node)!r} ({best_count} Isa words sampled)')  # noqa: F821
    return best_node


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest ETCBC DSS 1QIsaᵃ into BibCrit CSV format')
    parser.add_argument('--out', default='data/corpora/dss/', help='Output directory')
    args = parser.parse_args()
    ingest(args.out)
