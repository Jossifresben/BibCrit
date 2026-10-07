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
        self._book_cache: dict[str, list[dict]] = {}
        self._rows_cache: dict[Optional[tuple[str, ...]], list[dict]] = {}
        self._lexemes: Optional[dict] = None
        self._witnesses: Optional[list[dict]] = None
        self._manifest: Optional[dict] = None

    # ── metadata ──
    @property
    def available(self) -> bool:
        return os.path.exists(os.path.join(self.dir, 'align', 'manifest.json'))

    @property
    def manifest(self) -> dict:
        p = os.path.join(self.dir, 'align', 'manifest.json')
        if os.path.exists(p):
            if self._manifest is None:
                with open(p, encoding='utf-8') as f:
                    self._manifest = json.load(f)
            return self._manifest
        return {}

    @property
    def version(self) -> str:
        p = os.path.join(self.dir, 'VERSION')
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return f.read().strip()
        return self.manifest.get('version', '')

    @property
    def coverage(self) -> dict:
        p = os.path.join(self.dir, 'lemmas', 'coverage.json')
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        return {}

    @property
    def eval(self) -> Optional[dict]:
        p = os.path.join(self.dir, 'gold', 'eval.json')
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        return None

    @property
    def books(self) -> list[str]:
        return sorted(self.manifest.get('books', []), key=lambda b: BOOK_ORDER.get(b, 99))

    # ── rows ──
    def _book(self, stem: str) -> list[dict]:
        if stem not in self._book_cache:
            p = os.path.join(self.dir, 'align', f'{stem}.jsonl')
            self._book_cache[stem] = read_jsonl(p) if os.path.exists(p) else []
        return self._book_cache[stem]

    def rows(self, books: Optional[list[str]]) -> list[dict]:
        cache_key = None if books is None else tuple(b for b in books if b in self.books)
        if cache_key not in self._rows_cache:
            stems = list(self.books) if books is None else [b for b in books if b in self.books]
            out: list[dict] = []
            for s in stems:
                out.extend(self._book(s))
            self._rows_cache[cache_key] = out
        return self._rows_cache[cache_key]

    def verse_rows(self, ref: str) -> list[dict]:
        stem = ref.rsplit(' ', 1)[0].lower().replace(' ', '_')
        if stem not in self.books:
            return []
        return [r for r in self._book(stem) if r['ref'] == ref]

    # ── lexemes ──
    def lexemes(self, q: str, books: Optional[list[str]]) -> list[dict]:
        if self._lexemes is None:
            p = os.path.join(self.dir, 'lexemes.json')
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f:
                    self._lexemes = json.load(f)
            else:
                self._lexemes = {}
        q = _strip_points((q or '').strip().lower())
        bset = None if books is None else set(books)
        out = []
        for lex, e in self._lexemes.items():
            hay = _strip_points(f"{lex} {e.get('word', '')} {e.get('gloss', '')}".lower())
            if q and q not in hay:
                continue
            count = sum(c for b, c in e.get('books', {}).items() if bset is None or b in bset)
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
