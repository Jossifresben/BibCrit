"""BibCrit — Biblical Textual Criticism Platform."""

import json
import logging
import os
import threading

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
                cap_usd=float(os.environ.get('BIBCRIT_API_CAP_USD', '5.0')),
            )
        except Exception:
            logger.exception('ClaudePipeline init failed — analysis unavailable until fixed')

        _initialized = True


@app.before_request
def ensure_initialized():
    _init()


if __name__ == '__main__':
    app.run(debug=True)
