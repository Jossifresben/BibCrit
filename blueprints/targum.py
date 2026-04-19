"""Targum Comparator blueprint — /targum page and /api/targum/stream SSE endpoint."""

import json
import threading
from queue import Queue, Empty
from flask import Blueprint, render_template, request, Response, stream_with_context
from biblical_core.claude_pipeline import TARGUM_MODEL
from biblical_core.ref_utils import estimate_verse_count, TOOL_VERSE_LIMITS
import state

targum_bp = Blueprint('targum', __name__)

# IMPORTANT: must stay in sync with prompt_version in pipeline.analyze_targum()
_TARGUM_PROMPT = 'v1'

_STEPS = {
    'en': {
        'load_verse':     '📖 Loading verse text…',
        'checking_cache': '🔍 Checking analysis cache…',
        'found_cache':    '⚡ Found in cache — loading instantly',
        'found_es':       '⚡ Found in Spanish cache — loading instantly',
        'generating':     'Analyzing Targum — this typically takes 60–90 seconds…',
        'translating':    '🌐 Translating to Spanish…',
    },
    'es': {
        'load_verse':     '📖 Cargando texto del versículo…',
        'checking_cache': '🔍 Verificando caché de análisis…',
        'found_cache':    '⚡ Encontrado en caché — cargando al instante',
        'found_es':       '⚡ Encontrado en caché español — cargando al instante',
        'generating':     'Analizando el Targum — esto tarda 60–90 segundos…',
        'translating':    '🌐 Traduciendo al español…',
    },
}


def _step(lang: str, key: str) -> str:
    return _STEPS.get(lang, _STEPS['en']).get(key, _STEPS['en'].get(key, key))


def _check_ref_length(reference: str) -> str | None:
    max_v = TOOL_VERSE_LIMITS.get('targum')
    if not max_v:
        return None
    est = estimate_verse_count(reference)
    if est > max_v:
        return (
            f'Passage too long (≈{est} verses estimated). '
            f'Please limit to {max_v} verses or fewer for this tool.'
        )
    return None


# ── Page route ──────────────────────────────────────────────────────────────

@targum_bp.route('/targum')
def targum():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('targum.html', lang=lang, reference=reference, t=state.t)


# ── SSE stream ──────────────────────────────────────────────────────────────

@targum_bp.route('/api/targum/stream')
def api_targum_stream():
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        len_err = _check_ref_length(reference)
        if len_err:
            yield event('error', msg=len_err)
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if corpus is None or pipeline is None:
            yield event('error', msg='Server not ready — corpus or pipeline not initialized')
            return

        # Validate: Targum covers Torah + Prophets only
        from biblical_core.ref_utils import validate_targum_reference
        val_err = validate_targum_reference(reference)
        if val_err:
            yield event('error', msg=val_err)
            return

        # Step 1: load verse texts
        yield event('step', msg=_step(lang, 'load_verse'))
        mt_words   = corpus.get_verse_words(reference, 'MT')
        lxx_words  = corpus.get_verse_words(reference, 'LXX')
        targ_words = corpus.get_verse_words(reference, 'TARG')

        mt_text   = ' '.join(w.word_text for w in mt_words)   if mt_words   else ''
        lxx_text  = ' '.join(w.word_text for w in lxx_words)  if lxx_words  else ''
        targ_text = ' '.join(w.word_text for w in targ_words) if targ_words else ''
        manuscript = targ_words[0].manuscript if targ_words else 'Onkelos'

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'targum', _TARGUM_PROMPT, TARGUM_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es.update({'mt_text': mt_text, 'lxx_text': lxx_text,
                                   'targ_text': targ_text, 'manuscript': manuscript})
                yield event('done', data=cached_es)
                return

        # Step 2: check English cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'targum', _TARGUM_PROMPT, TARGUM_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            # Step 3: call Claude
            yield event('step', msg=_step(lang, 'generating'))
            q = Queue()

            def _run_targum():
                try:
                    for key, value in pipeline.stream_targum(
                        reference, mt_text, lxx_text, targ_text, manuscript
                    ):
                        if key is None:
                            q.put(('done', None, value))
                            return
                        q.put(('section', key, value))
                    q.put(('done', None, {}))
                except Exception as exc:
                    q.put(('error', None, str(exc)))

            _t = threading.Thread(target=_run_targum, daemon=True)
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

        result.update({'mt_text': mt_text, 'lxx_text': lxx_text,
                        'targ_text': targ_text, 'manuscript': manuscript})

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]

            def _run_tr():
                from blueprints.textual import _translate_step
                translated = _translate_step(pipeline, lang, result, reference,
                                             'targum', _TARGUM_PROMPT, TARGUM_MODEL)
                translated.update({'mt_text': result['mt_text'],
                                    'lxx_text': result['lxx_text'],
                                    'targ_text': result['targ_text'],
                                    'manuscript': result['manuscript']})
                _tr_box[0] = translated

            _tt = threading.Thread(target=_run_tr, daemon=True)
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
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
