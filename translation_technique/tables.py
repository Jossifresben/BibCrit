# translation_technique/tables.py
"""Deterministic aggregation over alignment rows. Pure functions, no I/O."""
from __future__ import annotations

import copy
from collections import Counter, defaultdict

from translation_technique.stats import chi_square, cramers_v

BOOK_ORDER = {
    'genesis': 1, 'exodus': 2, 'leviticus': 3, 'numbers': 4, 'deuteronomy': 5, 'joshua': 6, 'judges': 7,
    'ruth': 8, '1_samuel': 9, '2_samuel': 10, '1_kings': 11, '2_kings': 12, '1_chronicles': 13,
    '2_chronicles': 14, 'ezra': 15, 'nehemiah': 16, 'esther': 17, 'job': 18, 'psalms': 19, 'proverbs': 20,
    'ecclesiastes': 21, 'song_of_songs': 22, 'isaiah': 23, 'jeremiah': 24, 'lamentations': 25, 'ezekiel': 26,
    'daniel': 27, 'hosea': 28, 'joel': 29, 'amos': 30, 'obadiah': 31, 'jonah': 32, 'micah': 33, 'nahum': 34,
    'habakkuk': 35, 'zephaniah': 36, 'haggai': 37, 'zechariah': 38, 'malachi': 39,
}

FACETS: dict[str, dict] = {
    'vs': {'path': ('heb_feats', 'vs'), 'available': True, 'reason': None},
    'vt': {'path': ('heb_feats', 'vt'), 'available': True, 'reason': None},
    'clause_typ': {'path': ('heb_feats', 'clause_typ'), 'available': True, 'reason': None},
    'obj_function': {'path': ('heb_feats', 'obj_function'), 'available': True, 'reason': None},
    'next_prep': {'path': ('heb_feats', 'next_prep'), 'available': True, 'reason': None},
    'book': {'path': ('book',), 'available': True, 'reason': None},
    'animacy': {'path': None, 'available': False,
                'reason': 'not in BHSA; a future annotation layer, model-proposed and scholar-validated'},
}


def book_stem(ref: str) -> str:
    return ref.rsplit(' ', 1)[0].lower().replace(' ', '_')


def _ref_key(ref: str) -> tuple:
    book, cv = ref.rsplit(' ', 1)
    ch, v = cv.split(':')
    return (BOOK_ORDER.get(book.lower().replace(' ', '_'), 99), int(ch), int(v))


def facet_value(row: dict, facet_id: str) -> str:
    spec = FACETS[facet_id]
    if not spec['available']:
        raise ValueError(f'facet {facet_id} is not available: {spec["reason"]}')
    if spec['path'] == ('book',):
        return book_stem(row['ref'])
    feats = row.get('heb_feats') or {}
    return str(feats.get(spec['path'][1], 'NA'))


def _select(rows, heb_lex, books):
    bset = set(books) if books is not None else None
    return [r for r in rows if r['heb_lex'] == heb_lex and (bset is None or book_stem(r['ref']) in bset)]


def _is_model(r: dict) -> bool:
    return r.get('source') == 'model' or r.get('syr_source') == 'model'


def distribution(rows: list[dict], heb_lex: str, books) -> dict:
    sel = _select(rows, heb_lex, books)
    linked = [r for r in sel if r['kind'] != 'null']
    counts, model = Counter(), Counter()
    for r in linked:
        counts[r['syr_lemma']] += 1
        if _is_model(r):
            model[r['syr_lemma']] += 1
    items = [{'syr_lemma': k, 'count': c, 'model_share': model[k] / c}
             for k, c in counts.most_common()]
    return {
        'lex': heb_lex, 'total': len(sel), 'null_count': len(sel) - len(linked), 'items': items,
        'model_share_total': sum(model.values()) / len(linked) if linked else 0.0,
    }


def crosstab(rows: list[dict], heb_lex: str, facet_id: str, books) -> dict:
    if facet_id not in FACETS or not FACETS[facet_id]['available']:
        raise ValueError(f'facet {facet_id} is not available')
    sel = [r for r in _select(rows, heb_lex, books) if r['kind'] != 'null']
    cell = defaultdict(int)
    lemma_tot, val_tot = Counter(), Counter()
    for r in sel:
        v = facet_value(r, facet_id)
        cell[(r['syr_lemma'], v)] += 1
        lemma_tot[r['syr_lemma']] += 1
        val_tot[v] += 1
    lemmas = [k for k, _ in lemma_tot.most_common()]
    values = sorted(val_tot)
    matrix = [[cell[(l, v)] for v in values] for l in lemmas]
    cs = chi_square(matrix) if matrix else {'stat': 0.0, 'dof': 0, 'p': 1.0, 'unreliable': True}
    return {'lex': heb_lex, 'facet': facet_id, 'lemmas': lemmas, 'values': values, 'matrix': matrix,
            'stat': cs['stat'], 'dof': cs['dof'], 'p': cs['p'],
            'cramers_v': cramers_v(matrix, cs['stat']) if matrix else 0.0, 'unreliable': cs['unreliable']}


def model_share(rows: list[dict]) -> float:
    return sum(1 for r in rows if _is_model(r)) / len(rows) if rows else 0.0


def apply_witness(rows: list[dict], substitutions: dict) -> list[dict]:
    out = []
    for r in rows:
        key = (r['ref'], r.get('syr_position'))
        if key in substitutions:
            r = copy.copy(r)
            r['syr_lemma'] = substitutions[key]['lemma']
            r['syr_source'] = 'witness'
            if substitutions[key]['lemma'] is None:
                r['kind'] = 'null'
        out.append(r)
    return out


def occurrences(rows: list[dict], heb_lex: str, books) -> list[dict]:
    sel = [r for r in _select(rows, heb_lex, books) if r['kind'] != 'null']
    return sorted(sel, key=lambda r: (_ref_key(r['ref']), r['heb_node'] or 0))
