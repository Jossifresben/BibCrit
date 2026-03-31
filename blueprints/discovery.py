"""Discovery blueprint — public-facing plain-language findings.

Surfaces analysis_plain entries from the cache where discovery_ready=True.
Content grows automatically as scholars use the analysis tools (the flywheel).

Admin toggle: POST /api/admin/discovery/flag?ref=Isaiah+7:14&ready=true&key=ADMIN_KEY
"""

import os
import random
from flask import Blueprint, render_template, request, jsonify, url_for
import state

discovery_bp = Blueprint('discovery', __name__)


# ── Page route ─────────────────────────────────────────────────────────────

@discovery_bp.route('/discovery')
def discovery():
    lang  = request.args.get('lang', 'en')
    all_cards  = _load_all_cards()
    total      = len(all_cards)
    has_more   = total > 12
    cards      = _load_discovery_cards(limit=12)
    stats      = _load_stats()
    return render_template('discovery.html', lang=lang, t=state.t,
                           cards=cards, has_more=has_more, total=total,
                           stats=stats)


# ── Cards API (paginated) ──────────────────────────────────────────────────

@discovery_bp.route('/api/discovery/cards')
def api_discovery_cards():
    """Return a page of discovery cards as JSON for infinite-scroll / load-more."""
    try:
        offset = int(request.args.get('offset', 0))
        limit  = int(request.args.get('limit',  12))
    except ValueError:
        return jsonify({'error': 'offset and limit must be integers'}), 400

    limit = min(limit, 50)   # cap per request

    all_cards = _load_all_cards()
    if len(all_cards) > 1:
        tail = all_cards[1:]
        random.shuffle(tail)
        all_cards = all_cards[:1] + tail
    page      = all_cards[offset: offset + limit]
    has_more  = (offset + limit) < len(all_cards)

    return jsonify({
        'cards':    page,
        'offset':   offset,
        'limit':    limit,
        'total':    len(all_cards),
        'has_more': has_more,
    })


# ── Public Open-Data API ───────────────────────────────────────────────────

@discovery_bp.route('/api/cache')
def api_cache():
    """Public read-only endpoint for BibCrit's open analysis corpus.

    Query params (all optional):
        tool      — filter by tool: divergence | backtranslation | scribal |
                    numerical | dss | theological | patristic | genealogy
        ref       — filter by reference (case-insensitive substring match)
        discovery_ready — "true" | "false" (default: no filter)
        limit     — max records to return (default 50, max 200)
        offset    — pagination offset (default 0)

    Returns JSON:
        { total, offset, limit, has_more, records: [...] }

    Each record contains:
        cache_key, reference, tool, prompt_version, model_version,
        discovery_ready, cached_at, data
    """
    tool    = request.args.get('tool', '').strip()
    ref     = request.args.get('ref', '').strip()
    dr      = request.args.get('discovery_ready', '').strip().lower()
    try:
        limit  = min(int(request.args.get('limit',  50)),  200)
        offset = max(int(request.args.get('offset',  0)),    0)
    except ValueError:
        return jsonify({'error': 'limit and offset must be integers'}), 400

    records = []

    if state.pipeline and state.pipeline._supabase:
        try:
            q = state.pipeline._supabase.table('analysis_cache') \
                .select('cache_key, reference, tool, prompt_version, model_version, discovery_ready, cached_at, data')
            if tool:
                q = q.eq('tool', tool)
            if dr == 'true':
                q = q.eq('discovery_ready', True)
            elif dr == 'false':
                q = q.eq('discovery_ready', False)
            if ref:
                q = q.ilike('reference', f'%{ref}%')
            result = q.range(offset, offset + limit - 1).execute()
            records = result.data or []
        except Exception as e:
            # Fall through to disk
            pass

    if not records:
        # Disk fallback
        import json as _json
        cache_dir = state.pipeline._cache_dir if state.pipeline else ''
        if cache_dir and os.path.isdir(cache_dir):
            _SKIP = {'budget.json', 'votes.json', 'quality_votes.json'}
            all_files = [f for f in os.listdir(cache_dir)
                         if f.endswith('.json') and f not in _SKIP]
            for fn in sorted(all_files):
                try:
                    with open(os.path.join(cache_dir, fn), encoding='utf-8') as fp:
                        data = _json.load(fp)
                except Exception:
                    continue
                if tool and data.get('tool', '') != tool:
                    continue
                if dr == 'true' and not data.get('discovery_ready'):
                    continue
                if dr == 'false' and data.get('discovery_ready'):
                    continue
                if ref and ref.lower() not in (data.get('reference', '') or '').lower():
                    continue
                records.append({
                    'cache_key':       fn[:-5],
                    'reference':       data.get('reference', data.get('book', '')),
                    'tool':            data.get('tool', ''),
                    'prompt_version':  data.get('prompt_version', ''),
                    'model_version':   data.get('model', ''),
                    'discovery_ready': data.get('discovery_ready', False),
                    'cached_at':       data.get('cached_at', ''),
                    'data':            data,
                })

    total    = len(records)
    page     = records[offset:offset + limit] if not state.pipeline._supabase else records
    has_more = (offset + limit) < total if not state.pipeline._supabase else len(records) == limit

    return jsonify({
        'total':    total,
        'offset':   offset,
        'limit':    limit,
        'has_more': has_more,
        'records':  page,
        'license':  'Apache 2.0 — https://github.com/Jossifresben/bibcrit',
        'citation': 'Fresco Benaim, J. (2026). BibCrit: AI-assisted biblical textual criticism. ORCID:0009-0000-2026-0836',
    })


