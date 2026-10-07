# translation_technique/gold.py
"""Gold sample selection and aligner evaluation. Pure functions."""
from __future__ import annotations

import random
from collections import defaultdict


def _cv(ref: str) -> tuple[int, int]:
    ch, v = ref.rsplit(' ', 1)[1].split(':')
    return int(ch), int(v)


def select_sample(refs: list[str], n: int = 200, seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    by_ch: dict[int, list[str]] = defaultdict(list)
    for r in refs:
        by_ch[_cv(r)[0]].append(r)
    pools = {c: rng.sample(v, len(v)) for c, v in by_ch.items()}
    chosen: list[str] = []
    while len(chosen) < n and any(pools.values()):
        order = sorted(pools)
        rng.shuffle(order)
        for c in order:
            if pools[c] and len(chosen) < n:
                chosen.append(pools[c].pop())
    return sorted(chosen, key=_cv)


def _links(rows, reader):
    return {(r['ref'], r['heb_node'], r['syr_position']) for r in rows if r['reader'] == reader}


def agreement(gold_rows: list[dict]) -> dict:
    j, m = _links(gold_rows, 'jossi'), _links(gold_rows, 'model')
    agreed = j & m
    return {'verses': len({r['ref'] for r in gold_rows}), 'links_jossi': len(j), 'links_model': len(m),
            'agreed': len(agreed), 'agreement': len(agreed) / len(j) if j else 0.0}


def mark_agreed(gold_rows: list[dict]) -> list[dict]:
    j, m = _links(gold_rows, 'jossi'), _links(gold_rows, 'model')
    both = j & m
    out = []
    for r in gold_rows:
        r = dict(r)
        r['agreed'] = (r['ref'], r['heb_node'], r['syr_position']) in both
        out.append(r)
    return out


def precision_recall(align_rows: list[dict], gold_rows: list[dict]) -> dict:
    gold_nodes = {(r['ref'], r['heb_node']) for r in gold_rows if r['agreed'] and r['reader'] == 'jossi'}
    gold_links = {(r['ref'], r['heb_node'], r['syr_position']) for r in gold_rows
                  if r['agreed'] and r['reader'] == 'jossi' and r['syr_position'] is not None}
    pred_links = {(r['ref'], r['heb_node'], r['syr_position']) for r in align_rows
                  if r.get('kind') != 'null' and (r['ref'], r['heb_node']) in gold_nodes}
    tp = len(gold_links & pred_links)
    return {'precision': tp / len(pred_links) if pred_links else 0.0,
            'recall': tp / len(gold_links) if gold_links else 0.0,
            'n_gold': len(gold_links), 'n_pred': len(pred_links)}
