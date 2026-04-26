"""Critical Analysis blueprint — Scribal Tendency Profiler and Numerical Discrepancy Modeler."""

import json
import os
import time
import threading
from queue import Queue, Empty
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from biblical_core.claude_pipeline import (
    SCRIBAL_MODEL, NUMERICAL_MODEL, THEOLOGICAL_MODEL, PATRISTIC_MODEL,
    _SCRIBAL_SAMPLE_REFS
,
    CACHE_META_KEYS
)
from biblical_core.ref_utils import estimate_verse_count, TOOL_VERSE_LIMITS
import state



def _check_ref_length(reference: str, tool: str) -> str | None:
    """Return an error message string if the passage is too long, else None."""
    max_v = TOOL_VERSE_LIMITS.get(tool)
    if not max_v:
        return None
    est = estimate_verse_count(reference)
    if est > max_v:
        return (
            f'Passage too long (≈{est} verses estimated). '
            f'Please limit to {max_v} verses or fewer for this tool.'
        )

critical_bp = Blueprint('critical', __name__)

# IMPORTANT: These must stay in sync with the prompt_version set inside the
# corresponding pipeline.analyze_*() methods. A mismatch causes cache-key
# divergence — the blueprint generates lookup keys with version X while the
# pipeline stores them with version Y, producing cache misses on every request.
_SCRIBAL_PROMPT     = 'v1'
_NUMERICAL_PROMPT   = 'v3'
_THEOLOGICAL_PROMPT = 'v2'
_PATRISTIC_PROMPT   = 'v3'

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
            for _key, _val in cached.items():
                if _key not in CACHE_META_KEYS:
                    yield event('section', key=_key, data=_val)
                    time.sleep(0.04)
            result = cached
        else:
            yield event('step', msg=_step(lang, 'scribal_generating'))
            q = Queue()

            def _run_scribal():
                try:
                    for key, value in pipeline.stream_scribal(book, sample_passages):
                        if key is None:
                            q.put(('done', None, value))
                            return
                        q.put(('section', key, value))
                    q.put(('done', None, {}))
                except Exception as exc:
                    q.put(('error', None, str(exc)))

            _t = threading.Thread(target=_run_scribal, daemon=True)
            _t.start()

            result = {}
            while True:
                try:
                    item = q.get(timeout=8)
                except Empty:
                    yield ': keepalive\n\n'
                    continue

                evt_type, key, data = item
                if evt_type == 'section':
                    result[key] = data
                    yield event('section', key=key, data=data)
                elif evt_type == 'done':
                    result = data if data else result
                    break
                elif evt_type == 'error':
                    yield event('error', msg=data)
                    return

            if result.get('parse_error'):
                yield event('error', msg='Analysis could not be parsed — please try again')
                return

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
        len_err = _check_ref_length(reference, 'numerical')
        if len_err:
            yield event('error', msg=len_err)
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

        # Step 1: load SP corpus text for Pentateuch passages.
        # The numerical tool uses chapter-level references (e.g. "Genesis 5"),
        # so we aggregate all verse words across the chapter rather than a
        # single-verse lookup which would always return empty.
        sp_text = ''
        if state.corpus is not None:
            try:
                sp_words = state.corpus.get_verse_words(reference, 'SP')
                if not sp_words and ':' not in reference:
                    # Chapter-level reference — aggregate all verses
                    parts = reference.rsplit(' ', 1)
                    if len(parts) == 2:
                        book, chap_str = parts
                        chap = int(chap_str)
                        sp_words = state.corpus.get_chapter_words(book, chap, 'SP')
                sp_text = ' '.join(w.word_text for w in sp_words) if sp_words else ''
            except Exception:
                sp_text = ''

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'numerical', _NUMERICAL_PROMPT, NUMERICAL_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            for _key, _val in cached.items():
                if _key not in CACHE_META_KEYS:
                    yield event('section', key=_key, data=_val)
                    time.sleep(0.04)
            result = cached
        else:
            yield event('step', msg=_step(lang, 'num_generating'))
            q = Queue()

            def _run_numerical():
                try:
                    for key, value in pipeline.stream_numerical(reference, sp_text=sp_text):
                        if key is None:
                            q.put(('done', None, value))
                            return
                        q.put(('section', key, value))
                    q.put(('done', None, {}))
                except Exception as exc:
                    q.put(('error', None, str(exc)))

            _t = threading.Thread(target=_run_numerical, daemon=True)
            _t.start()

            result = {}
            while True:
                try:
                    item = q.get(timeout=8)
                except Empty:
                    yield ': keepalive\n\n'
                    continue

                evt_type, key, data = item
                if evt_type == 'section':
                    result[key] = data
                    yield event('section', key=key, data=data)
                elif evt_type == 'done':
                    result = data if data else result
                    break
                elif evt_type == 'error':
                    yield event('error', msg=data)
                    return

            if result.get('parse_error'):
                yield event('error', msg='Analysis could not be parsed — please try again')
                return

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
        len_err = _check_ref_length(reference, 'theological')
        if len_err:
            yield event('error', msg=len_err)
            return

        pipeline = state.pipeline
        if pipeline is None:
            yield event('error', msg='Server not ready — pipeline not initialized')
            return

        corpus = state.corpus
        vul_words = corpus.get_verse_words(reference, 'VUL') if corpus else None
        vul_text  = ' '.join(w.word_text for w in vul_words) if vul_words else ''

        # Fetch MT and LXX for immediate corpus display
        yield event('step', msg=_step(lang, 'load_verse'))
        mt_words  = corpus.get_verse_words(reference, 'MT')  if corpus else []
        lxx_words = corpus.get_verse_words(reference, 'LXX') if corpus else []
        mt_text   = ' '.join(w.word_text for w in mt_words)  if mt_words  else ''
        lxx_text  = ' '.join(w.word_text for w in lxx_words) if lxx_words else ''

        if mt_text or lxx_text:
            yield event('section', key='_corpus', data={
                'mt_text':  mt_text,
                'lxx_text': lxx_text,
            })

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
            for _key, _val in cached.items():
                if _key not in CACHE_META_KEYS:
                    yield event('section', key=_key, data=_val)
                    time.sleep(0.04)
            result = cached
        else:
            yield event('step', msg=_step(lang, 'theo_generating'))
            q = Queue()

            def _run_theological():
                try:
                    for key, value in pipeline.stream_theological(reference, vul_text):
                        if key is None:
                            # Epilogue: value is the final result dict
                            q.put(('done', None, value))
                            return
                        q.put(('section', key, value))
                    # Generator exhausted without epilogue (should not happen)
                    q.put(('done', None, {}))
                except Exception as exc:
                    q.put(('error', None, str(exc)))

            _t = threading.Thread(target=_run_theological, daemon=True)
            _t.start()

            result = {}
            while True:
                try:
                    item = q.get(timeout=8)
                except Empty:
                    yield ': keepalive\n\n'
                    continue

                evt_type, key, data = item
                if evt_type == 'section':
                    result[key] = data
                    yield event('section', key=key, data=data)
                elif evt_type == 'done':
                    result = data if data else result
                    break
                elif evt_type == 'error':
                    yield event('error', msg=data)
                    return

            if result.get('parse_error'):
                yield event('error', msg='Analysis could not be parsed — please try again')
                return

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
        len_err = _check_ref_length(reference, 'patristic')
        if len_err:
            yield event('error', msg=len_err)
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

        # Step 1: load corpus texts for display and context
        yield event('step', msg=_step(lang, 'load_verse'))
        corpus = state.corpus
        gnt_text = ''
        if corpus is not None:
            try:
                gnt_words = corpus.get_verse_words(reference, 'GNT')
                gnt_text  = ' '.join(w.word_text for w in gnt_words) if gnt_words else ''
            except Exception:
                gnt_text = ''

        mt_text = lxx_text = ''
        if corpus is not None:
            try:
                mt_words  = corpus.get_verse_words(reference, 'MT')
                lxx_words = corpus.get_verse_words(reference, 'LXX')
                mt_text   = ' '.join(w.word_text for w in mt_words)  if mt_words  else ''
                lxx_text  = ' '.join(w.word_text for w in lxx_words) if lxx_words else ''
            except Exception:
                pass

        if mt_text or lxx_text or gnt_text:
            yield event('section', key='_corpus', data={
                'mt_text':  mt_text,
                'lxx_text': lxx_text,
                'gnt_text': gnt_text,
            })

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'patristic', _PATRISTIC_PROMPT, PATRISTIC_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            for _key, _val in cached.items():
                if _key not in CACHE_META_KEYS:
                    yield event('section', key=_key, data=_val)
                    time.sleep(0.04)
            result = cached
        else:
            yield event('step', msg=_step(lang, 'pat_generating'))
            q = Queue()

            def _run_patristic():
                try:
                    for key, value in pipeline.stream_patristic(reference, gnt_text=gnt_text):
                        if key is None:
                            q.put(('done', None, value))
                            return
                        q.put(('section', key, value))
                    q.put(('done', None, {}))
                except Exception as exc:
                    q.put(('error', None, str(exc)))

            _t = threading.Thread(target=_run_patristic, daemon=True)
            _t.start()

            result = {}
            while True:
                try:
                    item = q.get(timeout=8)
                except Empty:
                    yield ': keepalive\n\n'
                    continue

                evt_type, key, data = item
                if evt_type == 'section':
                    result[key] = data
                    yield event('section', key=key, data=data)
                elif evt_type == 'done':
                    result = data if data else result
                    break
                elif evt_type == 'error':
                    yield event('error', msg=data)
                    return

            if result.get('parse_error'):
                yield event('error', msg='Analysis could not be parsed — please try again')
                return

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
