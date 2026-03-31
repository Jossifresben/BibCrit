"""Textual Analysis blueprint — MT/LXX Divergence Analyzer and corpus browser API."""

import json
import os
import threading
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from biblical_core.claude_pipeline import DIVERGENCE_MODEL, DSS_MODEL, GENEALOGY_MODEL
import state

_votes_lock = threading.Lock()

textual_bp = Blueprint('textual', __name__)

_DIVERGENCE_PROMPT     = 'v2'
_BACKTRANSLATION_PROMPT = 'v1'
_DSS_PROMPT            = 'v1'
_GENEALOGY_PROMPT      = 'v1'

_STEPS = {
    'en': {
        'load_verse':     '📖 Loading verse text…',
        'load_genealogy': '📚 Loading genealogy data…',
        'checking_cache': '🔍 Checking analysis cache…',
        'found_cache':    '⚡ Found in cache — loading instantly',
        'found_es':       '⚡ Found in Spanish cache — loading instantly',
        'translating':    '🌐 Translating to Spanish…',
        'div_generating': 'Analyzing — new passages typically take 60–90s…',
        'bt_generating':  'Reconstructing Vorlage — new passages typically take 60–90s…',
        'dss_generating': 'Comparing DSS witnesses — this typically takes 60–90 seconds…',
        'gen_generating': 'Tracing transmission history — this typically takes 60–90 seconds…',
    },
    'es': {
        'load_verse':     '📖 Cargando texto del versículo…',
        'load_genealogy': '📚 Cargando datos genealógicos…',
        'checking_cache': '🔍 Verificando caché de análisis…',
        'found_cache':    '⚡ Encontrado en caché — cargando al instante',
        'found_es':       '⚡ Encontrado en caché español — cargando al instante',
        'translating':    '🌐 Traduciendo al español…',
        'div_generating': 'Analizando — los pasajes nuevos tardan 60–90 s…',
        'bt_generating':  'Reconstruyendo el Vorlage — los pasajes nuevos tardan 60–90 s…',
        'dss_generating': 'Comparando testigos DSS — esto tarda 60–90 segundos…',
        'gen_generating': 'Rastreando la historia de transmisión — esto tarda 60–90 segundos…',
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

@textual_bp.route('/')
def index():
    lang = request.args.get('lang', 'en')
    return render_template('index.html', lang=lang, t=state.t)


@textual_bp.route('/divergence')
def divergence():
    lang = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('divergence.html', lang=lang, reference=reference, t=state.t)


@textual_bp.route('/backtranslation')
def backtranslation():
    lang = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('backtranslation.html', lang=lang, reference=reference, t=state.t)


@textual_bp.route('/dss')
def dss():
    lang = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('dss.html', lang=lang, reference=reference, t=state.t)


@textual_bp.route('/genealogy')
def genealogy():
    book = request.args.get('book', '').strip()
    lang = request.args.get('lang', 'en')
    return render_template('genealogy.html', book=book, lang=lang, t=state.t)


# ── Analysis API ───────────────────────────────────────────────────────────

@textual_bp.route('/api/divergence')
def api_divergence():
    """Run (or return cached) MT/LXX divergence analysis for a reference."""
    reference = request.args.get('ref', '').strip()
    if not reference:
        return jsonify({'error': 'ref parameter required'}), 400

    corpus   = state.corpus
    pipeline = state.pipeline

    if corpus is None or pipeline is None:
        return jsonify({'error': 'Server not ready — corpus or pipeline not initialized'}), 503

    mt_words  = corpus.get_verse_words(reference, 'MT')
    lxx_words = corpus.get_verse_words(reference, 'LXX')

    if not mt_words and not lxx_words:
        return jsonify({'error': f'No data found for "{reference}". '
                                  'Check spelling — e.g. "Isaiah 7:14"'}), 404

    mt_text  = ' '.join(w.word_text for w in mt_words)
    lxx_text = ' '.join(w.word_text for w in lxx_words)

    result = pipeline.analyze_divergence(reference, mt_text, lxx_text)

    result['mt_words']  = _words_to_dicts(mt_words)
    result['lxx_words'] = _words_to_dicts(lxx_words)
    result['reference'] = reference

    return jsonify(result)


# ── SSE streaming analysis ────────────────────────────────────────────────

@textual_bp.route('/api/divergence/stream')
def api_divergence_stream():
    """SSE endpoint: streams step-by-step progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if corpus is None or pipeline is None:
            yield event('error', msg='Server not ready — corpus or pipeline not initialized')
            return

        # Step 1: load verse text
        yield event('step', msg=_step(lang, 'load_verse'))
        mt_words  = corpus.get_verse_words(reference, 'MT')
        lxx_words = corpus.get_verse_words(reference, 'LXX')

        if not mt_words and not lxx_words:
            yield event('error', msg=f'No data found for "{reference}". Check spelling — e.g. "Isaiah 7:14"')
            return

        mt_text  = ' '.join(w.word_text for w in mt_words)
        lxx_text = ' '.join(w.word_text for w in lxx_words)

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'divergence', _DIVERGENCE_PROMPT, DIVERGENCE_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['mt_words']  = _words_to_dicts(mt_words)
                cached_es['lxx_words'] = _words_to_dicts(lxx_words)
                cached_es['reference'] = reference
                yield event('done', data=cached_es)
                return

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'divergence', _DIVERGENCE_PROMPT, DIVERGENCE_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            # Step 3: call Claude
            yield event('step', msg=_step(lang, 'div_generating'))
            _result_box = [None]
            def _run():
                _result_box[0] = pipeline.analyze_divergence(reference, mt_text, lxx_text)
            _t = threading.Thread(target=_run, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0]

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['mt_words']  = _words_to_dicts(mt_words)
        result['lxx_words'] = _words_to_dicts(lxx_words)
        result['reference'] = reference

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_div():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                             'divergence', _DIVERGENCE_PROMPT, DIVERGENCE_MODEL)
                # Restore corpus word data after translation (not stored in cache)
                _tr_box[0]['mt_words']  = result['mt_words']
                _tr_box[0]['lxx_words'] = result['lxx_words']
            _tt = threading.Thread(target=_run_tr_div, daemon=True)
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
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',   # disable nginx buffering on Render
        },
    )


# ── Back-translation SSE stream ───────────────────────────────────────────

@textual_bp.route('/api/backtranslation/stream')
def api_backtranslation_stream():
    """SSE endpoint: streams Vorlage reconstruction progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if corpus is None or pipeline is None:
            yield event('error', msg='Server not ready — corpus or pipeline not initialized')
            return

        # Step 1: load verse text
        yield event('step', msg=_step(lang, 'load_verse'))
        lxx_words = corpus.get_verse_words(reference, 'LXX')
        mt_words  = corpus.get_verse_words(reference, 'MT')

        if not lxx_words:
            yield event('error', msg=f'No LXX data found for "{reference}". Check spelling — e.g. "Isaiah 7:14"')
            return

        lxx_text = ' '.join(w.word_text for w in lxx_words)
        mt_text  = ' '.join(w.word_text for w in mt_words)

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'backtranslation',
                                               _BACKTRANSLATION_PROMPT, DIVERGENCE_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['lxx_words'] = _words_to_dicts(lxx_words)
                cached_es['mt_words']  = _words_to_dicts(mt_words)
                cached_es['reference'] = reference
                yield event('done', data=cached_es)
                return

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'backtranslation',
                                     _BACKTRANSLATION_PROMPT, DIVERGENCE_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            yield event('step', msg=_step(lang, 'bt_generating'))
            _result_box = [None]
            def _run_bt():
                _result_box[0] = pipeline.analyze_backtranslation(reference, lxx_text, mt_text)
            _t = threading.Thread(target=_run_bt, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0]

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['lxx_words'] = _words_to_dicts(lxx_words)
        result['mt_words']  = _words_to_dicts(mt_words)
        result['reference'] = reference

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]
            def _run_tr_bt():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                             'backtranslation', _BACKTRANSLATION_PROMPT, DIVERGENCE_MODEL)
                _tr_box[0]['lxx_words'] = result['lxx_words']
                _tr_box[0]['mt_words']  = result['mt_words']
            _tt = threading.Thread(target=_run_tr_bt, daemon=True)
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


