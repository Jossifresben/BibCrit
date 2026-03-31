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

DIVERGENCE_MODEL  = 'claude-sonnet-4-5-20250929'
SCRIBAL_MODEL     = 'claude-sonnet-4-5-20250929'
NUMERICAL_MODEL   = 'claude-sonnet-4-5-20250929'
DSS_MODEL         = 'claude-sonnet-4-5-20250929'
THEOLOGICAL_MODEL = 'claude-sonnet-4-5-20250929'
PATRISTIC_MODEL   = 'claude-sonnet-4-5-20250929'
GENEALOGY_MODEL   = 'claude-sonnet-4-5-20250929'

_SONNET_COST_IN  = 3.0  / 1_000_000   # $3 per MTok input (claude-sonnet-4-5)
_SONNET_COST_OUT = 15.0 / 1_000_000   # $15 per MTok output (claude-sonnet-4-5)

# Diagnostic passages used to build sample_passages for scribal profiling
_SCRIBAL_SAMPLE_REFS = {
    'Isaiah':      ['Isaiah 7:14', 'Isaiah 9:6', 'Isaiah 11:1', 'Isaiah 40:3',
                    'Isaiah 42:1', 'Isaiah 52:13', 'Isaiah 53:4', 'Isaiah 61:1'],
    'Jeremiah':    ['Jeremiah 1:5', 'Jeremiah 23:5', 'Jeremiah 31:31', 'Jeremiah 33:15'],
    'Psalms':      ['Psalm 2:7', 'Psalm 22:1', 'Psalm 22:17', 'Psalm 45:7', 'Psalm 110:1'],
    'Genesis':     ['Genesis 1:1', 'Genesis 1:26', 'Genesis 3:15', 'Genesis 18:1'],
    'Deuteronomy': ['Deuteronomy 18:15', 'Deuteronomy 32:8', 'Deuteronomy 32:43'],
    'Exodus':      ['Exodus 3:14', 'Exodus 24:10', 'Exodus 33:23'],
    'Proverbs':    ['Proverbs 8:22', 'Proverbs 8:30'],
    'Job':         ['Job 19:25', 'Job 38:7'],
    'Micah':       ['Micah 5:2', 'Micah 5:4'],
    'Zechariah':   ['Zechariah 9:9', 'Zechariah 12:10', 'Zechariah 13:7'],
}

