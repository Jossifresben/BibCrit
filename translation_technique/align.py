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


# ── IBM Model 1 with a diagonal prior ────────────────────────────────────────

NULL = '<null>'
SMOOTH = 0.5


def _diag(i: int, I: int, j: int, J: int, lam: float) -> float:
    return math.exp(-lam * abs(i / max(I, 1) - j / max(J, 1)))


def train_ibm1(pairs: list[tuple[list[list[str]], list[list[str]]]], iterations: int = 5,
               diag_lambda: float = 4.0) -> dict[str, dict[str, float]]:
    """t[target_unit][source_unit]. Each token may carry several alternative units.

    Source side gets a NULL word. Alternative units of one token split the
    token's expected count equally in the E-step; the diagonal prior favours
    links near the same relative position.
    """
    t: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(lambda: 1.0))
    for _ in range(iterations):
        count: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        total: dict[str, float] = defaultdict(float)
        for src, tgt in pairs:
            srcs = [[NULL]] + src
            I, J = len(srcs) - 1, len(tgt)
            for j, tunits in enumerate(tgt):
                share = 1.0 / len(tunits)
                for tu in tunits:
                    z = 0.0
                    probs = []
                    for i, sunits in enumerate(srcs):
                        prior = 0.2 if i == 0 else _diag(i - 1, I, j, J, diag_lambda)
                        for su in sunits:
                            p = t[tu][su] * prior / len(sunits)
                            probs.append((su, p))
                            z += p
                    if z == 0:
                        continue
                    for su, p in probs:
                        c = share * p / z
                        count[tu][su] += c
                        total[su] += c
        t = defaultdict(lambda: defaultdict(lambda: 1e-6))
        for tu, row in count.items():
            for su, c in row.items():
                t[tu][su] = c / (total[su] + SMOOTH) if total[su] else 0.0  # damps rare-source 'garbage collector' links
    return t


def _viterbi_links(t, src: list[list[str]], tgt: list[list[str]], lam: float) -> list[tuple[int, int, float]]:
    """Best source index per target token (or none), with normalized prob."""
    links = []
    srcs = [[NULL]] + src
    I, J = len(srcs) - 1, len(tgt)
    for j, tunits in enumerate(tgt):
        best, bestp, z = None, 0.0, 0.0
        for i, sunits in enumerate(srcs):
            prior = 0.2 if i == 0 else _diag(i - 1, I, j, J, lam)
            p = sum(t[tu][su] for tu in tunits for su in sunits) * prior / (len(sunits) * len(tunits))
            z += p
            if p > bestp:
                best, bestp = i, p
        if best and z > 0:
            links.append((best - 1, j, bestp / z))
    return links


def symmetrize(fwd: list[list[tuple[int, int, float]]],
               bwd: list[list[tuple[int, int, float]]]) -> list[list[tuple[int, int, float]]]:
    """Intersection, then grow-diag: add union links adjacent (incl. diagonal) to an accepted link."""
    out = []
    for f, b in zip(fwd, bwd):
        fp = {(h, s): p for h, s, p in f}
        bp = {(h, s): p for h, s, p in b}
        inter = {k: (fp[k] + bp[k]) / 2 for k in fp.keys() & bp.keys()}
        union = {k: fp.get(k, bp.get(k)) for k in fp.keys() | bp.keys()}
        accepted = dict(inter)
        grown = True
        while grown:
            grown = False
            for (h, s), p in union.items():
                if (h, s) in accepted:
                    continue
                if any((h + dh, s + ds) in accepted for dh in (-1, 0, 1) for ds in (-1, 0, 1)):
                    linked_h = any(hh == h for hh, _ in accepted)
                    linked_s = any(ss == s for _, ss in accepted)
                    if not linked_h and not linked_s:
                        accepted[(h, s)] = p
                        grown = True
        out.append(sorted((h, s, p) for (h, s), p in accepted.items()))
    return out


def _kind(h: int, s: int, links) -> str:
    hs = sum(1 for hh, ss, _ in links if hh == h)
    ss_ = sum(1 for hh, ss, _ in links if ss == s)
    if hs > 1:
        return 'one-many'
    if ss_ > 1:
        return 'many-one'
    return 'one-one'


def align_corpus(parallel: list[dict], iterations: int = 5, diag_lambda: float = 4.0) -> tuple[list[dict], dict]:
    heb_pairs = [([[h['lex']] for h in p['heb']], [s['units'] for s in p['syr']]) for p in parallel]
    t_hs = train_ibm1(heb_pairs, iterations, diag_lambda)               # P(syr | heb)
    t_sh = train_ibm1([(b, a) for a, b in heb_pairs], iterations, diag_lambda)  # P(heb | syr)
    fwd, bwd = [], []
    for src, tgt in heb_pairs:
        fwd.append([(h, s, p) for h, s, p in _viterbi_links(t_hs, src, tgt, diag_lambda)])
        bwd.append([(h, s, p) for s, h, p in _viterbi_links(t_sh, tgt, src, diag_lambda)])
    sym = symmetrize(fwd, bwd)
    rows, dis = [], {}
    for p, links in zip(parallel, sym):
        linked_h, linked_s = set(), set()
        for h, s, prob in links:
            hw, sw = p['heb'][h], p['syr'][s]
            lemma, pos = sw['lemma'], None
            if lemma is None and sw['candidates']:
                # choose the candidate the Hebrew lex supports most
                best = max(sw['candidates'], key=lambda c: t_hs[unit_key(c)][hw['lex']])
                z = sum(t_hs[unit_key(c)][hw['lex']] for c in sw['candidates'])
                post = t_hs[unit_key(best)][hw['lex']] / z if z else 1.0 / len(sw['candidates'])
                lemma, pos = best['lemma'], best['pos']
                dis[(p['ref'], sw['position'])] = (lemma, pos, round(post, 4))
            elif lemma is not None and '|' in lemma:
                lemma = lemma.split('|')[0]
            rows.append({
                'ref': p['ref'], 'heb_node': hw['node'], 'heb_lex': hw['lex'], 'heb_word': hw['word'],
                'heb_gloss': hw['gloss'], 'heb_feats': hw['feats'],
                'syr_position': sw['position'], 'syr_lemma': lemma, 'syr_source': sw['source'],
                'prob': round(prob, 4), 'kind': _kind(h, s, links), 'source': 'ibm1',
            })
            linked_h.add(h); linked_s.add(s)
        for h, hw in enumerate(p['heb']):
            if h not in linked_h:
                rows.append({'ref': p['ref'], 'heb_node': hw['node'], 'heb_lex': hw['lex'], 'heb_word': hw['word'],
                             'heb_gloss': hw['gloss'], 'heb_feats': hw['feats'], 'syr_position': None,
                             'syr_lemma': None, 'syr_source': None, 'prob': 0.0, 'kind': 'null', 'source': 'ibm1'})
        for s, sw in enumerate(p['syr']):
            if s not in linked_s:
                lemma = sw['lemma'].split('|')[0] if sw['lemma'] else (sw['candidates'][0]['lemma'] if sw['candidates'] else sw['form'])
                rows.append({'ref': p['ref'], 'heb_node': None, 'heb_lex': None, 'heb_word': None, 'heb_gloss': None,
                             'heb_feats': None, 'syr_position': sw['position'], 'syr_lemma': lemma,
                             'syr_source': sw['source'], 'prob': 0.0, 'kind': 'null', 'source': 'ibm1'})
    return rows, dis


def pending_links(rows: list[dict], threshold: float) -> list[dict]:
    return [r for r in rows if r['kind'] != 'null' and r['prob'] < threshold]
