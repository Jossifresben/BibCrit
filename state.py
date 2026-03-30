"""Shared application state — populated by app._init() before first request.

Blueprints import this module and access corpus/pipeline directly.
No circular imports: state.py imports nothing from blueprints or app.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from biblical_core.corpus import BiblicalCorpus
    from biblical_core.claude_pipeline import ClaudePipeline

corpus: 'BiblicalCorpus | None' = None
pipeline: 'ClaudePipeline | None' = None
i18n: dict = {}


class TranslationProxy:
    """Callable proxy: t('key', lang) or t.key — falls back to English."""

    def __call__(self, key: str, lang: str = 'en') -> str:
        return (
            i18n.get(lang, {}).get(key)
            or i18n.get('en', {}).get(key)
            or key
        )

    def __getattr__(self, key: str) -> str:
        return self(key)


t = TranslationProxy()