_DIVERGENCE_SYSTEM = (
    "You are a specialist in biblical textual criticism with deep expertise in "
    "Masoretic Hebrew, Septuagint Greek, Dead Sea Scrolls, and the history of the "
    "biblical text. You apply rigorous scholarly methodology. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_BACKTRANSLATION_SYSTEM = (
    "You are a specialist in Septuagint studies and Hebrew retroversion, with deep "
    "expertise in LXX translation technique, Tov's retroversion methodology, and "
    "Dead Sea Scrolls textual witnesses. You reconstruct probable Hebrew Vorlagen "
    "from Greek LXX text with rigorous scholarly precision. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_SCRIBAL_SYSTEM = (
    "You are a specialist in Septuagint translation technique, with deep expertise "
    "in the work of individual LXX translators, the degree of literalness of "
    "different LXX books, and the theological and hermeneutical tendencies of "
    "ancient translators. You apply the methods of Aejmelaeus, Tov, and de Waard. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_NUMERICAL_SYSTEM = (
    "You are a specialist in biblical textual criticism with deep expertise in the "
    "numerical divergences between the Masoretic Text, the Septuagint, and the "
    "Samaritan Pentateuch, particularly the patriarchal chronologies. You apply "
    "rigorous mathematical and text-critical analysis. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_DSS_SYSTEM = (
    "You are a specialist in Dead Sea Scrolls textual criticism with deep expertise "
    "in the biblical scrolls from Qumran, their relationship to the proto-MT, "
    "proto-LXX, and independent traditions, applying the methodology of Emanuel Tov "
    "and Eugene Ulrich. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_THEOLOGICAL_SYSTEM = (
    "You are a specialist in biblical theology and textual criticism with deep expertise "
    "in theologically motivated textual changes: anthropomorphism avoidance in the LXX "
    "and Targums, messianic heightening, harmonization tendencies, and proto-rabbinic "
    "revision. You apply the methodology of Caird, Schaper, van der Kooij, and de Waard. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_PATRISTIC_SYSTEM = (
    "You are a specialist in patristic biblical citation with deep expertise in how "
    "the Church Fathers cited the Old Testament, the text forms they used (proto-MT, "
    "proto-LXX, Old Latin, Vetus Latina), and what their citations imply for the "
    "history of the biblical text. You apply the methodology of Metzger, Hengel, "
    "and the Göttingen LXX critical apparatus. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_GENEALOGY_SYSTEM = (
    "You are a specialist in the manuscript transmission and stemmatic history of the "
    "Hebrew Bible / Old Testament, with deep expertise in the Masoretic Text, the "
    "Septuagint and its recensions, the Dead Sea Scrolls, and the ancient versions "
    "(Peshitta, Targum, Vulgate). You apply the methodology of Tov, Barthélemy, "
    "Cross, and the editors of BHQ and the Göttingen Septuagint. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_TRANSLATION_SYSTEM = (
    "You are a professional translator specializing in biblical textual criticism. "
    "Translate a JSON object from English to Spanish. "
    "PRESERVE EXACTLY — do not translate: "
    "(1) All JSON field/key names. "
    "(2) Hebrew, Greek, Aramaic, Syriac, or other non-Latin script text. "
    "(3) Manuscript sigla (e.g. 1QIsa-a, 4QSam, P46, Codex B, etc.). "
    "(4) Bible references (e.g. 'Isaiah 7:14', 'Gen 1:1', 'Ps 22:1'). "
    "(5) Scholar surnames and publication titles. "
    "(6) Technical abbreviations: MT, LXX, SP, DSS, BHS, BHQ, OT, NT, NETS, NRSV, etc. "
    "(7) All numbers and numeric values. "
    "(8) Boolean values (true/false) and null. "
    "(9) Values for keys: tool, model, model_version, prompt_version, cached_at, cache_key, "
    "reference, book, siglum, alignment, classification, revision_type, discovery_ready. "
    "Translate all other English prose text values into fluent, academic Spanish. "
    "CRITICAL: Return ONLY raw JSON with exactly the same structure. No markdown, no code fences."
)


