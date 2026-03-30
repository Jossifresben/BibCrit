"""Claude API pipeline with disk caching and budget tracking.

Cache key = sha256(reference | tool | prompt_version | model_version)
Budget: data/cache/budget.json tracks monthly spend in USD.
"""

import hashlib
import json
import os
import re
import threading
from datetime import datetime

DIVERGENCE_MODEL = 'claude-3-5-sonnet-20241022'

_SONNET_COST_IN  = 3.0  / 1_000_000   # $3 per MTok input
_SONNET_COST_OUT = 15.0 / 1_000_000   # $15 per MTok output

_DIVERGENCE_SYSTEM = (
    "You are a specialist in biblical textual criticism with deep expertise in "
    "Masoretic Hebrew, Septuagint Greek, Dead Sea Scrolls, and the history of the "
    "biblical text. You apply rigorous scholarly methodology. Always return valid JSON."
)


class ClaudePipeline:
    """Manages Claude API calls, caching, and monthly budget tracking."""

    def __init__(self, data_dir: str, api_key: str, cap_usd: float = 5.0) -> None:
        self._data_dir = data_dir
        self._cache_dir = os.path.join(data_dir, 'cache')
        self._prompts_dir = os.path.join(data_dir, 'prompts')
        self._budget_path = os.path.join(self._cache_dir, 'budget.json')
        self._cap_usd = cap_usd
        self._client = None
        self._budget_lock = threading.Lock()

        os.makedirs(self._cache_dir, exist_ok=True)

        if api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                pass

    # ── Public interface ───────────────────────────────────────────────────

    @property
    def cache_dir(self) -> str:
        """Public accessor for the cache directory path."""
        return self._cache_dir

    # ── Cache ──────────────────────────────────────────────────────────────

    def _cache_key(self, reference: str, tool: str,
                   prompt_version: str, model: str) -> str:
        payload = f'{reference}|{tool}|{prompt_version}|{model}'
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def _cache_path(self, key: str) -> str:
        return os.path.join(self._cache_dir, f'{key}.json')

    def get_cached(self, reference: str, tool: str,
                   prompt_version: str, model: str):
        """Return cached result dict or None if not found."""
        key = self._cache_key(reference, tool, prompt_version, model)
        path = self._cache_path(key)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_cache(self, reference: str, tool: str,
                   prompt_version: str, model: str, data: dict) -> None:
        """Write result to cache with metadata."""
        key = self._cache_key(reference, tool, prompt_version, model)
        path = self._cache_path(key)
        data['cached_at'] = datetime.utcnow().isoformat()
        data['model_version'] = model
        data['prompt_version'] = prompt_version
        data.setdefault('discovery_ready', False)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Budget ─────────────────────────────────────────────────────────────

    def get_budget(self) -> dict:
        """Return current monthly budget dict: {month, spend_usd, cap_usd}."""
        if os.path.exists(self._budget_path):
            with open(self._budget_path, 'r') as f:
                stored = json.load(f)
            if stored.get('month') == datetime.utcnow().strftime('%Y-%m'):
                stored['cap_usd'] = self._cap_usd
                return stored
        return {
            'month': datetime.utcnow().strftime('%Y-%m'),
            'spend_usd': 0.0,
            'cap_usd': self._cap_usd,
        }

    def record_spend(self, amount_usd: float) -> None:
        """Add amount to this month's spend total (thread-safe read-modify-write)."""
        with self._budget_lock:
            budget = self.get_budget()
            budget['spend_usd'] = round(budget['spend_usd'] + amount_usd, 6)
            with open(self._budget_path, 'w') as f:
                json.dump(budget, f)

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
        On error (no API key, parse failure): returns {'error': ..., 'divergences': []}.
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