# ── Admin API ──────────────────────────────────────────────────────────────

@discovery_bp.route('/api/admin/discovery/flag', methods=['POST'])
def admin_flag():
    """Toggle discovery_ready on a cached analysis.

    Query params:
        ref   — reference string, e.g. "Isaiah 7:14"
        ready — "true" | "false"
        key   — must match BIBCRIT_ADMIN_KEY env var
    """
    admin_key = os.environ.get('BIBCRIT_ADMIN_KEY', '')
    if not admin_key or request.args.get('key', '') != admin_key:
        return jsonify({'error': 'Unauthorized'}), 403

    ref   = request.args.get('ref', '').strip()
    ready = request.args.get('ready', 'true').lower() == 'true'

    if not ref:
        return jsonify({'error': 'ref parameter required'}), 400
    if state.pipeline is None:
        return jsonify({'error': 'Pipeline not initialized'}), 503

    updated = state.pipeline.set_discovery_ready(ref, ready)
    if not updated:
        return jsonify({'error': f'No cached analysis found for "{ref}"'}), 404

    return jsonify({'reference': ref, 'discovery_ready': ready})


# ── Helpers ────────────────────────────────────────────────────────────────

def _load_all_cards() -> list:
    """Return ALL discovery cards (no limit) for pagination.

    Priority: discovery_ready=True entries first.
    Falls back to all high-confidence entries in demo / early-content mode.
    """
    if not state.pipeline:
        return []

    curated = state.pipeline.get_discovery_cards(min_confidence=0.6, limit=9999)

    if len(curated) >= 3:
        return curated

    return state.pipeline.get_all_analysis_cards(min_confidence=0.6, limit=9999)


_FEATURED_TYPES = {'different_vorlage', 'theological_tendency', 'scribal_error'}

def _load_discovery_cards(limit: int = 12) -> list:
    """Return first `limit` cards for the initial page render.

    Featured card (index 0) is chosen from the most interesting divergence types:
    different_vorlage, theological_tendency, or scribal_error — these tell compelling
    stories for a general audience. Falls back to the top high-confidence card if
    none of those types are in the pool.
    The remaining cards are shuffled for variety.
    """
    all_cards = _load_all_cards()
    if not all_cards:
        return []

    # Separate into interesting-type candidates vs. the rest
    interesting = [c for c in all_cards if c.get('divergence_type') in _FEATURED_TYPES]
    other       = [c for c in all_cards if c.get('divergence_type') not in _FEATURED_TYPES]

    if interesting:
        # Pick randomly from the up-to-5 highest-confidence interesting cards
        pool_size   = min(5, len(interesting))
        pool        = interesting[:pool_size]
        featured    = pool.pop(random.randrange(pool_size))
        remaining   = pool + interesting[pool_size:] + other
    else:
        # Fall back: pick from top-5 overall
        pool_size   = min(5, len(all_cards))
        pool        = all_cards[:pool_size]
        featured    = pool.pop(random.randrange(pool_size))
        remaining   = pool + all_cards[pool_size:]

    random.shuffle(remaining)
    return ([featured] + remaining)[:limit]


def _load_stats() -> dict:
    """Return aggregate stats for the hero bar."""
    if not state.pipeline:
        return {'passages': 0, 'divergences': 0}
    return state.pipeline.get_discovery_stats()
