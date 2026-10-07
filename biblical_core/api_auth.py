"""API key issuance and validation for BibCrit's Open API v1.

Keys are never stored in plaintext — only their SHA-256 hash. Only the Flask
backend (holding the Supabase service-role key) ever reads/writes api_keys;
the table has RLS enabled with zero policies (default-deny).

Key enforcement is opt-in via BIBCRIT_API_KEYS_ENFORCE=1; by default the
key-gated endpoints accept anonymous calls, rate-limited by IP. See
docs/superpowers/specs/2026-07-01-open-api-v1-design.md for the full design.
"""
import hashlib
import logging
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import jsonify, request

import state

logger = logging.getLogger(__name__)

KEY_PREFIX = 'bibcrit_live_'


def generate_api_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def _unauthorized():
    return jsonify({
        'error': 'unauthorized',
        'message': 'Missing or invalid API key. Get one for free: POST /api/v1/keys',
    }), 401


def api_keys_enforced() -> bool:
    return os.environ.get('BIBCRIT_API_KEYS_ENFORCE', '0') == '1'


def validate_api_key(raw_key: str) -> bool:
    """Return True and bump usage stats if raw_key is a live, non-revoked key."""
    if not raw_key or not state.pipeline or not state.pipeline._supabase:
        return False
    key_hash = hash_api_key(raw_key)
    try:
        result = (
            state.pipeline._supabase.table('api_keys')
            .select('id, revoked, requests_total')
            .eq('key_hash', key_hash)
            .limit(1)
            .execute()
        )
        if not result.data or result.data[0]['revoked']:
            return False
        row = result.data[0]
        state.pipeline._supabase.table('api_keys').update({
            'last_used_at':    datetime.utcnow().isoformat(),
            'requests_total':  row['requests_total'] + 1,
        }).eq('id', row['id']).execute()
        return True
    except Exception:
        logger.exception('validate_api_key failed unexpectedly')
        return False


def require_api_key(view):
    """Decorator for Tier-1 (Claude-calling) routes. Reads the X-API-Key
    header, rejects with 401 if missing/invalid/revoked — only when
    BIBCRIT_API_KEYS_ENFORCE=1; otherwise the view is called directly."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not api_keys_enforced():
            return view(*args, **kwargs)
        raw_key = request.headers.get('X-API-Key', '')
        if not validate_api_key(raw_key):
            return _unauthorized()
        return view(*args, **kwargs)
    return wrapped
