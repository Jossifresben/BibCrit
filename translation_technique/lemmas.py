"""Syriac lemma layer: normalization, affix rules, SEDRA cache, lemma rows.

No Flask here. Network access only through an injected fetcher.
"""
from __future__ import annotations

import json
import os
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