# ── DSS Bridge SSE stream ─────────────────────────────────────────────────

@textual_bp.route('/api/dss/stream')
def api_dss_stream():
    """SSE endpoint: streams DSS bridge analysis progress then final result."""
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if pipeline is None:
            yield event('error', msg='Server not ready — pipeline not initialized')
            return

        # Step 1: load verse text
        yield event('step', msg=_step(lang, 'load_verse'))
        mt_text  = ''
        lxx_text = ''
        if corpus is not None:
            mt_words  = corpus.get_verse_words(reference, 'MT')
            lxx_words = corpus.get_verse_words(reference, 'LXX')
            mt_text   = ' '.join(w.word_text for w in mt_words)  if mt_words  else ''
            lxx_text  = ' '.join(w.word_text for w in lxx_words) if lxx_words else ''

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'dss', _DSS_PROMPT, DSS_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['reference'] = reference
                yield event('done', data=cached_es)
                return

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'dss', _DSS_PROMPT, DSS_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            yield event('step', msg=_step(lang, 'dss_generating'))
            _result_box = [None]
            def _run_dss():
                _result_box[0] = pipeline.analyze_dss(reference, mt_text, lxx_text)
            _t = threading.Thread(target=_run_dss, daemon=True)
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
            def _run_tr_dss():
                _tr_box[0] = _translate_step(pipeline, lang, result, reference,
                                             'dss', _DSS_PROMPT, DSS_MODEL)
            _tt = threading.Thread(target=_run_tr_dss, daemon=True)
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


