# translation_technique/adjudicate.py
"""Model annotation: prompts, strict parsing, merging. No network here; the client is injected."""
from __future__ import annotations

import json
import re
from typing import Protocol

SEDRA_POS = {'verb', 'noun', 'adjective', 'pronoun', 'particle', 'preposition', 'adverb', 'numeral',
             'conjunction', 'interjection', 'proper noun', 'adjective of place'}
_SYRIAC = re.compile(r'[ܐ-ܯ]+')


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class AnnotatorClient(Protocol):
    def complete(self, prompt: str) -> tuple[str, str]: ...  # (text, stop_reason)


class AnthropicAnnotator:
    def __init__(self, model_id: str) -> None:
        import anthropic
        self.model_id = model_id
        self._client = anthropic.Anthropic()

    def complete(self, prompt: str) -> tuple[str, str]:
        msg = self._client.messages.create(model=self.model_id, max_tokens=16000,
                                           messages=[{'role': 'user', 'content': prompt}])
        text = ''.join(b.text for b in msg.content if getattr(b, 'type', '') == 'text')
        return text, msg.stop_reason or ''


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
        if not isinstance(norm, str) or norm not in allowed or not isinstance(lemma, str) or not _SYRIAC.fullmatch(lemma):
            continue
        if not isinstance(pos, str) or pos not in SEDRA_POS or not _is_num(conf) or not 0 <= conf <= 1:
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
        ref, node, pos = it.get('ref'), it.get('heb_node'), it.get('syr_position')
        if not isinstance(ref, str) or not _is_int(node):
            continue
        key = (ref, node)
        if key not in valid:
            continue
        if pos is not None and not (_is_int(pos) and pos in valid[key]):
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


def recompute_kinds(rows: list[dict]) -> None:
    """Set one-one / one-many / many-one on every linked row (syr_position and heb_node both set),
    counting links per heb_node and per syr_position within each verse. Same convention as align._kind."""
    by_ref: dict = {}
    for r in rows:
        if r['heb_node'] is not None and r['syr_position'] is not None:
            by_ref.setdefault(r['ref'], []).append(r)
    for links in by_ref.values():
        per_h: dict = {}
        per_s: dict = {}
        for r in links:
            per_h[r['heb_node']] = per_h.get(r['heb_node'], 0) + 1
            per_s[r['syr_position']] = per_s.get(r['syr_position'], 0) + 1
        for r in links:
            r['kind'] = ('one-many' if per_h[r['heb_node']] > 1
                         else 'many-one' if per_s[r['syr_position']] > 1 else 'one-one')


def restore_orphans(rows: list[dict], lemma_lookup: dict, positions_by_ref: dict) -> int:
    """Add a null row (heb_node None, source ibm1) for every Syriac position of the given verses that no
    row references any more. Rows stay grouped by verse. Returns the number of rows added."""
    seen: dict = {}
    for r in rows:
        if r['syr_position'] is not None:
            seen.setdefault(r['ref'], set()).add(r['syr_position'])
    added = []
    for ref, positions in positions_by_ref.items():
        for pos in sorted(positions - seen.get(ref, set())):
            lemma, src = lemma_lookup.get((ref, pos), (None, None))
            added.append({'ref': ref, 'heb_node': None, 'heb_lex': None, 'heb_word': None, 'heb_gloss': None,
                          'heb_feats': None, 'syr_position': pos, 'syr_lemma': lemma, 'syr_source': src,
                          'prob': 0.0, 'kind': 'null', 'source': 'ibm1'})
    if added:
        rows.extend(added)
        order: dict = {}
        for r in rows:
            order.setdefault(r['ref'], len(order))
        rows.sort(key=lambda r: order[r['ref']])  # stable: keeps in-verse order, orphans last in their verse
    return len(added)


def merge_link_annotations(rows: list[dict], accepted: list[dict], lemma_lookup: dict) -> int:
    """Per accepted (ref, heb_node): replace the first ibm1 row, drop other ibm1 rows for the key.
    Model rows are never touched. Model links carry prob None (no probability). Afterwards, per touched
    verse: Syriac tokens left unreferenced get a null row back and kinds are recomputed.
    Returns the number of keys merged."""
    by_key = {(a['ref'], a['heb_node']): a for a in accepted}
    done: set = set()
    drop: list[int] = []
    for idx, r in enumerate(rows):
        key = (r['ref'], r['heb_node'])
        if r['heb_node'] is None or key not in by_key or r['source'] != 'ibm1':
            continue
        if key in done:
            drop.append(idx)
            continue
        done.add(key)
        pos = by_key[key]['syr_position']
        r['source'] = 'model'
        if pos is None:
            r.update(syr_position=None, syr_lemma=None, syr_source=None, prob=0.0, kind='null')
        else:
            lemma, src = lemma_lookup.get((r['ref'], pos), (None, None))
            r.update(syr_position=pos, syr_lemma=lemma, syr_source=src, prob=None, kind='one-one')
    for idx in reversed(drop):
        del rows[idx]
    touched = {k[0] for k in done}
    if touched:
        positions: dict = {}
        for (ref, pos) in lemma_lookup:
            if ref in touched:
                positions.setdefault(ref, set()).add(pos)
        restore_orphans(rows, lemma_lookup, positions)
        recompute_kinds([r for r in rows if r['ref'] in touched])
    return len(done)
