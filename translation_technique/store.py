"""Lazy, read-only access to data/tt/ for the blueprint. No Text-Fabric, no model."""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Optional

from translation_technique.tables import BOOK_ORDER
from translation_technique.witnesses import load_witnesses, sigla, substitutions_for


_POINTS = re.compile(r'[֑-ׇ]')


def _strip_points(text: str) -> str:
    """Remove Hebrew vowel points and accents so unpointed input matches pointed lexeme forms."""
    return _POINTS.sub('', text)


_HEB_TO_BHSA = {'א': '>', 'ב': 'B', 'ג': 'G', 'ד': 'D', 'ה': 'H', 'ו': 'W', 'ז': 'Z', 'ח': 'X', 'ט': 'V',
                'י': 'J', 'כ': 'K', 'ך': 'K', 'ל': 'L', 'מ': 'M', 'ם': 'M', 'נ': 'N', 'ן': 'N', 'ס': 'S',
                'ע': '<', 'פ': 'P', 'ף': 'P', 'צ': 'Y', 'ץ': 'Y', 'ק': 'Q', 'ר': 'R', 'ש': 'C', 'ת': 'T'}


def _lex_stem(text: str) -> str:
    """Upper-case BHSA stem of a typed query or a lex id: Hebrew letters transliterated, [ / = suffix dropped."""
    t = _strip_points(text.strip())
    t = ''.join(_HEB_TO_BHSA.get(c, c) for c in t).upper()
    return re.sub(r'[\[/=]+$', '', t)


def _read_compact(path: str) -> list[dict]:
    """Read an align JSONL file into rows that are cheap to hold for the life of the process.

    The Render instance has 512 MB. json.loads gives every row its own copy of each
    repeated string and its own heb_feats dict; interning the strings and sharing
    identical heb_feats dicts (Deuteronomy: 22,330 rows, 2,518 distinct feature sets)
    keeps the same data in about half the memory. Rows are compacted one line at a
    time so the uncompacted file is never held whole. Rows are read-only here;
    callers that change a row copy it first (tables.apply_witness), and none
    mutate heb_feats.
    """
    feats: dict = {}
    rows: list[dict] = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            for k, v in r.items():
                if type(v) is str:
                    r[k] = sys.intern(v)
            f = r.get('heb_feats')
            if isinstance(f, dict):
                key = tuple(sorted(f.items()))
                shared = feats.get(key)
                if shared is None:
                    shared = feats[key] = {sys.intern(k): sys.intern(v) if type(v) is str else v
                                           for k, v in f.items()}
                r['heb_feats'] = shared
            rows.append(r)
    return rows


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
            self._book_cache[stem] = _read_compact(p) if os.path.exists(p) else []
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
        raw_q = (q or '').strip()
        q = _strip_points(raw_q.lower())
        stem = _lex_stem(raw_q) if raw_q else ''
        bset = None if books is None else set(books)
        out = []
        for lex, e in self._lexemes.items():
            hay = _strip_points(f"{lex} {e.get('word', '')} {e.get('gloss', '')}".lower())
            exact = bool(stem) and _lex_stem(lex) == stem
            if q and q not in hay and not exact:
                continue
            count = sum(c for b, c in e.get('books', {}).items() if bset is None or b in bset)
            if count:
                out.append({'lex': lex, 'gloss': e.get('gloss', ''), 'word': e.get('word', ''), 'count': count,
                            '_exact': exact})
        out.sort(key=lambda x: (not x['_exact'], -x['count']))
        for x in out:
            del x['_exact']
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