class ClaudePipeline:
    """Manages Claude API calls, Supabase caching, and monthly budget tracking."""

    def __init__(self, data_dir: str, api_key: str, cap_usd: float = 10.0,
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

    # ── Spanish cache (analysis_cache_es) ─────────────────────────────────

    def get_cached_es(self, reference: str, tool: str,
                      prompt_version: str, model: str):
        """Return Spanish-translated cached result or None. Supabase only (no disk ES cache)."""
        if not self._supabase:
            return None
        key = self._cache_key(reference, tool, prompt_version, model)
        try:
            result = (
                self._supabase.table('analysis_cache_es')
                .select('data, translated_at, model_version, prompt_version')
                .eq('cache_key', key)
                .limit(1)
                .execute()
            )
            if result.data:
                row = result.data[0]
                data = row['data']
                data['cached_at']     = row['translated_at']
                data['model_version'] = row['model_version']
                data['prompt_version'] = row['prompt_version']
                return data
        except Exception:
            pass
        return None

    def save_cache_es(self, reference: str, tool: str,
                      prompt_version: str, model: str, data: dict) -> None:
        """Write Spanish translation to analysis_cache_es (Supabase only)."""
        if not self._supabase:
            return
        key = self._cache_key(reference, tool, prompt_version, model)
        now = datetime.utcnow().isoformat()
        try:
            self._supabase.table('analysis_cache_es').upsert({
                'cache_key':      key,
                'reference':      reference,
                'tool':           tool,
                'prompt_version': prompt_version,
                'model_version':  model,
                'data':           data,
                'translated_at':  now,
                'source_key':     key,
                'discovery_ready': data.get('discovery_ready', False),
            }).execute()
        except Exception:
            pass

    def translate_to_spanish(self, data: dict, tool: str) -> dict:
        """Return a Spanish-translated copy of an English analysis dict.

        Preserves Hebrew/Greek text, sigla, Bible refs, scholar names,
        technical abbreviations, and all JSON field names unchanged.
        Falls back to the original English dict on any error.
        """
        if not self._client:
            return data

        # Strip ephemeral housekeeping fields before sending to Claude
        translate_data = {k: v for k, v in data.items()
                          if k not in ('cached_at', 'model_version', 'prompt_version',
                                       'discovery_ready', 'mt_words', 'lxx_words')}

        user_content = (
            f'Tool: {tool}\n\n'
            + json.dumps(translate_data, ensure_ascii=False, indent=2)
        )

        try:
            response = self._client.messages.create(
                model=DIVERGENCE_MODEL,
                max_tokens=8192,
                system=_TRANSLATION_SYSTEM,
                messages=[
                    {'role': 'user',      'content': user_content},
                    {'role': 'assistant', 'content': '{'},
                ],
            )
            cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                    response.usage.output_tokens * _SONNET_COST_OUT)
            self.record_spend(cost)

            raw        = '{' + response.content[0].text
            translated = _parse_json_response(raw)
            if translated.get('error'):
                return data  # fallback to English on parse failure
            return translated
        except Exception:
            return data  # fallback to English on API error

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
                    .select('reference, tool, data')
                    .eq('discovery_ready', True)
                    .execute()
                )
                for row in result.data:
                    cards.extend(_extract_cards(row['reference'], row['data'], min_confidence,
                                                tool=row.get('tool', 'divergence')))
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
                tool = _detect_tool(data)
                cards.extend(_extract_cards(data.get('reference', '') or data.get('book', '') or filename[:-5][:32], data, min_confidence, tool=tool))

        return sorted(cards, key=lambda c: c['confidence'], reverse=True)[:limit]

    # ── Discovery helpers ─────────────────────────────────────────────────

    def set_discovery_ready(self, reference: str, ready: bool) -> bool:
        """Mark cached analysis for a reference as discovery_ready.

        Returns True if at least one entry was updated, False if none found.
        """
        updated = False
        prompt_version = 'v2'
        model = DIVERGENCE_MODEL
        key = self._cache_key(reference, 'divergence', prompt_version, model)

        # Update Supabase
        if self._supabase:
            try:
                result = self._supabase.table('analysis_cache').update(
                    {'discovery_ready': ready}
                ).eq('cache_key', key).execute()
                if result.data:
                    updated = True
            except Exception:
                pass

        # Update disk
        path = os.path.join(self._cache_dir, f'{key}.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['discovery_ready'] = ready
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                updated = True
            except (json.JSONDecodeError, OSError):
                pass

        return updated

    def get_all_analysis_cards(self, min_confidence: float = 0.6,
                               limit: int = 12) -> list:
        """Return cards from ALL cached analyses (ignores discovery_ready flag).

        Used in demo / early-content mode when fewer than 3 curated entries exist.
        """
        cards = []

        if self._supabase:
            try:
                result = (
                    self._supabase.table('analysis_cache')
                    .select('reference, tool, data')
                    .execute()
                )
                for row in result.data:
                    cards.extend(_extract_cards(row['reference'], row['data'],
                                                min_confidence,
                                                tool=row.get('tool', 'divergence')))
                return sorted(cards, key=lambda c: c['confidence'],
                               reverse=True)[:limit]
            except Exception:
                pass

        # Disk fallback
        if not os.path.isdir(self._cache_dir):
            return []
        for filename in os.listdir(self._cache_dir):
            if not filename.endswith('.json') or filename in (
                    'budget.json', 'votes.json'):
                continue
            path = os.path.join(self._cache_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            tool = _detect_tool(data)
            cards.extend(_extract_cards(data.get('reference', '') or data.get('book', '') or filename[:-5][:32], data,
                                        min_confidence, tool=tool))

        return sorted(cards, key=lambda c: c['confidence'],
                      reverse=True)[:limit]

    def get_discovery_stats(self) -> dict:
        """Return aggregate stats: total passages analyzed, total divergences."""
        passages = 0
        divergences = 0

        if self._supabase:
            try:
                result = (
                    self._supabase.table('analysis_cache')
                    .select('data')
                    .execute()
                )
                for row in result.data:
                    passages += 1
                    divergences += len(row['data'].get('divergences', []))
                return {'passages': passages, 'divergences': divergences}
            except Exception:
                pass

        # Disk fallback
        if not os.path.isdir(self._cache_dir):
            return {'passages': 0, 'divergences': 0}
        for filename in os.listdir(self._cache_dir):
            if not filename.endswith('.json') or filename in (
                    'budget.json', 'votes.json'):
                continue
            path = os.path.join(self._cache_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                passages += 1
                divergences += len(data.get('divergences', []))
            except (json.JSONDecodeError, OSError):
                continue

        return {'passages': passages, 'divergences': divergences}

    # ── Prompts ────────────────────────────────────────────────────────────

    def load_prompt(self, tool: str, version: str = 'v1') -> str:
        """Load versioned prompt template from data/prompts/{tool}_{version}.txt."""
        path = os.path.join(self._prompts_dir, f'{tool}_{version}.txt')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return ''

    # ── Analysis ───────────────────────────────────────────────────────────

    def analyze_backtranslation(self, reference: str, lxx_text: str,
                                mt_text: str) -> dict:
        """Return back-translation (Vorlage reconstruction) analysis.

        Returns dict with 'reconstructed_words', 'summary_technical', etc.
        On error: returns {'error': ..., 'reconstructed_words': [], ...}.
        """
        model          = DIVERGENCE_MODEL
        prompt_version = 'v1'
        tool           = 'backtranslation'

        cached = self.get_cached(reference, tool, prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'reconstructed_words': [],
                'summary_technical': '',
                'summary_plain': '',
                'overall_confidence': 0.0,
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'reconstructed_words': [],
                'summary_technical': '',
                'summary_plain': '',
                'overall_confidence': 0.0,
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        template = self.load_prompt('backtranslation', prompt_version)
        user_content = (
            template
            .replace('{{REFERENCE}}', reference)
            .replace('{{LXX_TEXT}}', lxx_text)
            .replace('{{MT_TEXT}}',  mt_text)
        ) if template else (
            f'Reference: {reference}\nLXX: {lxx_text}\nMT: {mt_text}\n'
            'Reconstruct the Hebrew Vorlage. Return JSON with reconstructed_words array.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=8192,
            system=_BACKTRANSLATION_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},
            ],
        )

        cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw  = '{' + response.content[0].text
        data = _parse_json_response(raw)
        self.save_cache(reference, tool, prompt_version, model, data)
        return data

    def analyze_scribal(self, book_name: str, sample_passages: str) -> dict:
        """Return scribal tendency profile for an LXX book.

        Returns dict with 'translator_profile', 'dimensions', etc.
        On error: returns {'error': ..., 'translator_profile': {}, 'dimensions': []}.
        """
        model          = SCRIBAL_MODEL
        prompt_version = 'v1'
        tool           = 'scribal'

        cached = self.get_cached(book_name, tool, prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'book': book_name, 'translator_name': '', 'translator_profile': {},
                'dimensions': [], 'overall_assessment': '', 'overall_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'book': book_name, 'translator_name': '', 'translator_profile': {},
                'dimensions': [], 'overall_assessment': '', 'overall_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        template = self.load_prompt('scribal', prompt_version)
        user_content = (
            template
            .replace('{{BOOK_NAME}}', book_name)
            .replace('{{SAMPLE_PASSAGES}}', sample_passages)
        ) if template else (
            f'Book: {book_name}\nSample passages:\n{sample_passages}\n'
            'Profile this LXX translator. Return JSON with translator_profile and dimensions.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=8192,
            system=_SCRIBAL_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},
            ],
        )

        cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw  = '{' + response.content[0].text
        data = _parse_json_response(raw)
        self.save_cache(book_name, tool, prompt_version, model, data)
        return data

    def analyze_numerical(self, reference: str) -> dict:
        """Return numerical discrepancy analysis for a passage.

        Returns dict with 'figures', 'systematic_analysis', 'theories', etc.
        On error: returns {'error': ..., 'figures': [], 'theories': []}.
        """
        model          = NUMERICAL_MODEL
        prompt_version = 'v1'
        tool           = 'numerical'

        cached = self.get_cached(reference, tool, prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'reference': reference, 'subject': '', 'figures': [],
                'systematic_analysis': {'is_systematic': False, 'pattern': '', 'pattern_plain': ''},
                'theories': [], 'overall_assessment': '', 'overall_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'reference': reference, 'subject': '', 'figures': [],
                'systematic_analysis': {'is_systematic': False, 'pattern': '', 'pattern_plain': ''},
                'theories': [], 'overall_assessment': '', 'overall_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        template = self.load_prompt('numerical', prompt_version)
        user_content = (
            template.replace('{{REFERENCE}}', reference)
        ) if template else (
            f'Reference: {reference}\n'
            'Analyze numerical divergences between MT, LXX, and SP. Return JSON.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=8192,
            system=_NUMERICAL_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},
            ],
        )

        cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw  = '{' + response.content[0].text
        data = _parse_json_response(raw)
        self.save_cache(reference, tool, prompt_version, model, data)
        return data

    def analyze_dss(self, reference: str, mt_text: str = '',
                    lxx_text: str = '') -> dict:
        """Return DSS bridge analysis comparing MT, LXX, and Dead Sea Scrolls.

        Returns dict with 'dss_manuscripts', 'synthesis', 'synthesis_plain', etc.
        On error: returns {'error': ..., 'dss_manuscripts': [], ...}.
        """
        model          = DSS_MODEL
        prompt_version = 'v1'
        tool           = 'dss'

        cached = self.get_cached(reference, tool, prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'reference': reference, 'dss_manuscripts': [],
                'synthesis': '', 'synthesis_plain': '', 'textual_history_implication': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'reference': reference, 'dss_manuscripts': [],
                'synthesis': '', 'synthesis_plain': '', 'textual_history_implication': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        template = self.load_prompt('dss', prompt_version)
        user_content = (
            template
            .replace('{{REFERENCE}}', reference)
            .replace('{{MT_TEXT}}', mt_text)
            .replace('{{LXX_TEXT}}', lxx_text)
        ) if template else (
            f'Reference: {reference}\nMT: {mt_text}\nLXX: {lxx_text}\n'
            'Compare MT, LXX, and DSS witnesses. Return JSON with dss_manuscripts array.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=8192,
            system=_DSS_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},
            ],
        )

        cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw  = '{' + response.content[0].text
        data = _parse_json_response(raw)
        self.save_cache(reference, tool, prompt_version, model, data)
        return data

    def analyze_theological(self, reference: str) -> dict:
        """Return theologically motivated revision analysis for a book or passage.

        Returns dict with 'revisions', 'summary', 'overall_assessment', etc.
        On error: returns {'error': ..., 'revisions': [], ...}.
        """
        model          = THEOLOGICAL_MODEL
        prompt_version = 'v1'
        tool           = 'theological'

        cached = self.get_cached(reference, tool, prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'scope': reference, 'revisions': [], 'summary': '', 'summary_plain': '',
                'overall_assessment': '', 'overall_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'scope': reference, 'revisions': [], 'summary': '', 'summary_plain': '',
                'overall_assessment': '', 'overall_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        template = self.load_prompt('theological', prompt_version)
        user_content = (
            template.replace('{{REFERENCE}}', reference)
        ) if template else (
            f'Reference: {reference}\n'
            'Identify theologically motivated textual changes. Return JSON with revisions array.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=8192,
            system=_THEOLOGICAL_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},
            ],
        )

        cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw  = '{' + response.content[0].text
        data = _parse_json_response(raw)
        self.save_cache(reference, tool, prompt_version, model, data)
        return data

    def analyze_patristic(self, reference: str) -> dict:
        """Return patristic citation analysis for a passage.

        Returns dict with 'citations', 'transmission_synthesis', etc.
        On error: returns {'error': ..., 'citations': [], ...}.
        """
        model          = PATRISTIC_MODEL
        prompt_version = 'v1'
        tool           = 'patristic'

        cached = self.get_cached(reference, tool, prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'reference': reference, 'citations': [],
                'transmission_synthesis': '', 'transmission_synthesis_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'reference': reference, 'citations': [],
                'transmission_synthesis': '', 'transmission_synthesis_plain': '',
                'bibcrit_assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            }

        template = self.load_prompt('patristic', prompt_version)
        user_content = (
            template.replace('{{REFERENCE}}', reference)
        ) if template else (
            f'Reference: {reference}\n'
            'Trace patristic citations and text forms. Return JSON with citations array.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=8192,
            system=_PATRISTIC_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},
            ],
        )

        cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw  = '{' + response.content[0].text
        data = _parse_json_response(raw)
        self.save_cache(reference, tool, prompt_version, model, data)
        return data

    def analyze_genealogy(self, book: str) -> dict:
        """Return manuscript transmission genealogy (stemma) for a biblical book.

        Returns dict with 'stemma_nodes', 'stemma_edges', 'key_divergences', etc.
        On error: returns {'error': ..., 'stemma_nodes': [], 'stemma_edges': [], ...}.
        """
        model          = GENEALOGY_MODEL
        prompt_version = 'v1'
        tool           = 'genealogy'

        cached = self.get_cached(book, tool, prompt_version, model)
        if cached:
            return cached

        if not self._client:
            return {
                'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
                'book': book, 'stemma_nodes': [], 'stemma_edges': [],
                'key_divergences': [], 'transmission_narrative': '',
                'transmission_plain': '', 'archetype_description': '',
                'bibcrit_assessment': {'title': '', 'plain': '', 'confidence': 0.0},
            }

        budget = self.get_budget()
        if budget['spend_usd'] >= self._cap_usd:
            return {
                'error': (
                    f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                    "Please try again next month or donate to increase the cap."
                ),
                'book': book, 'stemma_nodes': [], 'stemma_edges': [],
                'key_divergences': [], 'transmission_narrative': '',
                'transmission_plain': '', 'archetype_description': '',
                'bibcrit_assessment': {'title': '', 'plain': '', 'confidence': 0.0},
            }

        template = self.load_prompt('genealogy', prompt_version)
        user_content = (
            template.replace('{{BOOK}}', book)
        ) if template else (
            f'Book: {book}\n'
            'Construct a manuscript transmission genealogy (stemma). Return JSON with stemma_nodes and stemma_edges arrays.'
        )

        response = self._client.messages.create(
            model=model,
            max_tokens=8192,
            system=_GENEALOGY_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},
            ],
        )

        cost = (response.usage.input_tokens  * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw  = '{' + response.content[0].text
        data = _parse_json_response(raw)
        data['discovery_ready'] = True
        self.save_cache(book, tool, prompt_version, model, data)
        return data

    def analyze_divergence(self, reference: str, mt_text: str,
                           lxx_text: str) -> dict:
        """Return divergence analysis. Checks cache first.

        Returns dict with 'divergences', 'summary_technical', 'summary_plain'.
        On error (no API key, budget exceeded, parse failure): returns {'error': ..., 'divergences': []}.
        """
        model = DIVERGENCE_MODEL
        prompt_version = 'v2'

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
            max_tokens=8192,
            system=_DIVERGENCE_SYSTEM,
            messages=[
                {'role': 'user',      'content': user_content},
                {'role': 'assistant', 'content': '{'},  # pre-fill: forces raw JSON, no fence
            ],
        )

        cost = (response.usage.input_tokens * _SONNET_COST_IN +
                response.usage.output_tokens * _SONNET_COST_OUT)
        self.record_spend(cost)

        raw = '{' + response.content[0].text  # prepend the pre-filled opening brace
        data = _parse_json_response(raw)
        self.save_cache(reference, 'divergence', prompt_version, model, data)
        return data