# ── Genealogy SSE stream ──────────────────────────────────────────────────

@textual_bp.route('/api/genealogy/stream')
def api_genealogy_stream():
    """SSE endpoint: streams manuscript genealogy analysis progress then final result."""
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

        if lang == 'es':
            cached_es = pipeline.get_cached_es(book, 'genealogy', _GENEALOGY_PROMPT, GENEALOGY_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['book'] = book
                yield event('done', data=cached_es)
                return

        # Step 1: announce loading
        yield event('step', msg=_step(lang, 'load_genealogy'))

        # Step 2: check cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(book, 'genealogy', _GENEALOGY_PROMPT, GENEALOGY_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            yield event('step', msg=_step(lang, 'gen_generating'))
            _result_box = [None]
            def _run_genealogy():
                _result_box[0] = pipeline.analyze_genealogy(book)
            _t = threading.Thread(target=_run_genealogy, daemon=True)
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
            def _run_tr_gen():
                _tr_box[0] = _translate_step(pipeline, lang, result, book,
                                             'genealogy', _GENEALOGY_PROMPT, GENEALOGY_MODEL)
            _tt = threading.Thread(target=_run_tr_gen, daemon=True)
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


# ── Corpus browser API ─────────────────────────────────────────────────────

@textual_bp.route('/api/books')
def api_books():
    tradition = request.args.get('tradition', 'MT')
    if state.corpus is None:
        return jsonify({'books': []})
    books = state.corpus.get_books(tradition)
    return jsonify({'books': books})


@textual_bp.route('/api/chapters')
def api_chapters():
    book      = request.args.get('book', '')
    tradition = request.args.get('tradition', 'MT')
    if not book:
        return jsonify({'error': 'book parameter required'}), 400
    if state.corpus is None:
        return jsonify({'chapters': []})
    chapters = state.corpus.get_chapters(book, tradition)
    return jsonify({'chapters': chapters})


@textual_bp.route('/api/verses')
def api_verses():
    book      = request.args.get('book', '')
    tradition = request.args.get('tradition', 'MT')
    try:
        chapter = int(request.args.get('chapter', '1'))
    except ValueError:
        return jsonify({'error': 'chapter must be an integer'}), 400
    if not book:
        return jsonify({'error': 'book parameter required'}), 400
    if state.corpus is None:
        return jsonify({'verses': []})
    verses = state.corpus.get_verses(book, chapter, tradition)
    return jsonify({'verses': verses})


# ── Budget API ─────────────────────────────────────────────────────────────

@textual_bp.route('/api/budget')
def api_budget():
    if state.pipeline is None:
        return jsonify({'spend_usd': 0.0, 'cap_usd': 10.0, 'pct': 0.0,
                        'month': ''})
    budget = state.pipeline.get_budget()
    cap = budget['cap_usd'] or 10.0
    pct = round((budget['spend_usd'] / cap) * 100, 1)
    budget['pct'] = pct
    return jsonify(budget)


# ── Export API ─────────────────────────────────────────────────────────────

@textual_bp.route('/api/divergence/export/sbl')
def export_sbl():
    reference = request.args.get('ref', '').strip()
    if not reference:
        return jsonify({'error': 'ref parameter required'}), 400
    if state.pipeline is None:
        return jsonify({'error': 'Pipeline not initialized'}), 503
    data = state.pipeline.get_cached(
        reference, 'divergence', _DIVERGENCE_PROMPT, DIVERGENCE_MODEL
    )
    if not data:
        return jsonify({'error': f'No cached analysis for "{reference}". '
                                  'Run the Divergence Analyzer first.'}), 404
    from biblical_core.divergence import parse_claude_response, format_sbl_footnote
    records   = parse_claude_response(data, reference)
    footnotes = [format_sbl_footnote(r) for r in records]
    return jsonify({'reference': reference, 'footnotes': footnotes})


@textual_bp.route('/api/divergence/export/bibtex')
def export_bibtex():
    reference = request.args.get('ref', '').strip()
    if not reference:
        return jsonify({'error': 'ref parameter required'}), 400
    if state.pipeline is None:
        return jsonify({'error': 'Pipeline not initialized'}), 503
    data = state.pipeline.get_cached(
        reference, 'divergence', _DIVERGENCE_PROMPT, DIVERGENCE_MODEL
    )
    if not data:
        return jsonify({'error': f'No cached analysis for "{reference}".'}), 404
    from biblical_core.divergence import parse_claude_response, format_bibtex
    model_version = data.get('model_version', 'Claude')
    records = parse_claude_response(data, reference)
    bibtex  = '\n\n'.join(format_bibtex(r, model_version) for r in records)
    return jsonify({'reference': reference, 'bibtex': bibtex})


# ── Result quality vote API ────────────────────────────────────────────────

@textual_bp.route('/api/vote', methods=['POST'])
def api_vote():
    """Record a quality vote (upvote=1, downvote=-1, remove=0) for a tool result."""
    try:
        body = request.get_json(force=True) or {}
        ref   = str(body.get('reference', ''))[:200]
        tool  = str(body.get('tool', ''))[:50]
        value = int(body.get('value', 0))
        if value not in (-1, 0, 1):
            return jsonify({'error': 'value must be -1, 0, or 1'}), 400
        quality_votes_path = _votes_path().replace('votes.json', 'quality_votes.json')
        with _votes_lock:
            try:
                with open(quality_votes_path, 'r', encoding='utf-8') as f:
                    quality_votes = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                quality_votes = {}
            key = f'{tool}:{ref}'
            if value == 0:
                quality_votes.pop(key, None)
            else:
                quality_votes[key] = quality_votes.get(key, 0) + value
            os.makedirs(os.path.dirname(quality_votes_path), exist_ok=True)
            with open(quality_votes_path, 'w', encoding='utf-8') as f:
                json.dump(quality_votes, f, ensure_ascii=False, indent=2)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Result quality votes GET ──────────────────────────────────────────────

@textual_bp.route('/api/votes')
def api_votes():
    """Return aggregate vote counts for a tool+reference pair."""
    ref  = request.args.get('ref',  '').strip()[:200]
    tool = request.args.get('tool', '').strip()[:50]
    quality_votes_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'data', 'cache', 'quality_votes.json'
    )
    try:
        with open(quality_votes_path, 'r') as f:
            votes = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        votes = {}
    key_up   = f'{tool}:{ref}:up'
    key_down = f'{tool}:{ref}:down'
    # Also check the aggregated format stored by api_vote
    val = votes.get(f'{tool}:{ref}', 0)
    upvotes   = max(0, val) if val > 0 else votes.get(key_up, 0)
    downvotes = max(0, -val) if val < 0 else votes.get(key_down, 0)
    return jsonify({'tool': tool, 'reference': ref, 'upvotes': upvotes, 'downvotes': downvotes})


