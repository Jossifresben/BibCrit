#!/usr/bin/env python3
"""Push local data/cache/ JSON files → Supabase analysis_cache table.

Use this to contribute your locally-generated analyses back to the shared
community database, or to restore Supabase from a git-committed cache snapshot.

Usage:
    python scripts/push_cache_to_supabase.py           # push all local files
    python scripts/push_cache_to_supabase.py --dry-run # print what would be pushed
    python scripts/push_cache_to_supabase.py --force   # overwrite existing rows

Requires SUPABASE_URL and SUPABASE_KEY in .env (or environment).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

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

# Map known data shapes → analysis_type labels
def _detect_type(data: dict) -> str:
    if 'dimensions' in data:                        return 'scribal'
    if 'figures' in data and 'theories' in data:    return 'numerical'
    if 'divergences' in data:                       return 'divergence'
    if 'back_translations' in data:                 return 'backtranslation'
    if 'dss_manuscripts' in data:                   return 'dss'
    if 'revisions' in data:                         return 'theological'
    if 'citations' in data and 'text_form_distribution' in data: return 'patristic'
    return 'unknown'


def main() -> None:
    parser = argparse.ArgumentParser(description='Push local cache → Supabase')
    parser.add_argument('--dry-run', action='store_true',
                        help='List files that would be pushed, without writing')
    parser.add_argument('--force', action='store_true',
                        help='Upsert (overwrite) existing rows (default: skip existing)')
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit('ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env or environment.')

    try:
        from supabase import create_client
    except ImportError:
        sys.exit('ERROR: supabase package not installed. Run: pip install supabase')

    if not os.path.isdir(CACHE_DIR):
        sys.exit(f'ERROR: cache directory not found: {CACHE_DIR}')

    _SKIP = {'budget.json', 'votes.json'}
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.json') and f not in _SKIP]
    print(f'Found {len(files)} JSON file(s) in {CACHE_DIR}/')

    if args.dry_run:
        for fn in sorted(files):
            with open(os.path.join(CACHE_DIR, fn), encoding='utf-8') as fp:
                data = json.load(fp)
            key  = fn[:-5]
            kind = _detect_type(data)
            ref  = data.get('reference', data.get('book', '?'))
            print(f'  {key[:16]}…  type={kind:14s}  ref={ref}')
        print('Dry-run complete — nothing pushed.')
        return

    client   = create_client(SUPABASE_URL, SUPABASE_KEY)
    pushed   = 0
    skipped  = 0

    for fn in sorted(files):
        path = os.path.join(CACHE_DIR, fn)
        with open(path, encoding='utf-8') as fp:
            data = json.load(fp)

        key  = fn[:-5]
        kind = _detect_type(data)
        ref  = data.get('reference', data.get('book', ''))

        if not args.force:
            # Check if already exists
            existing = (client.table('analysis_cache')
                        .select('cache_key')
                        .eq('cache_key', key)
                        .execute())
            if existing.data:
                skipped += 1
                continue

        client.table('analysis_cache').upsert({
            'cache_key':      key,
            'tool':           kind,
            'reference':      ref,
            'data':           data,
            'prompt_version': 'v1',
            'model_version':  data.get('model', 'unknown'),
            'discovery_ready': kind in ('divergence', 'scribal', 'numerical', 'backtranslation', 'dss', 'theological', 'patristic', 'genealogy'),
        }).execute()
        pushed += 1
        print(f'  ✓  {key[:16]}…  {kind}  {ref}')

    print(f'\n✅  Pushed {pushed} row(s).  Skipped {skipped} already-existing row(s).')
    print('    Use --force to overwrite existing rows.')


if __name__ == '__main__':
    main()
