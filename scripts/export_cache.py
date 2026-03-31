#!/usr/bin/env python3
"""Export analyses from Supabase → local data/cache/ JSON files.

Use this to seed your local cache from the shared community database,
or to back up the production Supabase data before a migration.

Usage:
    python scripts/export_cache.py                  # pull all rows
    python scripts/export_cache.py --type scribal   # only scribal analyses
    python scripts/export_cache.py --dry-run        # print count, don't write

Requires SUPABASE_URL and SUPABASE_KEY in .env (or environment).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    pass

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
DATA_DIR     = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CACHE_DIR    = os.path.join(DATA_DIR, 'cache')


def main() -> None:
    parser = argparse.ArgumentParser(description='Export Supabase cache → local JSON files')
    parser.add_argument('--type', choices=['divergence', 'scribal', 'numerical', 'backtranslation'],
                        help='Filter by analysis type (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Count rows and print summary without writing files')
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit('ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env or environment.')

    try:
        from supabase import create_client
    except ImportError:
        sys.exit('ERROR: supabase package not installed. Run: pip install supabase')

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f'Connecting to Supabase: {SUPABASE_URL[:40]}…')
    query = client.table('analysis_cache').select('cache_key,data')
    if args.type:
        query = query.eq('analysis_type', args.type)

    result = query.execute()
    rows   = result.data or []
    print(f'Found {len(rows)} row(s) in analysis_cache.')

    if args.dry_run:
        for row in rows:
            key  = row.get('cache_key', '?')
            data = row.get('data') or {}
            kind = data.get('type', data.get('book', data.get('reference', '?')))
            print(f'  {key[:16]}…  →  {kind}')
        print('Dry-run complete — no files written.')
        return

    os.makedirs(CACHE_DIR, exist_ok=True)
    written = 0
    for row in rows:
        key  = row.get('cache_key')
        data = row.get('data')
        if not key or not data:
            continue
        path = os.path.join(CACHE_DIR, f'{key}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        written += 1

    print(f'✅  Wrote {written} file(s) to {CACHE_DIR}/')
    print('    These files are tracked by git. Run `git add data/cache/` to commit them.')


if __name__ == '__main__':
    main()
