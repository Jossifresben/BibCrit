"""BibCrit — Biblical Textual Criticism Platform."""

import json
import logging
import os
import threading

# Load .env for local development (silently ignored if file absent or dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)
except ImportError:
    pass

from flask import Flask

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')

_initialized = False
_init_lock = threading.Lock()


def create_app() -> Flask:
    app = Flask(__name__)

    from blueprints.textual import textual_bp
    from blueprints.critical import critical_bp
    from blueprints.research import research_bp
    from blueprints.discovery import discovery_bp

    app.register_blueprint(textual_bp)
    app.register_blueprint(critical_bp)
    app.register_blueprint(research_bp)
    app.register_blueprint(discovery_bp)

    return app


app = create_app()


def _init() -> None:
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return

        import state

        # Load i18n
        i18n_path = os.path.join(DATA_DIR, 'i18n.json')
        if os.path.exists(i18n_path):
            with open(i18n_path, 'r', encoding='utf-8') as f:
                state.i18n = json.load(f)

        # Load corpus (graceful if not yet built)
        try:
            from biblical_core.corpus import BiblicalCorpus
            state.corpus = BiblicalCorpus()
            state.corpus.set_data_dir(DATA_DIR)
            state.corpus.load_all()
        except Exception:
            logger.exception('BiblicalCorpus init failed — corpus unavailable until fixed')

        # Load Claude pipeline (graceful if no API key)
        try:
            from biblical_core.claude_pipeline import ClaudePipeline
            state.pipeline = ClaudePipeline(
                data_dir=DATA_DIR,
                api_key=os.environ.get('ANTHROPIC_API_KEY', ''),
                cap_usd=float(os.environ.get('BIBCRIT_API_CAP_USD', '10.0')),
                supabase_url=os.environ.get('SUPABASE_URL', ''),
                supabase_key=os.environ.get('SUPABASE_KEY', ''),
            )
        except Exception:
            logger.exception('ClaudePipeline init failed — analysis unavailable until fixed')

        _initialized = True


@app.before_request
def ensure_initialized():
    _init()


# ── SEO / Discovery files ──────────────────────────────────────────────────

@app.route('/robots.txt')
def robots_txt():
    from flask import Response
    content = """User-agent: *
Allow: /
Disallow: /api/

User-agent: GPTBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://bibcrit.app/sitemap.xml
"""
    return Response(content, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap_xml():
    from flask import Response
    pages = [
        ('/', '1.0', 'weekly'),
        ('/divergence', '0.9', 'weekly'),
        ('/backtranslation', '0.9', 'weekly'),
        ('/dss', '0.9', 'weekly'),
        ('/scribal', '0.9', 'weekly'),
        ('/numerical', '0.9', 'weekly'),
        ('/theological', '0.9', 'weekly'),
        ('/patristic', '0.9', 'weekly'),
        ('/genealogy', '0.9', 'weekly'),
        ('/discovery', '0.8', 'monthly'),
        ('/guide', '0.7', 'monthly'),
    ]
    urls = ''
    for path, priority, freq in pages:
        urls += f"""  <url>
    <loc>https://bibcrit.app{path}</loc>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
    <xhtml:link rel="alternate" hreflang="en" href="https://bibcrit.app{path}"/>
    <xhtml:link rel="alternate" hreflang="es" href="https://bibcrit.app{path}?lang=es"/>
  </url>\n"""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
{urls}</urlset>"""
    return Response(xml, mimetype='application/xml')


@app.route('/llms.txt')
def llms_txt():
    from flask import Response
    content = """# BibCrit

> AI-powered toolkit for biblical textual criticism. Eight specialized scholarly tools for analyzing divergences between the Masoretic Text (MT) and the Septuagint (LXX), profiling scribal tendencies, comparing Dead Sea Scrolls witnesses, reconstructing Hebrew Vorlagen, tracing patristic citations, modeling numerical discrepancies, detecting theological revisions, and visualizing manuscript genealogies.

BibCrit streams AI analysis (powered by Anthropic Claude) directly in the browser. Frequently analyzed passages are cached and load instantly. All tools are free and openly accessible.

## Tools

- MT/LXX Divergence Analyzer: https://bibcrit.app/divergence
- Back-Translation Workbench: https://bibcrit.app/backtranslation
- DSS Bridge Tool: https://bibcrit.app/dss
- Scribal Tendency Profiler: https://bibcrit.app/scribal
- Numerical Discrepancy Modeler: https://bibcrit.app/numerical
- Theological Revision Detector: https://bibcrit.app/theological
- Patristic Citation Tracker: https://bibcrit.app/patristic
- Manuscript Genealogy: https://bibcrit.app/genealogy

## Languages

Available in English and Spanish. Append `?lang=es` to any URL for the Spanish interface.

## Open Data API

Full REST API for programmatic access to all analysis results.
- API endpoint: https://bibcrit.app/api/discovery
- Documentation: https://github.com/Jossifresben/BibCrit/blob/main/docs/api-reference.md

## Source & License

- GitHub: https://github.com/Jossifresben/BibCrit
- License: Apache 2.0

## Citation

Fresco Benaim, J. (2026). BibCrit: AI-assisted biblical textual criticism. https://bibcrit.app ORCID:0009-0000-2026-0836
"""
    return Response(content, mimetype='text/plain')



@app.context_processor
def inject_globals():
    """Inject _t() translation helper, current lang, and JS i18n dict into every template."""
    from flask import request
    import state
    lang = request.args.get('lang', 'en')

    def _t(key: str) -> str:
        return state.t(key, lang)

    i18n_lang = state.i18n.get(lang, state.i18n.get('en', {})) if state.i18n else {}
    return dict(_t=_t, lang=lang, i18n_lang=i18n_lang)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, port=port)
