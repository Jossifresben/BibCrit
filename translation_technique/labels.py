# translation_technique/labels.py
"""Full names for BHSA/ETCBC facet codes. Pure, table-driven; English only (grammatical terms)."""
from __future__ import annotations

import re

_NOT_VERB = 'not a verb'

_STEMS = {
    'qal': 'Qal', 'nif': 'Niphal', 'pie': 'Piel', 'pua': 'Pual', 'hit': 'Hitpael', 'hif': 'Hiphil',
    'hof': 'Hophal', 'hsht': 'Hishtaphel', 'pasq': 'Passive qal', 'pass': 'Passive', 'peal': 'Peal',
    'peil': 'Peil', 'pael': 'Pael', 'etpa': 'Etpaal', 'afel': 'Afel', 'etpe': 'Etpeel', 'shaf': 'Shafel',
    'tif': 'Tiphil', 'pol': 'Polel', 'poal': 'Poal', 'polp': 'Polpal', 'htpo': 'Hitpolel', 'htpa': 'Hitpael (Aramaic)',
    'poel': 'Poel', 'hotp': 'Hotpaal',
}

_TENSES = {
    'perf': 'perfect (qatal)', 'impf': 'imperfect (yiqtol)', 'wayq': 'wayyiqtol', 'ptca': 'active participle',
    'ptcp': 'passive participle', 'infc': 'infinitive construct', 'infa': 'infinitive absolute', 'impv': 'imperative',
}

# clause-type tokens, longest/most specific first
_CLAUSE_TOKENS = [
    ('XQtl', 'X-qatal (subject first)'), ('XYqt', 'X-yiqtol (subject first)'),
    ('InfC', 'infinitive construct clause'), ('InfA', 'infinitive absolute clause'),
    ('NmCl', 'nominal clause'), ('Ptcp', 'participial clause'), ('Ellp', 'ellipsis'), ('Voct', 'vocative'),
    ('Reop', 'reopening'), ('MSyn', 'macrosyntactic sign'), ('Defc', 'defective clause'),
    ('Way', 'wayyiqtol'), ('Qt', 'qatal'), ('Yq', 'yiqtol'), ('Im', 'imperative'), ('Pt', 'participle'),
    ('In', 'infinitive'), ('W', 'we-'), ('x', 'fronted element'), ('Z', 'asyndetic'), ('Q', 'qatal'),
]
_ENDINGS = {'X': 'with explicit subject', '0': 'no explicit subject'}

_OBJC = {'Objc': 'has an object phrase', 'none': 'no object phrase'}

_PREPS = {
    'L': 'ל to', '>L': 'אל to, towards', 'B': 'ב in, with', 'K': 'כ like', 'MN': 'מן from', '<D': 'עד up to',
    '<L': 'על on, against', '>T': 'את (object marker / with)', '<M': 'עם with', 'LPNJ': 'לפני before',
    '>XR/': 'אחר after', 'BJN/': 'בין between', 'TXT/': 'תחת under', 'none': 'no preposition',
}


def stem_name(code: str) -> str:
    return _NOT_VERB if code == 'NA' else _STEMS.get(code, code)


def tense_name(code: str) -> str:
    return _NOT_VERB if code == 'NA' else _TENSES.get(code, code)


def clause_type_name(code: str) -> str:
    rest, parts, we = code, [], False
    while rest:
        if len(rest) == 1 and rest in _ENDINGS and parts:
            parts.append(_ENDINGS[rest]); rest = ''; break
        for tok, name in _CLAUSE_TOKENS:
            if rest.startswith(tok):
                rest = rest[len(tok):]
                if tok == 'W':
                    if rest.startswith(('Qt', 'Yq', 'Im', 'Pt', 'In')):
                        we = True
                    else:
                        parts.append('we-')
                else:
                    parts.append(('we-' + name) if we and tok not in ('x', 'Z') else name)
                    if tok not in ('x', 'Z'):
                        we = False
                break
        else:
            return code
    if we:
        parts.append('we-')
    return ', '.join(parts) if parts else code


def objc_name(code: str) -> str:
    return _OBJC.get(code, code)


def prep_name(lex: str) -> str:
    return _PREPS.get(lex, lex)


def facet_value_label(facet_id: str, value: str) -> str:
    fn = {'vs': stem_name, 'vt': tense_name, 'clause_typ': clause_type_name,
          'obj_function': objc_name, 'next_prep': prep_name}.get(facet_id)
    return fn(value) if fn else value