_DISCOVERY_TYPES = {'translation_idiom', 'different_vorlage', 'theological_tendency',
                    'omission', 'addition', 'scribal_error'}


def _detect_tool(data: dict) -> str:
    if 'divergences' in data:         return 'divergence'
    if 'revisions' in data:           return 'theological'
    if 'dss_manuscripts' in data:     return 'dss'
    if 'back_translations' in data:   return 'backtranslation'
    if 'figures' in data:             return 'numerical'
    if 'dimensions' in data:          return 'scribal'
    if 'citations' in data:           return 'patristic'
    if 'stemma_nodes' in data:        return 'genealogy'
    return 'divergence'


def _extract_cards(reference: str, data: dict, min_confidence: float,
                   tool: str = 'divergence') -> list:
    """Extract discovery cards from a cached analysis dict, for any tool."""
    if tool == 'divergence':
        return _extract_cards_divergence(reference, data, min_confidence)
    if tool == 'theological':
        return _extract_cards_theological(reference, data, min_confidence)
    if tool == 'patristic':
        return _extract_cards_patristic(reference, data, min_confidence)
    if tool == 'dss':
        return _extract_cards_dss(reference, data, min_confidence)
    if tool == 'backtranslation':
        return _extract_cards_backtranslation(reference, data, min_confidence)
    if tool == 'numerical':
        return _extract_cards_numerical(reference, data, min_confidence)
    if tool == 'scribal':
        return _extract_cards_scribal(reference, data, min_confidence)
    if tool == 'genealogy':
        return _extract_cards_genealogy(reference, data, min_confidence)
    return []


