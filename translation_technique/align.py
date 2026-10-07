# translation_technique/align.py
"""Hebrew–Syriac word alignment: parallel corpus, IBM Model 1, symmetrization.

Text-Fabric is imported only inside the functions that need it, so the web
process never pays for it.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Optional

_BOOK_FIX = {'Song of songs': 'Song of Songs'}


def normalize_ref(ref: str) -> str:
    ref = re.sub(r'\s+', ' ', ref.strip())
    for bad, good in _BOOK_FIX.items():
        if ref.startswith(bad + ' '):
            ref = good + ref[len(bad):]
    return ref


def unit_key(cand: dict) -> str:
    """Alignment unit for a SEDRA candidate: lemma, plus pos when present."""
    return f"{cand['lemma']}|{cand['pos']}" if cand.get('pos') else cand['lemma']


def syr_units(row: dict) -> list[str]:
    if row['lemma'] is not None:
        return [row['lemma']]
    if row['candidates']:
        return [unit_key(c) for c in row['candidates']]
    return [row['norm']]


def build_parallel(heb: dict[str, list[dict]], lemma_rows: list[dict]) -> list[dict]:
    by_ref: dict[str, list[dict]] = defaultdict(list)
    for r in lemma_rows:
        by_ref[normalize_ref(r['ref'])].append(r)
    out = []
    for ref, hwords in heb.items():
        ref = normalize_ref(ref)
        if ref not in by_ref:
            continue
        syr = sorted(by_ref[ref], key=lambda r: r['position'])
        out.append({
            'ref': ref,
            'heb': hwords,
            'syr': [{'position': r['position'], 'form': r['form'], 'lemma': r['lemma'],
                     'candidates': r['candidates'], 'source': r['source'], 'units': syr_units(r)}
                    for r in syr],
        })
    return out


# ── Text-Fabric side (build time only) ───────────────────────────────────────

def hebrew_features(api, node: int) -> dict:
    F, L = api.F, api.L
    clause = L.u(node, 'clause')
    clause_typ = F.typ.v(clause[0]) if clause else 'NA'
    obj_function = 'none'
    next_prep = 'none'
    if clause:
        phrases = L.d(clause[0], 'phrase')
        for ph in phrases:
            if F.function.v(ph) == 'Objc':
                obj_function = 'Objc'
                break
        words = L.d(clause[0], 'word')
        after = [w for w in words if w > node]
        for w in after[:3]:
            if F.sp.v(w) == 'prep':
                next_prep = F.lex.v(w)
                break
    return {
        'sp': F.sp.v(node) or 'NA',
        'vs': F.vs.v(node) or 'NA',
        'vt': F.vt.v(node) or 'NA',
        'clause_typ': clause_typ or 'NA',
        'obj_function': obj_function,
        'next_prep': next_prep,
    }


def hebrew_tokens(api, book_stem: str) -> dict[str, list[dict]]:
    """All BHSA words of one book, grouped by normalized reference."""
    F, L, T = api.F, api.L, api.T
    out: dict[str, list[dict]] = {}
    for book_node in F.otype.s('book'):
        raw = T.bookName(book_node)
        if raw.lower() != book_stem:
            continue
        for verse in L.d(book_node, 'verse'):
            b, ch, v = T.sectionFromNode(verse)
            ref = normalize_ref(f"{b.replace('_', ' ')} {ch}:{v}")
            words = []
            for w in L.d(verse, 'word'):
                lexnode = L.u(w, 'lex')
                words.append({
                    'node': w,
                    'lex': F.lex.v(w),
                    'word': F.g_word_utf8.v(w),
                    'gloss': F.gloss.v(lexnode[0]) if lexnode else '',
                    'feats': hebrew_features(api, w),
                })
            out[ref] = words
    return out
