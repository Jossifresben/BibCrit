"""Research blueprint — concordance, hapax, collocations."""

import os
import re
import markdown as _md

from flask import Blueprint, jsonify, render_template, request
import state

research_bp = Blueprint('research', __name__)

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def _parse_paper():
    """Parse paper.md and paper.bib, return dict ready for template."""
    paper_path = os.path.join(_BASE_DIR, 'paper.md')
    bib_path   = os.path.join(_BASE_DIR, 'paper.bib')

    with open(paper_path, encoding='utf-8') as f:
        raw = f.read()

    # Strip YAML frontmatter
    body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', raw, flags=re.DOTALL)

    # Extract frontmatter fields
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', raw, flags=re.DOTALL)
    frontmatter = fm_match.group(1) if fm_match else ''
    title   = re.search(r"^title:\s*['\"]?(.*?)['\"]?\s*$", frontmatter, re.M)
    date    = re.search(r'^date:\s*(.+)$', frontmatter, re.M)
    # Only parse names/orcids under the `authors:` block (stop at `affiliations:`)
    authors_block = re.search(r'^authors:\s*\n(.*?)(?=^\w)', frontmatter, re.DOTALL | re.M)
    ab = authors_block.group(1) if authors_block else ''
    authors = re.findall(r'^\s*-?\s*name:\s*(.+)$', ab, re.M)
    orcids  = re.findall(r'^\s*orcid:\s*(.+)$', ab, re.M)

    # Build cite key → short label mapping for inline superscripts
    cite_keys = re.findall(r'@(\w+)', body)
    unique_keys = list(dict.fromkeys(cite_keys))  # preserve order
    key_num = {k: i+1 for i, k in enumerate(unique_keys)}

    # Replace [@key1; @key2] or [@key] with superscript footnote numbers
    def _replace_cite(m):
        keys = re.findall(r'@(\w+)', m.group(0))
        nums = ', '.join(str(key_num[k]) for k in keys if k in key_num)
        return f'<sup class="paper-cite">[{nums}]</sup>'
    body = re.sub(r'\[@[^\]]+\]', _replace_cite, body)

    # Remove the bare "# References" section — we render from bib
    body = re.sub(r'\n# References\s*$', '', body, flags=re.DOTALL)

    # Convert markdown to HTML
    html = _md.markdown(body, extensions=['tables', 'fenced_code', 'nl2br'])

    # Parse bib file into list of formatted reference strings
    refs = _parse_bib(bib_path, unique_keys, key_num)

    return {
        'title':   title.group(1) if title else 'BibCrit',
        'authors': list(zip(authors, orcids + ['']*len(authors))),
        'date':    date.group(1) if date else '2026',
        'html':    html,
        'refs':    refs,
    }


def _parse_bib(bib_path, ordered_keys, key_num):
    """Return list of (num, formatted_html) tuples in citation order."""
    with open(bib_path, encoding='utf-8') as f:
        raw = f.read()

    entries = {}
    for entry in re.finditer(r'@\w+\{(\w+),(.*?)\n\}', raw, re.DOTALL):
        key   = entry.group(1)
        block = entry.group(2)
        def _field(name):
            m = re.search(rf'{name}\s*=\s*\{{(.+?)\}}', block, re.DOTALL)
            v = m.group(1).strip().replace('\n', ' ') if m else ''
            return v.strip('{}')  # remove BibTeX double-brace wrappers
        entries[key] = {
            'author':  _field('author'),
            'title':   _field('title'),
            'year':    _field('year'),
            'journal': _field('journal'),
            'publisher': _field('publisher'),
            'edition': _field('edition'),
            'url':     _field('url'),
            'doi':     _field('doi'),
            'note':    _field('note'),
            'howpublished': _field('howpublished').replace(r'\url{', '').rstrip('}'),
        }

    result = []
    for k in ordered_keys:
        if k not in entries:
            continue
        e   = entries[k]
        num = key_num[k]
        url = e['doi'] and f'https://doi.org/{e["doi"]}' or e['url'] or e['howpublished'] or ''
        url = re.sub(r'\\url\{([^}]+)\}', r'\1', url)
        parts = []
        if e['author']:  parts.append(e['author'])
        if e['title']:
            t = f'<em>{e["title"]}</em>' if not e['journal'] else f'"{e["title"]}"'
            parts.append(t)
        if e['journal']: parts.append(e['journal'])
        if e['edition']: parts.append(e['edition'] + ' ed.')
        if e['publisher']: parts.append(e['publisher'])
        if e['year']:    parts.append(e['year'])
        ref_text = '. '.join(parts)
        if url:
            ref_text += f'. <a href="{url}" target="_blank" rel="noopener">{url}</a>'
        result.append((num, ref_text))

    return result


@research_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'app': 'bibcrit'})


@research_bp.route('/guide')
def guide():
    lang = request.args.get('lang', 'en')
    template = 'guide_es.html' if lang == 'es' else 'guide.html'
    return render_template(template, lang=lang, t=state.t)


@research_bp.route('/paper')
def paper():
    lang = request.args.get('lang', 'en')
    data = _parse_paper()
    return render_template('paper.html', lang=lang, t=state.t, **data)