def _extract_cards_divergence(reference: str, data: dict, min_confidence: float) -> list:
    cards = []
    for div in data.get('divergences', []):
        dtype = div.get('divergence_type', '')
        if dtype not in _DISCOVERY_TYPES:
            continue
        if div.get('analysis_plain') and div.get('confidence', 0) >= min_confidence:
            cards.append({
                'reference':       reference,
                'tool':            'divergence',
                'card_type':       dtype,
                'divergence_type': dtype,   # keep for backward compat
                'mt_word':         div.get('mt_word', ''),
                'lxx_word':        div.get('lxx_word', ''),
                'headline':        '',
                'analysis_plain':  div.get('analysis_plain', ''),
                'summary_plain':   data.get('summary_plain', ''),
                'confidence':      div.get('confidence', 0.0),
                'cached_at':       data.get('cached_at', ''),
                'link':            f'/divergence?ref={reference}',
            })
    return cards


def _extract_cards_theological(reference: str, data: dict, min_confidence: float) -> list:
    cards = []
    summ = data.get('summary_plain', '')
    for rev in data.get('revisions', []):
        conf = rev.get('confidence', 0)
        plain = rev.get('plain_description', '') or rev.get('plain', '')
        if plain and conf >= min_confidence:
            cards.append({
                'reference':       reference,
                'tool':            'theological',
                'card_type':       rev.get('category', 'theological_revision'),
                'divergence_type': rev.get('category', 'theological_revision'),
                'mt_word':         '',
                'lxx_word':        '',
                'headline':        rev.get('category', '').replace('_', ' ').title(),
                'analysis_plain':  plain,
                'summary_plain':   summ,
                'confidence':      conf,
                'cached_at':       data.get('cached_at', ''),
                'link':            f'/theological?ref={reference}',
            })
    return cards[:3]  # cap at 3 per passage


