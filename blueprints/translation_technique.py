# blueprints/translation_technique.py
"""Translation technique workbench: Hebrew lexeme → Syriac renderings, computed from data/tt/.

No model is called here. Every number comes from translation_technique.tables.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request

import state
from biblical_core.rate_limit import limiter
from translation_technique.lemmas import read_jsonl, write_jsonl
from translation_technique.tables import (
    FACETS, apply_witness, crosstab, distribution, model_share, occurrences,
)

tt_bp = Blueprint('translation_technique', __name__)

GATE_HASH = '7062b83b59f40eec7869d77246c095a2f019123acd53e2d83d99433631bb02b6'


def _store():
    if state.tt is None:
        abort(503)
    return state.tt


def _lang() -> str:
    lang = request.args.get('lang', 'en')
    return lang if lang in ('en', 'es') else 'en'


def _books_arg() -> list[str] | None:
    raw = request.args.get('books', '').strip()
    return [b for b in raw.split(',') if b] or None


def _rows_for(store, books, witness):
    rows = store.rows(books)
    if witness:
        rows = apply_witness(rows, store.witness_substitutions(witness))
    return rows


# ── pages ───────────────────────────────────────────────────────────────────

@tt_bp.route('/translation-technique')
def tt_page():
    lang = _lang()
    store = _store()
    return render_template('translation_technique.html', lang=lang, gate_hash=GATE_HASH,
                           available=store.available, books=store.books, facets=FACETS,
                           sigla=store.witness_sigla())


@tt_bp.route('/translation-technique/verse/<path:ref>')
def tt_verse(ref: str):
    lang = _lang()
    store = _store()
    rows = store.verse_rows(ref)
    if not rows:
        abort(404)
    heb = [r for r in rows if r['heb_node'] is not None]
    heb.sort(key=lambda r: r['heb_node'])
    syr_only = [r for r in rows if r['heb_node'] is None]
    syr_text = ''
    if state.corpus is not None:
        try:
            syr_text = state.corpus.get_verse_text(ref, 'PESH')
        except Exception:
            syr_text = ''
    return render_template('tt_verse.html', lang=lang, ref=ref, rows=heb, syr_only=syr_only, syr_text=syr_text,
                           manifest=store.manifest)


# ── JSON endpoints (not gated) ──────────────────────────────────────────────

@tt_bp.route('/api/tt/meta')
@limiter.limit('60/minute;1000/day')
def tt_meta():
    store = _store()
    return jsonify({
        'available': store.available, 'version': store.version, 'manifest': store.manifest,
        'books': store.books, 'coverage': store.coverage, 'eval': store.eval,
        'sigla': store.witness_sigla(), 'facets': FACETS,
    })


@tt_bp.route('/api/tt/lexemes')
@limiter.limit('60/minute;1000/day')
def tt_lexemes():
    store = _store()
    return jsonify(store.lexemes(request.args.get('q', ''), _books_arg()))


@tt_bp.route('/api/tt/table')
@limiter.limit('60/minute;1000/day')
def tt_table():
    store = _store()
    lex = request.args.get('lex', '').strip()
    if not lex:
        return jsonify({'error': 'lex is required'}), 400
    facet = request.args.get('facet', '').strip() or None
    if facet and (facet not in FACETS or not FACETS[facet]['available']):
        return jsonify({'error': f'facet not available: {facet}'}), 400
    witness = request.args.get('witness', '').strip() or None
    books = _books_arg()
    rows = _rows_for(store, books, witness)
    sel = occurrences(rows, lex, books)
    return jsonify({
        'lex': lex, 'books': books or store.books, 'witness': witness,
        'distribution': distribution(rows, lex, books),
        'crosstab': crosstab(rows, lex, facet, books) if facet else None,
        'occurrences': sel,
        'model_share': model_share(sel),
        'witness_notes': store.witness_notes(witness) if witness else [],
        'manifest_hash': store.manifest.get('hash'), 'version': store.version,
    })


@tt_bp.route('/api/tt/occurrences.csv')
@limiter.limit('30/minute;500/day')
def tt_csv():
    store = _store()
    lex = request.args.get('lex', '').strip()
    if not lex:
        return jsonify({'error': 'lex is required'}), 400
    witness = request.args.get('witness', '').strip() or None
    books = _books_arg()
    sel = occurrences(_rows_for(store, books, witness), lex, books)
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', lex)
    buf = io.StringIO()
    def _c(x):
        return re.sub(r'[\r\n]', ' ', str(x))
    buf.write(f"# BibCrit translation technique export; version={store.version}; "
              f"manifest={store.manifest.get('hash')}; lex={_c(lex)}; books={_c(','.join(books or store.books))}; "
              f"witness={_c(witness or 'main')}\n")
    w = csv.writer(buf)
    w.writerow(['ref', 'heb_node', 'heb_lex', 'heb_word', 'heb_gloss', 'vs', 'vt', 'clause_typ', 'obj_function',
                'next_prep', 'syr_position', 'syr_lemma', 'syr_source', 'prob', 'kind', 'link_source'])
    for r in sel:
        f = r.get('heb_feats') or {}
        w.writerow([r['ref'], r['heb_node'], r['heb_lex'], r['heb_word'], r['heb_gloss'], f.get('vs'), f.get('vt'),
                    f.get('clause_typ'), f.get('obj_function'), f.get('next_prep'), r['syr_position'],
                    r['syr_lemma'], r['syr_source'], r['prob'], r['kind'], r['source']])
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="tt_{safe}.csv"'})


# ── gold form (local only: TT_GOLD_EDIT=1) ───────────────────────────────────
def _gold_enabled() -> bool:
    return os.environ.get('TT_GOLD_EDIT') == '1'


def _gold_paths(store):
    return (os.path.join(store.dir, 'gold', 'sample_refs.json'),
            os.path.join(store.dir, 'gold', 'deuteronomy_sample.jsonl'))


@tt_bp.route('/translation-technique/gold')
def tt_gold_index():
    if not _gold_enabled():
        abort(404)
    store = _store()
    sample_path, gold_path = _gold_paths(store)
    refs = json.load(open(sample_path, encoding='utf-8')) if os.path.exists(sample_path) else []
    done = {r['ref'] for r in read_jsonl(gold_path) if r['reader'] == 'jossi'} if os.path.exists(gold_path) else set()
    return render_template('tt_gold.html', refs=refs, done=done, ref=None, rows=None, lang=_lang())


@tt_bp.route('/translation-technique/gold/<path:ref>', methods=['GET', 'POST'])
def tt_gold_edit(ref: str):
    if not _gold_enabled():
        abort(404)
    store = _store()
    sample_path, gold_path = _gold_paths(store)
    rows = store.verse_rows(ref)
    heb = sorted((r for r in rows if r['heb_node'] is not None), key=lambda r: r['heb_node'])
    if not heb:
        abort(404)
    syr = sorted({(r['syr_position'], r['syr_lemma']) for r in rows if r['syr_position'] is not None})
    if request.method == 'POST':
        new = []
        for r in {x['heb_node']: x for x in heb}.values():
            raw = request.form.get(f"node_{r['heb_node']}", '')
            pos = int(raw) if raw.strip() else None
            lemma = next((l for p, l in syr if p == pos), None) if pos else None
            new.append({'ref': ref, 'heb_node': r['heb_node'], 'heb_lex': r['heb_lex'], 'heb_word': r['heb_word'],
                        'heb_gloss': r['heb_gloss'], 'heb_feats': None, 'syr_position': pos, 'syr_lemma': lemma,
                        'syr_source': None, 'kind': 'one-one' if pos else 'null', 'reader': 'jossi', 'agreed': None})
        existing = [g for g in (read_jsonl(gold_path) if os.path.exists(gold_path) else [])
                    if not (g['ref'] == ref and g['reader'] == 'jossi')]
        write_jsonl(gold_path, existing + new)
        return redirect('/translation-technique/gold')
    try:
        syr_text = state.corpus.get_verse_text(ref, 'PESH') if state.corpus is not None else ''
    except Exception:
        syr_text = ''
    return render_template('tt_gold.html', refs=None, done=None, ref=ref, rows=heb, syr=syr, syr_text=syr_text,
                           lang=_lang())
