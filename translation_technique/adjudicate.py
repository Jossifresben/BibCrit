# translation_technique/adjudicate.py
"""Model annotation: prompts, strict parsing, merging. No network here; the client is injected."""
from __future__ import annotations

import json
import re
from typing import Protocol

SEDRA_POS = {'verb', 'noun', 'adjective', 'pronoun', 'particle', 'preposition', 'adverb', 'numeral',
             'conjunction', 'interjection', 'proper noun', 'adjective of place'}
_SYRIAC = re.compile(r'^[ܐ-ܯ]+$')


class AnnotatorClient(Protocol):
    def complete(self, prompt: str) -> str: ...


class AnthropicAnnotator:
    def __init__(self, model_id: str) -> None:
        import anthropic
        self.model_id = model_id
        self._client = anthropic.Anthropic()

    def complete(self, prompt: str) -> str:
        msg = self._client.messages.create(model=self.model_id, max_tokens=4096,
                                           messages=[{'role': 'user', 'content': prompt}])
        return ''.join(b.text for b in msg.content if getattr(b, 'type', '') == 'text')


def _extract_json(text: str):
    text = text.strip()
    m = re.search(r'```(?:json)?\s*(.*?)```', text, re.S)
    if m:
        text = m.group(1)
    try:
        return json.loads(text)
    except ValueError:
        return None


def lemma_prompt(batch: list[dict]) -> str:
    items = '\n'.join(f"- form: {b['norm']} | ref: {b['ref']} | verse: {b['verse_text']}" for b in batch)
    return (
        'You are annotating Classical Syriac (Peshitta Old Testament) word forms that the SEDRA IV lexicon '
        'did not resolve. For each form give the dictionary lemma in Syriac script (verbs: the 3ms peal '
        'perfect root; nouns: the emphatic state), the part of speech from this set: '
        + ', '.join(sorted(SEDRA_POS)) +
        ', and your confidence from 0 to 1. If you cannot determine the lemma, omit the item.\n'
        'Answer with a JSON array only, items shaped {"norm": "...", "lemma": "...", "pos": "...", "confidence": 0.0}.\n\n'
        + items
    )


def parse_lemma_response(text: str, batch: list[dict]) -> list[dict]:
    data = _extract_json(text)
    if not isinstance(data, list):
        return []
    allowed = {b['norm'] for b in batch}
    out = []
    for it in data:
        if not isinstance(it, dict):
            continue
        norm, lemma, pos, conf = it.get('norm'), it.get('lemma'), it.get('pos'), it.get('confidence')
        if norm not in allowed or not isinstance(lemma, str) or not _SYRIAC.match(lemma):
            continue
        if pos not in SEDRA_POS or not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            continue
        out.append({'norm': norm, 'lemma': lemma, 'pos': pos, 'confidence': float(conf)})
    return out


def link_prompt(batch: list[dict]) -> str:
    items = []
    for b in batch:
        toks = ' '.join(f"[{t['position']}] {t['form']}" for t in b['syr_tokens'])
        items.append(f"- ref: {b['ref']} | heb_node: {b['heb_node']} | hebrew: {b['heb_word']} ({b['heb_lex']}, "
                     f"'{b['heb_gloss']}') | syriac tokens: {toks}")
    return (
        'For each Hebrew word below, name the position of the Peshitta token that renders it in the same verse, '
        'or null if nothing renders it. Use only the numbered positions shown. Do not explain.\n'
        'Answer with a JSON array only, items shaped {"ref": "...", "heb_node": 0, "syr_position": 0 or null}.\n\n'
        + '\n'.join(items)
    )


def parse_link_response(text: str, batch: list[dict]) -> list[dict]:
    data = _extract_json(text)
    if not isinstance(data, list):
        return []
    valid = {(b['ref'], b['heb_node']): {t['position'] for t in b['syr_tokens']} for b in batch}
    out = []
    for it in data:
        if not isinstance(it, dict):
            continue
        key = (it.get('ref'), it.get('heb_node'))
        if key not in valid:
            continue
        pos = it.get('syr_position')
        if pos is not None and pos not in valid[key]:
            continue
        out.append({'ref': key[0], 'heb_node': key[1], 'syr_position': pos})
    return out


def merge_lemma_annotations(rows: list[dict], accepted: list[dict]) -> int:
    by_norm = {a['norm']: a for a in accepted}
    n = 0
    for r in rows:
        if r['source'] == 'unresolved' and r['norm'] in by_norm:
            a = by_norm[r['norm']]
            r['lemma'], r['pos'], r['source'], r['confidence'] = a['lemma'], a['pos'], 'model', a['confidence']
            n += 1
    return n


def merge_link_annotations(rows: list[dict], accepted: list[dict], lemma_lookup: dict) -> int:
    by_key = {(a['ref'], a['heb_node']): a for a in accepted}
    n = 0
    for r in rows:
        key = (r['ref'], r['heb_node'])
        if r['heb_node'] is None or key not in by_key:
            continue
        pos = by_key[key]['syr_position']
        r['source'] = 'model'
        if pos is None:
            r.update(syr_position=None, syr_lemma=None, syr_source=None, prob=0.0, kind='null')
        else:
            lemma, src = lemma_lookup.get((r['ref'], pos), (None, None))
            r.update(syr_position=pos, syr_lemma=lemma, syr_source=src, prob=1.0, kind='one-one')
        n += 1
    return n