def _extract_cards_patristic(reference: str, data: dict, min_confidence: float) -> list:
    ass = data.get('bibcrit_assessment', {})
    plain = ass.get('plain', '') or data.get('transmission_synthesis_plain', '')
    conf  = ass.get('confidence', 0) or 0.7
    if not plain or conf < min_confidence:
        return []
    total = data.get('total_citations_found', 0)
    headline = f'{total} patristic citation{"s" if total != 1 else ""}' if total else 'Patristic citations'
    return [{
        'reference':       reference,
        'tool':            'patristic',
        'card_type':       'patristic_citations',
        'divergence_type': 'patristic_citations',
        'mt_word':         '',
        'lxx_word':        '',
        'headline':        headline,
        'analysis_plain':  plain,
        'summary_plain':   data.get('period_summary', ''),
        'confidence':      conf,
        'cached_at':       data.get('cached_at', ''),
        'link':            f'/patristic?ref={reference}',
    }]


def _extract_cards_dss(reference: str, data: dict, min_confidence: float) -> list:
    ass = data.get('bibcrit_assessment', {})
    plain = ass.get('plain', '') or data.get('synthesis_plain', '')
    conf  = ass.get('confidence', 0) or 0.7
    if not plain or conf < min_confidence:
        return []
    ms_count = len([m for m in data.get('dss_manuscripts', []) if m.get('verse_present')])
    headline = f'{ms_count} DSS scroll{"s" if ms_count != 1 else ""} attest this passage' if ms_count else 'DSS witness'
    return [{
        'reference':       reference,
        'tool':            'dss',
        'card_type':       'dss_witness',
        'divergence_type': 'dss_witness',
        'mt_word':         '',
        'lxx_word':        '',
        'headline':        headline,
        'analysis_plain':  plain,
        'summary_plain':   data.get('synthesis_plain', ''),
        'confidence':      conf,
        'cached_at':       data.get('cached_at', ''),
        'link':            f'/dss?ref={reference}',
    }]


