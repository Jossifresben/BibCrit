"""Syriac lemma layer: normalization, affix rules, SEDRA cache, lemma rows.

No Flask here. Network access only through an injected fetcher.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import Counter
from typing import Callable, Optional

# Combining marks the ETCBC Peshitta text carries: seyame, dot above,
# dot below, tilde below, macron below.
_DIACRITICS = {'̈', '̇', '̣', '̰', '̱'}


def normalize_form(form: str) -> str:
    """Return the form without seyame and diacritic dots, trimmed."""
    return ''.join(ch for ch in form.strip() if ch not in _DIACRITICS)


# (rule_id, kind, affix). Proclitics in the order the spec fixes; suffixes
# longest first so ܟܘܢ is tried before ܟ.
AFFIX_RULES: list[tuple[str, str, str]] = [
    ('pre_waw', 'pre', 'ܘ'),
    ('pre_dalath', 'pre', 'ܕ'),
    ('pre_lamadh', 'pre', 'ܠ'),
    ('pre_beth', 'pre', 'ܒ'),
    ('suf_kwn', 'suf', 'ܟܘܢ'),
    ('suf_kyn', 'suf', 'ܟܝܢ'),
    ('suf_hwn', 'suf', 'ܗܘܢ'),
    ('suf_hyn', 'suf', 'ܗܝܢ'),
    ('suf_ky', 'suf', 'ܟܝ'),
    ('suf_ny', 'suf', 'ܢܝ'),
    ('suf_h', 'suf', 'ܗ'),
    ('suf_k', 'suf', 'ܟ'),
    ('suf_n', 'suf', 'ܢ'),
    ('suf_y', 'suf', 'ܝ'),
]

_MIN_LEN = 2


def strip_affixes(norm: str) -> list[tuple[str, str]]:
    """Candidate stripped forms, each with the id of the rule that produced it.

    Proclitics are stripped cumulatively in rule order (ܘ, then ܕ off the
    result, …); each intermediate form is a candidate. Suffix rules are then
    applied to every proclitic-stripped candidate and to the input itself.
    Forms shorter than two letters are dropped. Order of the returned list is
    the order of application, so callers can stop at the first SEDRA hit.
    """
    out: list[tuple[str, str]] = []
    stages = [norm]
    current = norm
    for rule_id, kind, affix in AFFIX_RULES:
        if kind != 'pre':
            continue
        if current.startswith(affix) and len(current) - len(affix) >= _MIN_LEN:
            current = current[len(affix):]
            out.append((rule_id, current))
            stages.append(current)
    for base in stages:
        for rule_id, kind, affix in AFFIX_RULES:
            if kind != 'suf':
                continue
            if base.endswith(affix) and len(base) - len(affix) >= _MIN_LEN:
                cand = (rule_id, base[:-len(affix)])
                if cand not in out:
                    out.append(cand)
    return out


SEDRA_URL = 'https://sedra.bethmardutho.org/api/word/{}'


class SedraUnavailable(Exception):
    """SEDRA could not answer (network error or non-404 failure). Never cached."""


def sedra_fetch(norm: str) -> Optional[list[dict]]:
    """Live SEDRA IV lookup. Returns candidate list, None on a true miss
    (HTTP 404 or empty/invalid list); raises SedraUnavailable otherwise."""
    import requests
    try:
        r = requests.get(SEDRA_URL.format(norm), timeout=15)
    except requests.RequestException as exc:
        raise SedraUnavailable(str(exc)) from exc
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise SedraUnavailable(f'HTTP {r.status_code} for {norm}')
    try:
        data = r.json()
    except ValueError:
        return None
    if not isinstance(data, list) or not data:
        return None
    return [{'lemma': e.get('stem'), 'pos': e.get('category') or None, 'kaylo': e.get('kaylo') or None}
            for e in data if e.get('stem')] or None


class SedraCache:
    """JSON cache of SEDRA lookups keyed by normalized form. None = miss.

    Thread-safe: a lock guards the dict and the save; the fetch itself runs
    outside the lock so workers can fetch in parallel.
    """

    def __init__(self, path: str, fetcher: Optional[Callable[[str], Optional[list[dict]]]] = None,
                 delay: float = 0.3, autosave_every: int = 200) -> None:
        self.path = path
        self.fetcher = fetcher
        self.delay = delay
        self.autosave_every = autosave_every
        self._data: dict = {}
        self._dirty = False
        self._since_save = 0
        self._lock = threading.Lock()
        if os.path.exists(path):
            with open(path, encoding='utf-8') as fh:
                self._data = json.load(fh)

    def has(self, norm: str) -> bool:
        with self._lock:
            return norm in self._data

    def get(self, norm: str) -> Optional[list[dict]]:
        with self._lock:
            if norm in self._data:
                return self._data[norm]
        if self.fetcher is None:
            raise KeyError(norm)
        result = self.fetcher(norm)  # SedraUnavailable propagates; nothing stored
        with self._lock:
            self._data[norm] = result
            self._dirty = True
            self._since_save += 1
            if self.autosave_every and self._since_save >= self.autosave_every:
                self._save_locked()
        if self.delay:
            time.sleep(self.delay)
        return result

    def _save_locked(self) -> None:
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=0, sort_keys=True)
        os.replace(tmp, self.path)
        self._dirty = False
        self._since_save = 0

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def stats(self) -> dict:
        with self._lock:
            hits = sum(1 for v in self._data.values() if v)
            return {'hits': hits, 'misses': len(self._data) - hits}


def _dedupe(cands: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in cands:
        key = (c['lemma'], c['pos'], c.get('kaylo'))
        if key not in seen:
            seen.add(key)
            out.append({'lemma': c['lemma'], 'pos': c['pos'], 'kaylo': c.get('kaylo')})
    return out


def _lookup(cache: SedraCache, norm: str) -> Optional[list[dict]]:
    """cache.get, treating an unknown form with no fetcher (offline) as a miss."""
    try:
        return cache.get(norm)
    except KeyError:
        return None


def _resolve(norm: str, cache: SedraCache) -> tuple[str, Optional[str], list[dict]]:
    """Return (source, rule_id, candidates)."""
    cands = _lookup(cache, norm)
    if cands:
        return 'sedra', None, _dedupe(cands)
    for rule_id, stripped in strip_affixes(norm):
        cands = _lookup(cache, stripped)
        if cands:
            return 'rule', rule_id, _dedupe(cands)
    return 'unresolved', None, []


def build_lemma_rows(tokens: list[dict], cache: SedraCache) -> list[dict]:
    rows = []
    for t in tokens:
        form = t['word_text']
        norm = normalize_form(form)
        source, rule_id, cands = _resolve(norm, cache)
        lemma = pos = None
        confidence = 0.0
        if len(cands) == 1:
            lemma, pos, confidence = cands[0]['lemma'], cands[0]['pos'], 1.0
        rows.append({
            'ref': t['reference'],
            'position': int(t['position']),
            'form': form,
            'norm': norm,
            'lemma': lemma,
            'pos': pos,
            'source': source,
            'rule': rule_id,
            'candidates': cands,
            'confidence': confidence,
        })
    return rows


def coverage(rows: list[dict]) -> dict:
    n = len(rows)
    by_tok = Counter(r['source'] for r in rows)
    types: dict[str, str] = {}
    for r in rows:
        types.setdefault(r['norm'], r['source'])
    by_typ = Counter(types.values())
    return {
        'tokens': n,
        'types': len(types),
        'by_source_tokens': {k: v / n for k, v in sorted(by_tok.items())} if n else {},
        'by_source_types': {k: v / len(types) for k, v in sorted(by_typ.items())} if types else {},
    }


def write_jsonl(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')


def read_jsonl(path: str) -> list[dict]:
    with open(path, encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]
