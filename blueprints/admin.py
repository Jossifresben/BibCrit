"""Admin dashboard — hidden stats page, not linked from any menu.

Route: /bibcrit-admin-dash
Protected by ADMIN_TOKEN env var (query param ?token=...).
Falls back to no auth in local dev if ADMIN_TOKEN is not set.

Query params:
  ?days=7    number of days to show (default 7; use 'all' for full history)
  ?token=... admin token (required in production)
"""

import os
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, render_template, request

import state

admin_bp = Blueprint('admin', __name__)

_ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '')


def _check_auth() -> bool:
    if not _ADMIN_TOKEN:
        return True  # local dev: no token required
    return request.args.get('token') == _ADMIN_TOKEN


@admin_bp.route('/bibcrit-admin-dash')
def admin_dashboard():
    if not _check_auth():
        abort(403)

    # Days filter — default 7; 'all' means no cutoff
    days_param = request.args.get('days', '7')
    show_all = days_param == 'all'
    if not show_all:
        try:
            days = max(1, min(30, int(days_param)))
        except (ValueError, TypeError):
            days = 7
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    else:
        days = None
        cutoff = None

    sb = getattr(state, 'pipeline', None)
    sb = getattr(sb, '_supabase', None) if sb else None

    stats_by_day = []
    all_entries = []
    totals = {'total': 0, 'distinct_refs': 0, 'tools': []}

    if sb:
        raw_rows = (
            sb.table('analysis_cache')
            .select('cached_at, tool, reference, prompt_version, model_version')
            .order('cached_at', desc=True)
            .execute()
        ).data or []

        # Parse timestamps and optionally filter
        rows = []
        for row in raw_rows:
            raw_ts = row.get('cached_at', '')
            try:
                dt = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
            except Exception:
                continue
            if cutoff is None or dt >= cutoff:
                rows.append((dt, row))

        # Group by day
        by_day: dict = {}
        for dt, row in rows:
            day = dt.strftime('%Y-%m-%d')
            entry = by_day.setdefault(day, {
                'day': day, 'count': 0, 'refs': set(), 'tools': set(),
            })
            entry['count'] += 1
            entry['refs'].add(row.get('reference', ''))
            entry['tools'].add(row.get('tool', ''))

        stats_by_day = sorted(
            [
                {
                    'day': v['day'],
                    'count': v['count'],
                    'distinct_refs': len(v['refs']),
                    'tools': ', '.join(sorted(v['tools'])),
                }
                for v in by_day.values()
            ],
            key=lambda x: x['day'],
            reverse=True,
        )

        all_entries = [
            {
                'cached_at': dt.strftime('%Y-%m-%d %H:%M'),
                'reference': row.get('reference', ''),
                'tool': row.get('tool', ''),
                'prompt_version': row.get('prompt_version', ''),
                'model_version': (row.get('model_version') or '')[:30],
            }
            for dt, row in rows
        ]

        totals['total'] = len(rows)
        totals['distinct_refs'] = len({r.get('reference') for _, r in rows})
        totals['tools'] = sorted({r.get('tool') for _, r in rows})

    return render_template(
        'admin_stats.html',
        stats_by_day=stats_by_day,
        all_entries=all_entries,
        totals=totals,
        days=days,
        show_all=show_all,
        generated_at=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    )