def _extract_cards_backtranslation(reference: str, data: dict, min_confidence: float) -> list:
    ass = data.get('bibcrit_assessment', {})
    plain = ass.get('plain', '')
    conf  = ass.get('confidence', 0)
    if not plain or conf < min_confidence:
        return []
    return [{
        'reference':       reference,
        'tool':            'backtranslation',
        'card_type':       'vorlage_reconstruction',
        'divergence_type': 'vorlage_reconstruction',
        'mt_word':         '',
        'lxx_word':        '',
        'headline':        ass.get('title', 'Vorlage reconstruction'),
        'analysis_plain':  plain,
        'summary_plain':   data.get('summary_plain', ''),
        'confidence':      conf,
        'cached_at':       data.get('cached_at', ''),
        'link':            f'/backtranslation?ref={reference}',
    }]


def _extract_cards_numerical(reference: str, data: dict, min_confidence: float) -> list:
    ass = data.get('bibcrit_assessment', {})
    plain = ass.get('plain', '') or data.get('overall_plain', '')
    conf  = ass.get('confidence', 0) or 0
    if not plain or conf < min_confidence:
        return []
    return [{
        'reference':       reference,
        'tool':            'numerical',
        'card_type':       'numerical_discrepancy',
        'divergence_type': 'numerical_discrepancy',
        'mt_word':         '',
        'lxx_word':        '',
        'headline':        ass.get('title', 'Numerical discrepancy'),
        'analysis_plain':  plain,
        'summary_plain':   data.get('systematic_analysis', {}).get('pattern_plain', ''),
        'confidence':      conf,
        'cached_at':       data.get('cached_at', ''),
        'link':            f'/numerical?ref={reference}',
    }]


