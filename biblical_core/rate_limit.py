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
    header value if present, else fall back to IP. This key_func runs before
    require_api_key() validates the header (Flask-Limiter wraps the outer
    decorator), so a spammed bad key only burns its own quota bucket, never a
    legitimate key's — but it also means each distinct garbage key allocates
    its own live entry in the limiter's in-memory storage until its window
    expires (up to 1h for the 20/hour Tier-1 limit). At this project's scale
    (single gunicorn worker, small user base) that's a bounded memory cost,
    not a live incident — but if abuse ever targets this specifically, moving
    the @require_api_key check before @limiter.limit (auth-then-throttle
    instead of throttle-then-auth) would close it, at the cost of every
    invalid-key request doing an unthrottled Supabase lookup instead."""
    return request.headers.get('X-API-Key') or get_remote_address()
