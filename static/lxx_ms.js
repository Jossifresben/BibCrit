/* BibCrit — LXX Manuscript Witnesses */

(function () {
  'use strict';

  // OT + deuterocanon → chapter count. The analysis works from the critical
  // apparatus (training knowledge), so deuterocanonical books are included
  // even where the corpus has no Greek text to display.
  var _LXX_BOOKS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36, 'Deuteronomy': 34,
    'Joshua': 24, 'Judges': 21, 'Ruth': 4, '1 Samuel': 31, '2 Samuel': 24,
    '1 Kings': 22, '2 Kings': 25, '1 Chronicles': 29, '2 Chronicles': 36,
    'Ezra': 10, 'Nehemiah': 13, 'Esther': 10, 'Job': 42, 'Psalms': 151,
    'Proverbs': 31, 'Ecclesiastes': 12, 'Song of Songs': 8, 'Isaiah': 66,
    'Jeremiah': 52, 'Lamentations': 5, 'Ezekiel': 48, 'Daniel': 12,
    'Hosea': 14, 'Joel': 3, 'Amos': 9, 'Obadiah': 1, 'Jonah': 4, 'Micah': 7,
    'Nahum': 3, 'Habakkuk': 3, 'Zephaniah': 3, 'Haggai': 2, 'Zechariah': 14, 'Malachi': 4,
    // Deuterocanon (LXX-only)
    'Tobit': 14, 'Judith': 16, 'Wisdom': 19, 'Sirach': 51, 'Baruch': 5,
    '1 Maccabees': 16, '2 Maccabees': 15,
  };

  var selBook    = document.getElementById('sel-book');
  var selChapter = document.getElementById('sel-chapter');
  var selVerse   = document.getElementById('sel-verse');
  var refInput   = document.getElementById('ref-input');
  var btnAnalyze = document.getElementById('btn-analyze');
  var emptyState = document.getElementById('empty-state');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var results    = document.getElementById('lxx-ms-results');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  var _timer = null;
  var _currentRef = '';
  var _finalHandled = false;
  var _partialData = {};
  var _sectionReceived = false;

  if (selBook) {
    Object.keys(_LXX_BOOKS).forEach(function (b) {
      var opt = document.createElement('option');
      opt.value = b; opt.textContent = b;
      selBook.appendChild(opt);
    });
  }

  function _resetSelect(el, ph) {
    while (el.options.length > 1) el.remove(1);
    el.options[0].text = ph;
    el.disabled = true; el.value = '';
  }

  if (selBook) {
    selBook.addEventListener('change', function () {
      _resetSelect(selChapter, 'Ch…');
      _resetSelect(selVerse, 'Vs…');
      var n = _LXX_BOOKS[this.value] || 0;
      for (var i = 1; i <= n; i++) {
        var o = document.createElement('option');
        o.value = i; o.textContent = i; selChapter.appendChild(o);
      }
      if (n) selChapter.disabled = false;
    });
  }

  if (selChapter) {
    selChapter.addEventListener('change', function () {
      _resetSelect(selVerse, 'Vs…');
      for (var v = 1; v <= 50; v++) {
        var o = document.createElement('option');
        o.value = v; o.textContent = v; selVerse.appendChild(o);
      }
      selVerse.disabled = false;
    });
  }

  if (selVerse) {
    selVerse.addEventListener('change', function () {
      var b = selBook ? selBook.value : '';
      var c = selChapter ? selChapter.value : '';
      if (b && c && this.value) refInput.value = b + ' ' + c + ':' + this.value;
    });
  }

  document.querySelectorAll('.featured-ref').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.dataset.ref;
      if (ref) { refInput.value = ref; analyze(ref); }
    });
  });

  btnAnalyze.addEventListener('click', function () {
    var ref = (refInput ? refInput.value : '').trim();
    if (!ref) { showToast(window.t ? window.t('err_enter_passage', 'Please enter a passage') : 'Please enter a passage'); return; }
    analyze(ref);
  });

  if (refInput) refInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') btnAnalyze.click(); });

  function showToast(msg, dur) {
    if (!toast) return;
    toast.textContent = msg; toast.style.display = 'block';
    setTimeout(function () { toast.style.display = 'none'; }, dur || 3000);
  }

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function _reveal(el) { if (el && window.staggerReveal) staggerReveal(el, 0); }

  function _confBar(c) {
    if (typeof c !== 'number') return '';
    return '<div class="confidence-bar"><div class="confidence-fill" style="width:' +
      (c * 100).toFixed(0) + '%"></div></div>';
  }

  // Friendly model label + cached-date attribution (credibility pattern)
  function _friendlyModel(modelId) {
    if (!modelId) return 'Claude';
    var m = String(modelId).toLowerCase();
    if (m.indexOf('opus') !== -1)   return 'Claude Opus';
    if (m.indexOf('sonnet') !== -1) return 'Claude Sonnet';
    if (m.indexOf('haiku') !== -1)  return 'Claude Haiku';
    return 'Claude';
  }
  function _formatCached(isoStr) {
    if (!isoStr) return '';
    try {
      return new Date(isoStr).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (_) { return ''; }
  }

  // ── Section renderers ─────────────────────────────────────────────────────

  function _renderCorpus(data) {
    var el  = document.getElementById('lxx-text-body');
    var sec = document.getElementById('lxx-text-display');
    if (el && data && data.lxx_text) {
      el.textContent = data.lxx_text;
      if (sec) { sec.style.display = ''; _reveal(sec); }
    }
  }

  function _renderSummary(data) {
    var text = typeof data === 'string' ? data : (data && data.passage_summary) || '';
    var el  = document.getElementById('lxx-summary-body');
    var sec = document.getElementById('lxx-summary-section');
    if (el) el.textContent = text;
    if (sec && text) { sec.style.display = ''; _reveal(sec); }
  }

  function _renderWitnesses(data) {
    var arr = Array.isArray(data) ? data : [];
    if (!arr.length) return;
    var html = arr.map(function (w) {
      var extant = w.extant !== false;
      var tag = extant
        ? '<span class="ms-support support-sides-with-critical">extant</span>'
        : '<span class="ms-support support-split">not extant — lacuna</span>';
      return '<div class="ms-family-row">' +
        '<div class="ms-family-header">' +
          '<span class="ms-family-name">' + esc(w.siglum || '') + '</span>' + tag +
        '</div>' +
        '<p class="ms-family-note">' + esc(w.character || '') + '</p>' +
        _confBar(w.confidence) +
      '</div>';
    }).join('');
    var el  = document.getElementById('lxx-witnesses-body');
    var sec = document.getElementById('lxx-witnesses-section');
    if (el) el.innerHTML = html;
    if (sec) { sec.style.display = ''; _reveal(sec); }
  }

  function _renderDivergences(data) {
    var arr = Array.isArray(data) ? data : [];
    var el  = document.getElementById('lxx-divergences-body');
    var sec = document.getElementById('lxx-divergences-section');
    if (!arr.length) {
      if (el) el.innerHTML = '<p class="vc-note">The witnesses substantially agree at this passage — no significant divergences reported.</p>';
      if (sec) { sec.style.display = ''; _reveal(sec); }
      return;
    }
    var html = arr.map(function (d, i) {
      var readings = Array.isArray(d.readings) ? d.readings : [];
      var rHtml = readings.map(function (r) {
        return '<div class="dp-row">' +
          '<strong>' + esc(r.witnesses || '') + ':</strong> ' +
          '<span style="font-family:var(--serif,serif);font-weight:600;">' + esc(r.lexeme || '') + '</span>' +
          (r.gloss ? ' — <em>' + esc(r.gloss) + '</em>' : '') +
          (r.description ? '<div class="vc-note">' + esc(r.description) + '</div>' : '') +
        '</div>';
      }).join('');
      return '<div class="variant-card">' +
        '<div class="vc-type">' + esc(d.locus || ('Divergence ' + (i + 1))) + '</div>' +
        rHtml +
        (d.significance ? '<p class="vc-note"><strong>Significance:</strong> ' + esc(d.significance) + '</p>' : '') +
        _confBar(d.confidence) +
      '</div>';
    }).join('');
    if (el) el.innerHTML = html;
    if (sec) { sec.style.display = ''; _reveal(sec); }
  }

  function _renderAssessment(data) {
    var a = data || {};
    var html = '';
    if (a.synthesis) html += '<p class="bc-plain">' + esc(a.synthesis) + '</p>';
    if (a.verify_against) {
      var va = Array.isArray(a.verify_against) ? a.verify_against.join('; ') : a.verify_against;
      html += '<p><strong>Verify against:</strong> ' + esc(va) + '</p>';
    }
    html += _confBar(a.overall_confidence);
    // Credibility: model + cached-date attribution
    var attr = 'Performed by ' + esc(_friendlyModel(_partialData.model_version));
    var when = _formatCached(_partialData.cached_at);
    if (when) attr += ' · ' + esc(when);
    html += '<p class="analysis-model-attr">' + attr + '</p>';
    var el  = document.getElementById('lxx-assessment-body');
    var sec = document.getElementById('lxx-assessment-section');
    if (el) el.innerHTML = html;
    if (sec) { sec.style.display = ''; _reveal(sec); }
  }

  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived = true;
    if (emptyState) emptyState.style.display = 'none';

    if (key === '_corpus')        return _renderCorpus(data);
    if (key === 'passage_summary') return _renderSummary(data);
    if (key === 'witnesses')       return _renderWitnesses(data);
    if (key === 'divergences')     return _renderDivergences(data);
    if (key === 'assessment')      return _renderAssessment(data);
  }

  function renderResult(data) {
    if (_timer) { clearInterval(_timer); _timer = null; }
    if (loadTimer) loadTimer.textContent = '';
    if (loadState) loadState.style.display = 'none';
    _partialData = Object.assign({}, _partialData, data || {});

    if (heading) {
      heading.innerHTML = '<span class="ph-ref">' + esc(data.reference || _currentRef) + '</span>';
      heading.style.display = '';
    }
    if (data.lxx_text) _renderCorpus({ lxx_text: data.lxx_text });
    if (data.passage_summary) _renderSummary(data.passage_summary);
    if (data.witnesses) _renderWitnesses(data.witnesses);
    if (data.divergences !== undefined) _renderDivergences(data.divergences);
    if (data.assessment) _renderAssessment(data.assessment);

    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';
    _wireExport(data);
  }

  function _wireExport(data) {
    var btnSbl    = document.getElementById('btn-sbl');
    var btnBibtex = document.getElementById('btn-bibtex');
    var btnShare  = document.getElementById('btn-share');

    if (btnSbl) {
      btnSbl.onclick = function () {
        fetch('/api/export/sbl?tool=lxx_ms_variants&ref=' + encodeURIComponent(_currentRef))
          .then(function (r) { return r.json(); })
          .then(function (d) {
            var text = (d.footnotes || [d.footnote]).join('\n\n');
            navigator.clipboard.writeText(text).catch(function () {});
            showToast(window.t ? window.t('toast_sbl_copied_short', 'SBL footnote copied!') : 'SBL footnote copied!');
          }).catch(function () {});
      };
    }
    if (btnBibtex) {
      btnBibtex.onclick = function () {
        fetch('/api/export/bibtex?tool=lxx_ms_variants&ref=' + encodeURIComponent(_currentRef))
          .then(function (r) { return r.json(); })
          .then(function (d) {
            navigator.clipboard.writeText(d.bibtex || '').catch(function () {});
            showToast(window.t ? window.t('toast_bibtex_copied_short', 'BibTeX copied!') : 'BibTeX copied!');
          }).catch(function () {});
      };
    }
    if (btnShare) {
      btnShare.onclick = function () {
        var url = window.location.origin + '/lxx-witnesses?ref=' + encodeURIComponent(_currentRef);
        navigator.clipboard.writeText(url);
        showToast(window.t ? window.t('toast_link_copied', 'Link copied!') : 'Link copied!');
      };
    }
  }

  function _hideSpinner() {
    if (_timer) { clearInterval(_timer); _timer = null; }
    if (loadTimer) loadTimer.textContent = '';
    if (loadState) { loadState.classList.remove('is-compact'); loadState.style.display = 'none'; }
  }

  function analyze(ref) {
    if (!ref) return;
    if (window.BibCrit_requireVerse && window.BibCrit_requireVerse(ref)) return;
    _currentRef = ref;
    _finalHandled = false;
    _partialData = {};
    _sectionReceived = false;

    if (emptyState) emptyState.style.display = 'none';

    if (_timer) clearInterval(_timer);
    if (loadState) { loadState.classList.add('is-compact'); loadState.style.display = 'block'; }
    if (loadStep) loadStep.textContent = window.t ? window.t('step_generating', 'Analyzing — this may take 60–90 seconds…') : 'Analyzing — this may take 60–90 seconds…';
    if (loadTimer) {
      var s = 0; loadTimer.textContent = '';
      _timer = setInterval(function () { loadTimer.textContent = (++s) + 's'; }, 1000);
    }

    if (heading) { heading.innerHTML = '<span class="ph-ref">' + esc(ref) + '</span>'; heading.style.display = ''; }
    if (results) results.style.display = 'block';

    ['lxx-text-display', 'lxx-summary-section', 'lxx-witnesses-section',
     'lxx-divergences-section', 'lxx-assessment-section', 'export-row'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });

    var lang = new URLSearchParams(window.location.search).get('lang') || 'en';
    var url  = '/api/lxx-ms/stream?ref=' + encodeURIComponent(ref) + '&lang=' + lang;
    var es   = new EventSource(url);

    es.onmessage = function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          if (loadStep) loadStep.textContent = msg.msg;
        } else if (msg.type === 'section') {
          _renderSection(msg.key, msg.data);
        } else if (msg.type === 'done') {
          _finalHandled = true;
          es.close();
          _hideSpinner();
          renderResult(msg.data);
        } else if (msg.type === 'error') {
          _finalHandled = true;
          es.close(); _hideSpinner(); showToast(msg.msg || 'Error', 5000);
        }
      } catch (_) {}
    };

    es.onerror = function () {
      if (_finalHandled) return;
      es.close(); _hideSpinner();
      showToast(window.t ? window.t('err_connection', 'Connection error') : 'Connection error', 5000);
    };
  }

  window.lxxMs = { analyze: analyze };
}());
