"""Lazy, read-only access to data/tt/ for the blueprint. No Text-Fabric, no model."""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from translation_technique.lemmas import read_jsonl
from translation_technique.tables import BOOK_ORDER
from translation_technique.witnesses import load_witnesses, sigla, substitutions_for


_POINTS = re.compile(r'[֑-ׇ]')


def _strip_points(text: str) -> str:
    """Remove Hebrew vowel points and accents so unpointed input matches pointed lexeme forms."""
    return _POINTS.sub('', text)


class TTStore:
    def __init__(self, tt_dir: str) -> None:
        self.dir = tt_dir
        self._rows: dict[str, list[dict]] = {}
        self._lexemes: Optional[dict] = None
        self._witnesses: Optional[list[dict]] = None
        self._manifest: Optional[dict] = None

    # ── metadata ──
    @property
    def available(self) -> bool:
        return os.path.exists(os.path.join(self.dir, 'align', 'manifest.json'))

    @property
    def manifest(self) -> dict:
        if self._manifest is None:
            p = os.path.join(self.dir, 'align', 'manifest.json')
            self._manifest = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
        return self._manifest

    @property
    def version(self) -> str:
        p = os.path.join(self.dir, 'VERSION')
        return open(p, encoding='utf-8').read().strip() if os.path.exists(p) else self.manifest.get('version', '')

    @property
    def coverage(self) -> dict:
        p = os.path.join(self.dir, 'lemmas', 'coverage.json')
        return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}

    @property
    def eval(self) -> Optional[dict]:
        p = os.path.join(self.dir, 'gold', 'eval.json')
        return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None

    @property
    def books(self) -> list[str]:
        return sorted(self.manifest.get('books', []), key=lambda b: BOOK_ORDER.get(b, 99))

    # ── rows ──
    def _book(self, stem: str) -> list[dict]:
        if stem not in self._rows:
            p = os.path.join(self.dir, 'align', f'{stem}.jsonl')
            self._rows[stem] = read_jsonl(p) if os.path.exists(p) else []
        return self._rows[stem]

    def rows(self, books: Optional[list[str]]) -> list[dict]:
        stems = [b for b in (books or self.books) if b in self.books]
        out: list[dict] = []
        for s in stems:
            out.extend(self._book(s))
        return out

    def verse_rows(self, ref: str) -> list[dict]:
        stem = ref.rsplit(' ', 1)[0].lower().replace(' ', '_')
        return [r for r in self._book(stem) if r['ref'] == ref]

    # ── lexemes ──
    def lexemes(self, q: str, books: Optional[list[str]]) -> list[dict]:
        if self._lexemes is None:
            p = os.path.join(self.dir, 'lexemes.json')
            self._lexemes = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
        q = _strip_points((q or '').strip().lower())
        bset = set(books) if books else None
        out = []
        for lex, e in self._lexemes.items():
            hay = _strip_points(f"{lex} {e.get('word', '')} {e.get('gloss', '')}".lower())
            if q and q not in hay:
                continue
            count = sum(c for b, c in e['books'].items() if bset is None or b in bset)
            if count:
                out.append({'lex': lex, 'gloss': e.get('gloss', ''), 'word': e.get('word', ''), 'count': count})
        out.sort(key=lambda x: -x['count'])
        return out[:25]

    # ── witnesses ──
    def _wit(self) -> list[dict]:
        if self._witnesses is None:
            wdir = os.path.join(self.dir, 'witnesses')
            rows: list[dict] = []
            if os.path.isdir(wdir):
                for f in sorted(os.listdir(wdir)):
                    if f.endswith('.jsonl'):
                        rows.extend(load_witnesses(os.path.join(wdir, f)))
            self._witnesses = rows
        return self._witnesses

    def witness_sigla(self) -> list[str]:
        return sigla(self._wit())

    def witness_substitutions(self, sig: str) -> dict:
        return substitutions_for(self._wit(), sig)

    def witness_notes(self, sig: str) -> list[dict]:
        return [r for r in self._wit() if r['sigla'] == sig]