# ── Generic export API ─────────────────────────────────────────────────────

@textual_bp.route('/api/export/sbl')
def export_generic_sbl():
    """Generic SBL footnote export for any tool."""
    ref  = request.args.get('ref', '').strip() or request.args.get('book', '').strip()
    tool = request.args.get('tool', '').strip()
    if not ref or not tool:
        return jsonify({'error': 'ref/book and tool parameters required'}), 400
    if state.pipeline is None:
        return jsonify({'error': 'Pipeline not initialized'}), 503

    year = '2026'
    footnote = (
        f'BibCrit, s.v. "{ref}" ({tool} analysis), '
        f'accessed {year}, https://bibcrit.app/{tool}?ref={ref.replace(" ", "+")}, '
        f'powered by Anthropic Claude. '
        f'Jossi Fresco Benaim, ORCID: 0009-0000-2026-0836.'
    )
    return jsonify({'reference': ref, 'tool': tool, 'footnote': footnote, 'footnotes': [footnote]})


@textual_bp.route('/api/export/bibtex')
def export_generic_bibtex():
    """Generic BibTeX export for any tool."""
    ref  = request.args.get('ref', '').strip() or request.args.get('book', '').strip()
    tool = request.args.get('tool', '').strip()
    if not ref or not tool:
        return jsonify({'error': 'ref/book and tool parameters required'}), 400

    # Try to get model version from cache
    model_version = 'Claude'
    if state.pipeline:
        try:
            from biblical_core import claude_pipeline as _cp
            _model_map = {
                'backtranslation': getattr(_cp, 'BACKTRANSLATION_MODEL', _cp.DIVERGENCE_MODEL),
                'dss':             _cp.DSS_MODEL,
                'genealogy':       _cp.GENEALOGY_MODEL,
                'scribal':         getattr(_cp, 'SCRIBAL_MODEL',     _cp.DIVERGENCE_MODEL),
                'theological':     getattr(_cp, 'THEOLOGICAL_MODEL', _cp.DIVERGENCE_MODEL),
                'patristic':       getattr(_cp, 'PATRISTIC_MODEL',   _cp.DIVERGENCE_MODEL),
                'numerical':       getattr(_cp, 'NUMERICAL_MODEL',   _cp.DIVERGENCE_MODEL),
            }
            _pv_map = {
                'backtranslation': _BACKTRANSLATION_PROMPT,
                'dss':             _DSS_PROMPT,
                'genealogy':       _GENEALOGY_PROMPT,
            }
            _model  = _model_map.get(tool, _cp.DIVERGENCE_MODEL)
            _pv     = _pv_map.get(tool, 'v1')
            cached  = state.pipeline.get_cached(ref, tool, _pv, _model)
            if cached and cached.get('model_version'):
                model_version = cached['model_version']
        except Exception:
            pass

    import re as _re
    key = _re.sub(r'[^a-zA-Z0-9]', '', ref) + tool.capitalize() + '2026'
    bibtex = (
        f'@misc{{{key},\n'
        f'  author       = {{Fresco Benaim, Jossi}},\n'
        f'  orcid        = {{ORCID: 0009-0000-2026-0836}},\n'
        f'  title        = {{{{BibCrit {tool.title()} analysis of {ref}}}}},\n'
        f'  year         = {{2026}},\n'
        f'  howpublished = {{\\url{{https://bibcrit.app/{tool}?ref={ref.replace(" ", "+")}}}}},\n'
        f'  note         = {{Powered by {model_version}}},\n'
        f'}}'
    )
    return jsonify({'reference': ref, 'tool': tool, 'bibtex': bibtex})


