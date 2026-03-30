"""Discovery blueprint — public-facing plain-language findings.

Surfaces analysis_plain entries from the cache where discovery_ready=True.
Content grows automatically as scholars use the analysis tools (the flywheel).
"""

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
    return state.pipeline.get_discovery_cards(min_confidence=0.6, limit=12)
