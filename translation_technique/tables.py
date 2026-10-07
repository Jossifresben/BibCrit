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
    # A substitution carrying heb_lex links that verse's null Hebrew row for that lex to the substituted Syriac
    # token and removes the Syriac-only null row at that position. Only substitutions that actually find such a
    # null Hebrew row (and whose Syriac-only row exists) take this path; every other one falls back to plain
    # lemma substitution on the row at that position, so a Syriac token is never lost.
    def _is_null_heb(r, ref, lex):
        return r['ref'] == ref and r.get('heb_node') is not None and r['kind'] == 'null' and r.get('heb_lex') == lex

    def _is_syr_only(r, ref, pos):
        return r['ref'] == ref and r.get('heb_node') is None and r.get('syr_position') == pos

    linked = {}      # (ref, heb_lex) -> (pos, sub)
    for (ref, pos), sub in substitutions.items():
        lex = sub.get('heb_lex')
        if lex and sub['lemma'] is not None and (ref, lex) not in linked \
                and any(_is_null_heb(r, ref, lex) for r in rows) and any(_is_syr_only(r, ref, pos) for r in rows):
            linked[(ref, lex)] = (pos, sub)
    drop = {(ref, pos) for (ref, _), (pos, _s) in linked.items()}
    done, out = set(), []
    for r in rows:
        if r.get('heb_node') is None and (r['ref'], r.get('syr_position')) in drop:
            continue
        lk = linked.get((r['ref'], r.get('heb_lex')))
        if lk and _is_null_heb(r, r['ref'], r['heb_lex']) and (r['ref'], r['heb_lex']) not in done:
            pos, sub = lk
            done.add((r['ref'], r['heb_lex']))
            r = copy.copy(r)
            r.update({'kind': 'one-one', 'syr_position': pos, 'syr_lemma': sub['lemma'], 'source': 'witness',
                      'syr_source': 'witness', 'prob': 1.0})
            out.append(r)
            continue
        key = (r['ref'], r.get('syr_position'))
        sub = substitutions.get(key)
        if sub is not None and not ((key in drop)):
            r = copy.copy(r)
            r['syr_lemma'] = sub['lemma']
            r['syr_source'] = 'witness'
            if sub['lemma'] is None:
                r['kind'] = 'null'
        out.append(r)
    return out


def occurrences(rows: list[dict], heb_lex: str, books) -> list[dict]:
    sel = [r for r in _select(rows, heb_lex, books) if r['kind'] != 'null']
    return sorted(sel, key=lambda r: (_ref_key(r['ref']), r['heb_node'] or 0))


MIN_SUMMARY_N = 5


def p_text(p: float) -> str:
    """One p-value format for the findings and the client line: '< 0.001' or three decimals."""
    return '< 0.001' if p < 0.001 else f'{p:.3f}'


def summary(rows: list[dict], heb_lex: str, books) -> dict:
    """Structured, deterministic facts about one lexeme's table; the caller phrases them. No causal claims."""
    dist = distribution(rows, heb_lex, books)
    n = dist['total'] - dist['null_count']
    out = {'lex': heb_lex, 'n': n, 'too_few': n < MIN_SUMMARY_N, 'null_count': dist['null_count'],
           'total': dist['total'], 'model_share': dist['model_share_total']}
    if out['too_few']:
        return out
    top = dist['items'][0]
    out['dominant'] = {'lemma': top['syr_lemma'], 'count': top['count'], 'share': top['count'] / n}
    out['distinct'] = len(dist['items'])
    out['singletons'] = sum(1 for i in dist['items'] if i['count'] == 1)
    best = None
    for fid, spec in FACETS.items():
        if not spec['available']:
            continue
        x = crosstab(rows, heb_lex, fid, books)
        if x['unreliable'] or x['dof'] < 1:
            continue
        if best is None or x['cramers_v'] > best['v']:
            best = {'facet': fid, 'v': x['cramers_v'], 'p': x['p']}
    out['facet'] = best
    return out
