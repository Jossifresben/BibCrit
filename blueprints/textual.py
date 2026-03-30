"""Textual Analysis blueprint — MT/LXX tools, back-translation, DSS bridge."""

from flask import Blueprint, render_template, request
import state

textual_bp = Blueprint('textual', __name__)


@textual_bp.route('/')
def index():
    lang = request.args.get('lang', 'en')
    return render_template('index.html', lang=lang, t=state.t)
