"""Textual Analysis blueprint — MT/LXX Divergence Analyzer and corpus browser API."""

import json
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
import state

textual_bp = Blueprint('textual', __name__)

_DIVERGENCE_MODEL  = 'claude-3-5-sonnet-20241022'
_DIVERGENCE_PROMPT = 'v1'


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
        yield event('step', msg='📖 Loading verse text…')
        mt_words  = corpus.get_verse_words(reference, 'MT')
        lxx_words = corpus.get_verse_words(reference, 'LXX')

        if not mt_words and not lxx_words:
            yield event('error', msg=f'No data found for "{reference}". Check spelling — e.g. "Isaiah 7:14"')
            return

        mt_text  = ' '.join(w.word_text for w in mt_words)
        lxx_text = ' '.join(w.word_text for w in lxx_words)

        # Step 2: check cache
        yield event('step', msg='🔍 Checking analysis cache…')
        from biblical_core.claude_pipeline import DIVERGENCE_MODEL
        cached = pipeline.get_cached(reference, 'divergence', _DIVERGENCE_PROMPT, DIVERGENCE_MODEL)

        if cached:
            yield event('step', msg='⚡ Found in cache — loading instantly')
            result = cached
        else:
            # Step 3: call Claude
            yield event('step', msg='🤖 Calling Claude — new passages typically take 20–40s…')
            result = pipeline.analyze_divergence(reference, mt_text, lxx_text)

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['mt_words']  = _words_to_dicts(mt_words)
        result['lxx_words'] = _words_to_dicts(lxx_words)
        result['reference'] = reference

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',   # disable nginx buffering on Render
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
        return jsonify({'spend_usd': 0.0, 'cap_usd': 5.0, 'pct': 0.0,
                        'month': ''})
    budget = state.pipeline.get_budget()
    cap = budget['cap_usd'] or 5.0
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
        reference, 'divergence', _DIVERGENCE_PROMPT, _DIVERGENCE_MODEL
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
        reference, 'divergence', _DIVERGENCE_PROMPT, _DIVERGENCE_MODEL
    )
    if not data:
        return jsonify({'error': f'No cached analysis for "{reference}".'}), 404
    from biblical_core.divergence import parse_claude_response, format_bibtex
    records = parse_claude_response(data, reference)
    bibtex  = '\n\n'.join(format_bibtex(r) for r in records)
    return jsonify({'reference': reference, 'bibtex': bibtex})


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
