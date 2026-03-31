"""Critical Analysis blueprint — Scribal Tendency Profiler and Numerical Discrepancy Modeler."""

import json
import os
import threading
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from biblical_core.claude_pipeline import (
    SCRIBAL_MODEL, NUMERICAL_MODEL, THEOLOGICAL_MODEL, PATRISTIC_MODEL,
    _SCRIBAL_SAMPLE_REFS
)
import state

critical_bp = Blueprint('critical', __name__)

_SCRIBAL_PROMPT     = 'v1'
_NUMERICAL_PROMPT   = 'v1'
_THEOLOGICAL_PROMPT = 'v1'
_PATRISTIC_PROMPT   = 'v1'

_STEPS = {
    'en': {
        'load_passages':      '📖 Loading sample passages…',
        'checking_cache':     '🔍 Checking analysis cache…',
        'found_cache':        '⚡ Found in cache — loading instantly',
        'found_es':           '⚡ Found in Spanish cache — loading instantly',
        'translating':        '🌐 Translating to Spanish…',
        'scribal_generating': 'Profiling scribal tendencies — this typically takes 60–90s…',
        'num_generating':     'Modeling numerical traditions — this typically takes 30–60s…',
        'theo_generating':    'Analyzing theological revisions — this typically takes 60–90 seconds…',
        'pat_generating':     'Tracing patristic citations — this typically takes 60–90 seconds…',
    },
    'es': {
        'load_passages':      '📖 Cargando pasajes de muestra…',
        'checking_cache':     '🔍 Verificando caché de análisis…',
        'found_cache':        '⚡ Encontrado en caché — cargando al instante',
        'found_es':           '⚡ Encontrado en caché español — cargando al instante',
        'translating':        '🌐 Traduciendo al español…',
        'scribal_generating': 'Perfilando tendencias escribales — esto tarda 60–90 s…',
        'num_generating':     'Modelando tradiciones numéricas — esto tarda 30–60 s…',
        'theo_generating':    'Analizando revisiones teológicas — esto tarda 60–90 segundos…',
        'pat_generating':     'Rastreando citas patrísticas — esto tarda 60–90 segundos…',
    },
}


def _step(lang: str, key: str) -> str:
    return _STEPS.get(lang, _STEPS['en']).get(key, _STEPS['en'].get(key, key))


def _translate_step(pipeline, lang, result, ref_or_book, tool, prompt, model):
    """Translate result to Spanish and cache it. Returns translated result (or original on error)."""
    translated = pipeline.translate_to_spanish(result, tool)
    if not translated.get('error'):
        pipeline.save_cache_es(ref_or_book, tool, prompt, model, translated)
    return translated if not translated.get('error') else result


# ── Page routes ────────────────────────────────────────────────────────────

@critical_bp.route('/scribal')
def scribal():
    lang = request.args.get('lang', 'en')
    book = request.args.get('book', '')
    return render_template('scribal.html', lang=lang, book=book, t=state.t)


@critical_bp.route('/numerical')
def numerical():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('numerical.html', lang=lang, reference=reference, t=state.t)


@critical_bp.route('/theological')
def theological():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('theological.html', lang=lang, reference=reference, t=state.t)


@critical_bp.route('/patristic')
def patristic():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('patristic.html', lang=lang, reference=reference, t=state.t)


# ── SSE streams ────────────────────────────────────────────────────────────