def _extract_cards_scribal(reference: str, data: dict, min_confidence: float) -> list:
    # reference is actually the book name for scribal
    summ = data.get('summary_plain', '') or data.get('summary', '')
    dims = data.get('dimensions', [])
    if not dims or not summ:
        return []
    top = max(dims, key=lambda d: abs(d.get('score', 0) - 0.5), default=None)
    if not top:
        return []
    conf = top.get('confidence', 0) if 'confidence' in top else 0.7
    if conf < min_confidence:
        return []
    plain = top.get('plain_summary', '') or top.get('analysis', '')
    if not plain:
        return []
    return [{
        'reference':       reference,
        'tool':            'scribal',
        'card_type':       'scribal_tendency',
        'divergence_type': 'scribal_tendency',
        'mt_word':         '',
        'lxx_word':        '',
        'headline':        top.get('name', 'Scribal tendency').replace('_', ' ').title(),
        'analysis_plain':  plain,
        'summary_plain':   summ,
        'confidence':      conf,
        'cached_at':       data.get('cached_at', ''),
        'link':            f'/scribal?book={reference}',
    }]


def _extract_cards_genealogy(reference: str, data: dict, min_confidence: float) -> list:
    ass = data.get('bibcrit_assessment', {})
    plain = ass.get('plain', '') or data.get('transmission_plain', '')
    conf  = ass.get('confidence', 0) or 0.75
    if not plain or conf < min_confidence:
        return []
    return [{
        'reference':       reference,
        'tool':            'genealogy',
        'card_type':       'transmission_genealogy',
        'divergence_type': 'transmission_genealogy',
        'mt_word':         '',
        'lxx_word':        '',
        'headline':        ass.get('title', 'Transmission genealogy'),
        'analysis_plain':  plain,
        'summary_plain':   data.get('transmission_plain', ''),
        'confidence':      conf,
        'cached_at':       data.get('cached_at', ''),
        'link':            f'/genealogy?book={reference}',
    }]


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from Claude response, handling markdown fences."""
    # 1. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # 2. Strip code fence
    m = re.search(r'```(?:json)?\s*(.*?)\s*```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 3. Walk brace depth to find the true outermost {...}
    # (rfind fails when strings contain '}' characters)
    extracted = _extract_outermost_object(raw)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
    return {
        'divergences': [],
        'summary_technical': '',
        'summary_plain': '',
        'parse_error': raw[:500],
        'parse_error_len': len(raw),
    }


def _extract_outermost_object(text: str) -> str | None:
    """Return the first complete {...} JSON object found in text."""
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None
