"""Claude API pipeline with Supabase caching and budget tracking.

Cache key = sha256(reference | tool | prompt_version | model_version)
Budget: supabase `budget` table tracks monthly spend in USD.
Falls back to disk cache (data/cache/) if Supabase is unavailable.
"""

import hashlib
import json
import os
import re
import threading
from datetime import datetime

DIVERGENCE_MODEL = 'claude-sonnet-4-5-20250929'

_SONNET_COST_IN  = 3.0  / 1_000_000   # $3 per MTok input (claude-sonnet-4-5)
_SONNET_COST_OUT = 15.0 / 1_000_000   # $15 per MTok output (claude-sonnet-4-5)

_DIVERGENCE_SYSTEM = (
    "You are a specialist in biblical textual criticism with deep expertise in "
    "Masoretic Hebrew, Septuagint Greek, Dead Sea Scrolls, and the history of the "
    "biblical text. You apply rigorous scholarly methodology. Always return valid JSON."
)


class ClaudePipeline:
    """Manages Claude API calls, Supabase caching, and monthly budget tracking."""

    def __init__(self, data_dir: str, api_key: str, cap_usd: float = 5.0,
                 supabase_url: str = '', supabase_key: str = '') -> None:
        self._data_dir = data_dir
        self._cache_dir = os.path.join(data_dir, 'cache')
        self._prompts_dir = os.path.join(data_dir, 'prompts')
        self._budget_path = os.path.join(self._cache_dir, 'budget.json')
        self._cap_usd = cap_usd
        self._client = None
        self._supabase = None
        self._budget_lock = threading.Lock()

        os.makedirs(self._cache_dir, exist_ok=True)

        if api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                pass

        if supabase_url and supabase_key:
            try:
                from supabase import create_client
                self._supabase = create_client(supabase_url, supabase_key)
            except ImportError:
                pass

    # ── Public interface ───────────────────────────────────────────────────

    @property
    def cache_dir(self) -> str:
        """Public accessor for the local cache directory path."""
        return self._cache_dir

    # ── Cache key ──────────────────────────────────────────────────────────

    def _cache_key(self, reference: str, tool: str,
                   prompt_version: str, model: str) -> str:
        payload = f'{reference}|{tool}|{prompt_version}|{model}'
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    # ── Supabase cache ─────────────────────────────────────────────────────

    def get_cached(self, reference: str, tool: str,
                   prompt_version: str, model: str):
        """Return cached result dict or None. Checks Supabase first, then disk."""
        key = self._cache_key(reference, tool, prompt_version, model)

        # 1. Try Supabase
        if self._supabase:
            try:
                result = (
                    self._supabase.table('analysis_cache')
                    .select('data, cached_at, model_version, prompt_version, discovery_ready')
                    .eq('cache_key', key)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    row = result.data[0]
                    data = row['data']
                    data['cached_at'] = row['cached_at']
                    data['model_version'] = row['model_version']
                    data['prompt_version'] = row['prompt_version']
                    data['discovery_ready'] = row['discovery_ready']
                    return data
            except Exception:
                pass  # fall through to disk

        # 2. Fall back to disk
        path = os.path.join(self._cache_dir, f'{key}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None

    def save_cache(self, reference: str, tool: str,
                   prompt_version: str, model: str, data: dict) -> None:
        """Write result to Supabase cache (and disk as fallback)."""
        key = self._cache_key(reference, tool, prompt_version, model)
        now = datetime.utcnow().isoformat()
        data.setdefault('discovery_ready', False)
        data['reference'] = reference

        # 1. Save to Supabase
        if self._supabase:
            try:
                self._supabase.table('analysis_cache').upsert({
                    'cache_key':      key,
                    'reference':      reference,
                    'tool':           tool,
                    'prompt_version': prompt_version,
                    'model_version':  model,
                    'data':           data,
                    'cached_at':      now,
                    'discovery_ready': data['discovery_ready'],
                }).execute()
            except Exception:
                pass  # fall through to disk

        # 2. Always write disk copy as fallback
        data['cached_at'] = now
        data['model_version'] = model
        data['prompt_version'] = prompt_version
        path = os.path.join(self._cache_dir, f'{key}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Budget ─────────────────────────────────────────────────────────────

    def get_budget(self) -> dict:
        """Return current monthly budget dict: {month, spend_usd, cap_usd}."""
        current_month = datetime.utcnow().strftime('%Y-%m')

        if self._supabase:
            try:
                result = (
                    self._supabase.table('budget')
                    .select('month, spend_usd, cap_usd')
                    .eq('month', current_month)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    row = result.data[0]
                    return {
                        'month':     row['month'],
                        'spend_usd': float(row['spend_usd']),
                        'cap_usd':   self._cap_usd,
                    }
            except Exception:
                pass  # fall through to disk

        # Disk fallback
        if os.path.exists(self._budget_path):
            with open(self._budget_path, 'r') as f:
                stored = json.load(f)
            if stored.get('month') == current_month:
                stored['cap_usd'] = self._cap_usd
                return stored

        return {'month': current_month, 'spend_usd': 0.0, 'cap_usd': self._cap_usd}

    def record_spend(self, amount_usd: float) -> None:
        """Add amount to this month's spend total (thread-safe)."""
        current_month = datetime.utcnow().strftime('%Y-%m')

        with self._budget_lock:
            budget = self.get_budget()
            new_spend = round(budget['spend_usd'] + amount_usd, 6)

            if self._supabase:
                try:
                    self._supabase.table('budget').upsert({
                        'month':      current_month,
                        'spend_usd':  new_spend,
                        'cap_usd':    self._cap_usd,
                        'updated_at': datetime.utcnow().isoformat(),
                    }).execute()
                except Exception:
                    pass  # fall through to disk

            # Disk fallback
            disk_budget = {'month': current_month, 'spend_usd': new_spend, 'cap_usd': self._cap_usd}
            with open(self._budget_path, 'w') as f:
                json.dump(disk_budget, f)

    # ── Discovery cards ────────────────────────────────────────────────────

    def get_discovery_cards(self, min_confidence: float = 0.6, limit: int = 12) -> list:
        """Return high-confidence discovery-ready divergence records."""
        cards = []

        if self._supabase:
            try:
                result = (
                    self._supabase.table('analysis_cache')
                    .select('reference, data')
                    .eq('discovery_ready', True)
                    .execute()
                )
                for row in result.data:
                    cards.extend(_extract_cards(row['reference'], row['data'], min_confidence))
                return sorted(cards, key=lambda c: c['confidence'], reverse=True)[:limit]
            except Exception:
                pass  # fall through to disk

        # Disk fallback
        if not os.path.isdir(self._cache_dir):
            return []
        for filename in os.listdir(self._cache_dir):
            if not filename.endswith('.json') or filename == 'budget.json':
                continue
            path = os.path.join(self._cache_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if data.get('discovery_ready'):
                cards.extend(_extract_cards(data.get('reference', ''), data, min_confidence))

        return sorted(cards, key=lambda c: c['confidence'], reverse=True)[:limit]

    # ── Prompts ────────────────────────────────────────────────────────────

    def load_prompt(self, tool: str, version: str = 'v1') -> str:
        """Load versioned prompt template from data/prompts/{tool}_{version}.txt."""
        path = os.path.join(self._prompts_dir, f'{tool}_{version}.txt')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return ''

    # ── Analysis ───────────────────────────────────────────────────────────

    def analyze_divergence(self, reference: str, mt_text: str,
                           lxx_text: str) -> dict:
        """Return divergence analysis. Checks cache first.

        Returns dict with 'divergences', 'summary_technical', 'summary_plain'.
        On error (no API key, budget exceeded, parse failure): returns {'error': ..., 'divergences': []}.
        """
        model = DIVERGENCE_MODEL
        prompt_version = 'v1'

        cached = self.get_cached(reference, 'divergence', prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'divergences': [],
                'summary_technical': '',
                'summary_plain': '',
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'divergences': [],
                'summary_technical': '',
                'summary_plain': '',
            }

        template = self.load_prompt('divergence', prompt_version)
        user_content = (
            template
            .replace('{{REFERENCE}}', reference)
            .replace('{{MT_TEXT}}', mt_text)
            .replace('{{LXX_TEXT}}', lxx_text)
        ) if template else (
            f'Reference: {reference}\nMT: {mt_text}\nLXX: {lxx_text}\n'
            'Analyze divergences. Return JSON with divergences array.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=4096,
            system=_DIVERGENCE_SYSTEM,
            messages=[{'role': 'user', 'content': user_content}],
        )

        cost = (response.usage.input_tokens * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw = response.content[0].text
        data = _parse_json_response(raw)
        self.save_cache(reference, 'divergence', prompt_version, model, data)
        return data


def _extract_cards(reference: str, data: dict, min_confidence: float) -> list:
    """Extract discovery cards from a cached analysis dict."""
    cards = []
    for div in data.get('divergences', []):
        if div.get('analysis_plain') and div.get('confidence', 0) >= min_confidence:
            cards.append({
                'reference':       reference,
                'mt_word':         div.get('mt_word', ''),
                'lxx_word':        div.get('lxx_word', ''),
                'divergence_type': div.get('divergence_type', ''),
                'confidence':      div.get('confidence', 0.0),
                'analysis_plain':  div.get('analysis_plain', ''),
                'summary_plain':   data.get('summary_plain', ''),
                'cached_at':       data.get('cached_at', ''),
            })
    return cards


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from Claude response, handling markdown fences."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r'```(?:json)?\s*\n(.*?)\n```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return {
        'divergences': [],
        'summary_technical': '',
        'summary_plain': '',
        'parse_error': raw[:500],
    }
