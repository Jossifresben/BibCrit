"""API v1 blueprint — API key issuance for BibCrit's Open API.

See docs/superpowers/specs/2026-07-01-open-api-v1-design.md for the full
design: keys are only required on the Claude-calling analysis-stream
endpoints, never on the free/cached reads.
"""
from datetime import datetime

from flask import Blueprint, jsonify, request

import state
from biblical_core.api_auth import generate_api_key, hash_api_key
from biblical_core.rate_limit import limiter

api_v1_bp = Blueprint('api_v1', __name__)


@api_v1_bp.route('/api/v1/keys', methods=['POST'])
@limiter.limit('5/hour')
def issue_api_key():
    """Issue a new API key. Body: {"name": str, "email": str}.

    The raw key is returned ONCE and never stored in plaintext — save it, it
    cannot be recovered later. Free, no login required.
    """
    body = request.get_json(silent=True) or {}
    name = (body.get('name') or '').strip()
    email = (body.get('email') or '').strip()
    if not name or not email:
        return jsonify({'error': 'name and email are required'}), 400

    if not state.pipeline or not state.pipeline._supabase:
        return jsonify({'error': 'Key storage unavailable'}), 503

    raw_key = generate_api_key()
    try:
        state.pipeline._supabase.table('api_keys').insert({
            'key_hash':       hash_api_key(raw_key),
            'key_prefix':     raw_key[:12],
            'owner_name':     name,
            'owner_email':    email,
            'created_at':     datetime.utcnow().isoformat(),
            'revoked':        False,
            'requests_total': 0,
        }).execute()
    except Exception:
        return jsonify({'error': 'Could not create key, try again'}), 503

    return jsonify({
        'api_key': raw_key,
        'message': ('Save this key now — it will not be shown again. Send it '
                    'as the X-API-Key header on analysis-stream endpoints.'),
    }), 201
