"""Research blueprint — concordance, hapax, collocations."""

from flask import Blueprint, jsonify

research_bp = Blueprint('research', __name__)


@research_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'app': 'bibcrit'})
