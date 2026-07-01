# biblical_core/rate_limit.py
"""Shared Flask-Limiter instance for BibCrit's public API.

storage_uri is pinned to in-memory on purpose: render.yaml runs gunicorn with
--workers 1, so there is exactly one process and in-memory counters stay
consistent across every request. If --workers is ever raised above 1, this
MUST move to a shared backend (e.g. Redis) or limits will silently under-count
because each worker would keep its own counters.
"""
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def api_key_or_ip() -> str:
    """Rate-limit key for Tier-1 (API-key-gated) routes: the raw X-API-Key
    header value if present, else fall back to IP. require_api_key() rejects
    invalid/missing keys with 401 before any real work happens, so a spammed
    bad key only burns its own quota bucket, never a legitimate key's."""
    return request.headers.get('X-API-Key') or get_remote_address()
