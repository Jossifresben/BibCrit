"""Literary Analysis blueprint — Chiasm Detector and Source Criticism Tool."""

import json
import threading
from flask import Blueprint, render_template, request, Response, stream_with_context
from biblical_core.claude_pipeline import CHIASM_MODEL, SOURCE_MODEL
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

literary_bp = Blueprint('literary', __name__)

# IMPORTANT: These must stay in sync with the prompt_version set inside the
# corresponding pipeline.analyze_*() methods (see claude_pipeline.py).
# A mismatch causes cache-key divergence and cache misses on every request.
_CHIASM_PROMPT = 'v1'   # keep in sync with analyze_chiasm() prompt_version
_SOURCE_PROMPT = 'v1'   # keep in sync with analyze_source() prompt_version

_STEPS = {
    'en': {
        'load_verse':        '📖 Loading passage text…',
        'checking_cache':    '🔍 Checking analysis cache…',
        'found_cache':       '⚡ Found in cache — loading instantly',
        'found_es':          '⚡ Found in Spanish cache — loading instantly',
        'translating':       '🌐 Translating to Spanish…',
        'chiasm_generating': 'Detecting literary structure — this typically takes 60–90 seconds…',
        'source_generating': 'Analyzing source layers — this typically takes 60–90 seconds…',
    },
    'es': {
        'load_verse':        '📖 Cargando texto del pasaje…',
        'checking_cache':    '🔍 Verificando caché de análisis…',
        'found_cache':       '⚡ Encontrado en caché — cargando al instante',
        'found_es':          '⚡ Encontrado en caché español — cargando al instante',
        'translating':       '🌐 Traduciendo al español…',
        'chiasm_generating': 'Detectando estructura literaria — esto tarda 60–90 segundos…',
        'source_generating': 'Analizando capas de fuentes — esto tarda 60–90 segundos…',
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

@literary_bp.route('/chiasm')
def chiasm():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('chiasm.html', lang=lang, reference=reference, t=state.t)


@literary_bp.route('/source')
def source():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('source.html', lang=lang, reference=reference, t=state.t)


# ── SSE streaming endpoints ────────────────────────────────────────────────

@literary_bp.route('/api/chiasm/stream')
def api_chiasm_stream():
    """SSE endpoint: streams chiasm detection progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return
        len_err = _check_ref_length(reference, 'chiasm')
        if len_err:
            yield event('error', msg=len_err)
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if corpus is None or pipeline is None:
            yield event('error', msg='Server not ready — corpus or pipeline not initialized')
            return

        # Step 1: optionally load MT text for context
        yield event('step', msg=_step(lang, 'load_verse'))
        mt_words = corpus.get_verse_words(reference, 'MT')
        mt_text  = ' '.join(w.word_text for w in mt_words) if mt_words else ''

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'chiasm', _CHIASM_PROMPT, CHIASM_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['reference'] = reference
                yield event('done', data=cached_es)
                return

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'chiasm', _CHIASM_PROMPT, CHIASM_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            # Step 3: call Claude
            yield event('step', msg=_step(lang, 'chiasm_generating'))
            _result_box = [None]
            def _run_chiasm():
                try:
                    _result_box[0] = pipeline.analyze_chiasm(reference, mt_text)
                except Exception as exc:
                    _result_box[0] = {'error': str(exc), 'elements': []}
            _t = threading.Thread(target=_run_chiasm, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0] or {'error': 'Analysis returned no result', 'elements': []}

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['reference'] = reference

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_chiasm():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                              'chiasm', _CHIASM_PROMPT, CHIASM_MODEL)
            _tt = threading.Thread(target=_run_tr_chiasm, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0] or result

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@literary_bp.route('/api/source/stream')
def api_source_stream():
    """SSE endpoint: streams source criticism analysis progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return
        len_err = _check_ref_length(reference, 'source')
        if len_err:
            yield event('error', msg=len_err)
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if corpus is None or pipeline is None:
            yield event('error', msg='Server not ready — corpus or pipeline not initialized')
            return

        # Step 1: optionally load MT text for context
        yield event('step', msg=_step(lang, 'load_verse'))
        mt_words = corpus.get_verse_words(reference, 'MT')
        mt_text  = ' '.join(w.word_text for w in mt_words) if mt_words else ''

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'source', _SOURCE_PROMPT, SOURCE_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['reference'] = reference
                yield event('done', data=cached_es)
                return

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'source', _SOURCE_PROMPT, SOURCE_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            # Step 3: call Claude
            yield event('step', msg=_step(lang, 'source_generating'))
            _result_box = [None]
            def _run_source():
                try:
                    _result_box[0] = pipeline.analyze_source(reference, mt_text)
                except Exception as exc:
                    _result_box[0] = {'error': str(exc), 'source_units': []}
            _t = threading.Thread(target=_run_source, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0] or {'error': 'Analysis returned no result', 'source_units': []}

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['reference'] = reference

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_source():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                              'source', _SOURCE_PROMPT, SOURCE_MODEL)
            _tt = threading.Thread(target=_run_tr_source, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0] or result

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
