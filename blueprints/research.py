"""Research blueprint — concordance, hapax, collocations."""

from flask import Blueprint, jsonify, render_template, request
import state

research_bp = Blueprint('research', __name__)


@research_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'app': 'bibcrit'})


@research_bp.route('/guide')
def guide():
    lang = request.args.get('lang', 'en')
    template = 'guide_es.html' if lang == 'es' else 'guide.html'
    return render_template(template, lang=lang, t=state.t)