# ── Hypothesis voting API ──────────────────────────────────────────────────

@textual_bp.route('/api/hypothesis/votes')
def hypothesis_votes():
    """Return upvote/downvote counts for a reference."""
    ref = request.args.get('ref', '').strip()
    if not ref:
        return jsonify({'error': 'ref required'}), 400
    counts = _get_votes(ref)
    return jsonify(counts)


@textual_bp.route('/api/hypothesis/vote', methods=['POST'])
def hypothesis_vote():
    """Cast or retract a vote. direction=up|down, action=cast|retract."""
    ref       = request.args.get('ref', '').strip()
    direction = request.args.get('direction', '')   # 'up' or 'down'
    action    = request.args.get('action', 'cast')  # 'cast' or 'retract'

    if not ref or direction not in ('up', 'down'):
        return jsonify({'error': 'ref and direction (up|down) required'}), 400

    delta = 1 if action == 'cast' else -1
    counts = _record_vote(ref, direction, delta)
    return jsonify(counts)


def _votes_path() -> str:
    """Path to the disk-based votes store."""
    if state.pipeline:
        return os.path.join(state.pipeline.cache_dir, 'votes.json')
    return os.path.join('data', 'cache', 'votes.json')


def _get_votes(ref: str) -> dict:
    """Return {upvotes, downvotes} for ref. Tries Supabase first, falls back to disk."""
    sb = getattr(state.pipeline, '_supabase', None) if state.pipeline else None
    if sb:
        try:
            result = sb.table('hypothesis_votes').select('upvotes,downvotes') \
                       .eq('reference', ref).limit(1).execute()
            if result.data:
                row = result.data[0]
                return {'upvotes': row['upvotes'], 'downvotes': row['downvotes']}
        except Exception:
            pass  # fall through to disk

    # Disk fallback
    store = _load_votes_store()
    row = store.get(ref, {'upvotes': 0, 'downvotes': 0})
    return {'upvotes': row['upvotes'], 'downvotes': row['downvotes']}


