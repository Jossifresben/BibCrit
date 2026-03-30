"""Discovery blueprint — public-facing plain-language findings.

Surfaces analysis_plain entries from the cache where discovery_ready=True.
Content grows automatically as scholars use the analysis tools (the flywheel).
"""

import json
import os
from flask import Blueprint, render_template, request
import state

discovery_bp = Blueprint('discovery', __name__)


@discovery_bp.route('/discovery')
def discovery():
    lang = request.args.get('lang', 'en')
    cards = _load_discovery_cards()
    return render_template('discovery.html', lang=lang, t=state.t, cards=cards)


def _load_discovery_cards() -> list:
    """Return cached analyses flagged discovery_ready=True, sorted by confidence."""
    if not state.pipeline:
        return []

    cache_dir = state.pipeline.cache_dir
    cards = []

    if not os.path.isdir(cache_dir):
        return []

    for filename in os.listdir(cache_dir):
        if not filename.endswith('.json') or filename == 'budget.json':
            continue
        path = os.path.join(cache_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if not data.get('discovery_ready'):
            continue

        for div in data.get('divergences', []):
            if div.get('analysis_plain') and div.get('confidence', 0) >= 0.6:
                cards.append({
                    'reference':       data.get('reference', ''),
                    'mt_word':         div.get('mt_word', ''),
                    'lxx_word':        div.get('lxx_word', ''),
                    'divergence_type': div.get('divergence_type', ''),
                    'confidence':      div.get('confidence', 0.0),
                    'analysis_plain':  div.get('analysis_plain', ''),
                    'summary_plain':   data.get('summary_plain', ''),
                    'cached_at':       data.get('cached_at', ''),
                })

    return sorted(cards, key=lambda c: c['confidence'], reverse=True)[:12]
