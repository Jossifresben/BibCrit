# translation_technique/witnesses.py
"""Apparatus layer: alternative readings per (ref, position, sigla)."""
from __future__ import annotations

import json
import os

REQUIRED = ('ref', 'position', 'sigla', 'form', 'keyed_from')


def load_witnesses(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding='utf-8') as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            r = json.loads(line)
            missing = [k for k in REQUIRED if not r.get(k)]
            if missing:
                raise ValueError(f'{path}:{n} missing {missing}')
            r.setdefault('lemma', None)
            r.setdefault('note', '')
            r.setdefault('heb_lex', None)   # optional: links the substituted token to this lexeme's null row
            rows.append(r)
    return rows


def sigla(witness_rows: list[dict]) -> list[str]:
    return sorted({r['sigla'] for r in witness_rows})


def substitutions_for(witness_rows: list[dict], sig: str) -> dict:
    return {(r['ref'], int(r['position'])): {'lemma': r['lemma'], 'form': r['form'], 'note': r['note'],
                                             'keyed_from': r['keyed_from'], 'heb_lex': r.get('heb_lex')}
            for r in witness_rows if r['sigla'] == sig}