def _record_vote(ref: str, direction: str, delta: int) -> dict:
    """Atomically increment/decrement a vote. Returns updated counts."""
    with _votes_lock:
        current = _get_votes(ref)
        if direction == 'up':
            new_up   = max(0, current['upvotes']   + delta)
            new_down = current['downvotes']
        else:
            new_up   = current['upvotes']
            new_down = max(0, current['downvotes'] + delta)

        updated = {'upvotes': new_up, 'downvotes': new_down}

        # Write to Supabase
        sb = getattr(state.pipeline, '_supabase', None) if state.pipeline else None
        if sb:
            try:
                from datetime import datetime
                sb.table('hypothesis_votes').upsert({
                    'reference':  ref,
                    'upvotes':    new_up,
                    'downvotes':  new_down,
                    'updated_at': datetime.utcnow().isoformat(),
                }).execute()
            except Exception:
                pass

        # Always write disk fallback
        store = _load_votes_store()
        store[ref] = updated
        _save_votes_store(store)

        return updated


def _load_votes_store() -> dict:
    path = _votes_path()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_votes_store(store: dict) -> None:
    path = _votes_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


# ── Helpers ────────────────────────────────────────────────────────────────

def _words_to_dicts(words) -> list:
    return [
        {
            'position': w.position,
            'word_text': w.word_text,
            'lemma': w.lemma,
            'morph': w.morph,
            'strong': w.strong,
        }
        for w in words
    ]