@critical_bp.route('/api/scribal/stream')
def api_scribal_stream():
    """SSE endpoint: streams scribal tendency profiling progress then final result."""
    book = request.args.get('book', '').strip()

    lang = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not book:
            yield event('error', msg='book parameter required')
            return

        pipeline = state.pipeline
        if pipeline is None:
            yield event('error', msg='Server not ready — pipeline not initialized')
            return

        # Spanish fast path: check ES cache before anything else
        if lang == 'es':
            cached_es = pipeline.get_cached_es(book, 'scribal', _SCRIBAL_PROMPT, SCRIBAL_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['book'] = book
                yield event('done', data=cached_es)
                return

        # Step 1: load sample passages from corpus (if available)
        yield event('step', msg=_step(lang, 'load_passages'))
        sample_passages = _build_sample_passages(book)

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(book, 'scribal', _SCRIBAL_PROMPT, SCRIBAL_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            yield event('step', msg=_step(lang, 'scribal_generating'))
            _result_box = [None]
            def _run_scribal():
                _result_box[0] = pipeline.analyze_scribal(book, sample_passages)
            _t = threading.Thread(target=_run_scribal, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0]

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['book'] = book

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_scribal():
                _tr_box[0] = _translate_step(pipeline, lang, result, book,
                                             'scribal', _SCRIBAL_PROMPT, SCRIBAL_MODEL)
            _tt = threading.Thread(target=_run_tr_scribal, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0]

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@critical_bp.route('/api/numerical/stream')
def api_numerical_stream():
    """SSE endpoint: streams numerical discrepancy analysis progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        pipeline = state.pipeline
        if pipeline is None:
            yield event('error', msg='Server not ready — pipeline not initialized')
            return

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'numerical', _NUMERICAL_PROMPT, NUMERICAL_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['reference'] = reference
                yield event('done', data=cached_es)
                return

        # Step 1: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'numerical', _NUMERICAL_PROMPT, NUMERICAL_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            yield event('step', msg=_step(lang, 'num_generating'))
            _result_box = [None]
            def _run_numerical():
                _result_box[0] = pipeline.analyze_numerical(reference)
            _t = threading.Thread(target=_run_numerical, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0]

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['reference'] = reference

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_numerical():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                             'numerical', _NUMERICAL_PROMPT, NUMERICAL_MODEL)
            _tt = threading.Thread(target=_run_tr_numerical, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0]

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# ── Theological SSE stream ─────────────────────────────────────────────────

@critical_bp.route('/api/theological/stream')
def api_theological_stream():
    """SSE endpoint: streams theological revision analysis progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        pipeline = state.pipeline
        if pipeline is None:
            yield event('error', msg='Server not ready — pipeline not initialized')
            return

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'theological', _THEOLOGICAL_PROMPT, THEOLOGICAL_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['scope'] = cached_es.get('scope', reference)
                yield event('done', data=cached_es)
                return

        # Step 1: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'theological', _THEOLOGICAL_PROMPT, THEOLOGICAL_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            yield event('step', msg=_step(lang, 'theo_generating'))
            _result_box = [None]
            def _run_theological():
                _result_box[0] = pipeline.analyze_theological(reference)
            _t = threading.Thread(target=_run_theological, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0]

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['scope'] = result.get('scope', reference)

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_theological():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                             'theological', _THEOLOGICAL_PROMPT, THEOLOGICAL_MODEL)
            _tt = threading.Thread(target=_run_tr_theological, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0]

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# ── Patristic SSE stream ────────────────────────────────────────────────────

@critical_bp.route('/api/patristic/stream')
def api_patristic_stream():
    """SSE endpoint: streams patristic citation analysis progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        pipeline = state.pipeline
        if pipeline is None:
            yield event('error', msg='Server not ready — pipeline not initialized')
            return

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'patristic', _PATRISTIC_PROMPT, PATRISTIC_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['reference'] = cached_es.get('reference', reference)
                yield event('done', data=cached_es)
                return

        # Step 1: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'patristic', _PATRISTIC_PROMPT, PATRISTIC_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            yield event('step', msg=_step(lang, 'pat_generating'))
            _result_box = [None]
            def _run_patristic():
                _result_box[0] = pipeline.analyze_patristic(reference)
            _t = threading.Thread(target=_run_patristic, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0]

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['reference'] = result.get('reference', reference)

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_patristic():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                             'patristic', _PATRISTIC_PROMPT, PATRISTIC_MODEL)
            _tt = threading.Thread(target=_run_tr_patristic, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0]

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# ── Export API ─────────────────────────────────────────────────────────────

@critical_bp.route('/api/scribal/export/sbl')
def export_scribal_sbl():
    """Return SBL-style footnotes for each dimension's examples."""
    book = request.args.get('book', '').strip()
    if not book:
        return jsonify({'error': 'book parameter required'}), 400
    if state.pipeline is None:
        return jsonify({'error': 'Pipeline not initialized'}), 503

    data = state.pipeline.get_cached(book, 'scribal', _SCRIBAL_PROMPT, SCRIBAL_MODEL)
    if not data:
        return jsonify({'error': f'No cached analysis for "{book}". Run the Scribal Profiler first.'}), 404

    footnotes = []
    translator = data.get('translator_name', f'LXX {book}')
    for dim in data.get('dimensions', []):
        dim_name = dim.get('dimension', '').replace('_', ' ').title()
        score    = dim.get('score', 0.0)
        summary  = dim.get('summary', '')
        fn = f'{translator} ({dim_name} score: {score:.2f}): {summary}'
        for ex in dim.get('examples', []):
            ref  = ex.get('reference', '')
            note = ex.get('note', '')
            if ref:
                fn += f' Cf. {ref}: {note}'
        footnotes.append(fn.strip())

    return jsonify({'book': book, 'footnotes': footnotes})


@critical_bp.route('/api/numerical/export/sbl')
def export_numerical_sbl():
    """Stub — numerical export not yet implemented."""
    return jsonify({'error': 'Numerical SBL export not yet implemented'}), 501


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_sample_passages(book: str) -> str:
    """Build a formatted sample passages string for the scribal prompt.

    Tries to pull real text from the corpus; falls back to an empty string
    (Claude can profile from training knowledge alone).
    """
    refs = _SCRIBAL_SAMPLE_REFS.get(book, [])
    if not refs or state.corpus is None:
        return f'(No sample passage text available — profile {book} from your training knowledge)'

    lines = []
    for ref in refs:
        try:
            mt_words  = state.corpus.get_verse_words(ref, 'MT')
            lxx_words = state.corpus.get_verse_words(ref, 'LXX')
            mt_text   = ' '.join(w.word_text for w in mt_words)  if mt_words  else '(not found)'
            lxx_text  = ' '.join(w.word_text for w in lxx_words) if lxx_words else '(not found)'
            lines.append(f'{ref}:\n  MT:  {mt_text}\n  LXX: {lxx_text}')
        except Exception:
            lines.append(f'{ref}: (error loading)')

    return '\n\n'.join(lines) if lines else '(No sample passages loaded)'
