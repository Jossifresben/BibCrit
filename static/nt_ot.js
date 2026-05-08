/**
 * nt_ot.js — BibCrit NT Use of OT Analyzer
 *
 * Responsibilities:
 *   - Corpus browser: cascading book/chapter/verse selects (GNT tradition)
 *   - Fetch and render allusion analysis from /api/nt-ot/stream
 *   - Render allusion cards with MT/LXX columns, alignment badges, and confidence
 *   - Scholar/Student mode toggle (technical vs. plain-language display)
 *   - BibCrit hypothesis card at the end of results
 */

(function () {
  'use strict';

  // ── State ─────────────────────────────────────────────────────────────────
  var currentData  = null;
  var currentRef   = '';
  var _finalHandled   = false;
  var _partialData    = {};
  var _sectionReceived = false;
  var _timer          = null;

  // ── Skeleton helpers ──────────────────────────────────────────────────────
  function _skelRows(n, widths) {
    var html = '', pcts = widths || [100, 88, 72, 58, 45];
    for (var i = 0; i < n; i++)
      html += '<div class="dss-skel-row" style="height:12px;width:' + (pcts[i] || 55) + '%"></div>';
    return html;
  }
  function _hideCompactSpinner() {
    if (loadingState) { loadingState.classList.remove('is-compact'); loadingState.style.display = 'none'; }
    clearInterval(_timer);
  }
  function _skelCard() {
    return '<div class="dss-ms-card" style="max-width:900px;margin:0 auto 1rem;opacity:0.6">' +
      '<div style="padding:1rem 1.25rem">' +
      '<div class="dss-skel-row" style="height:16px;width:40%"></div>' +
      '<div style="margin-top:0.75rem">' + _skelRows(3, [95, 80, 65]) + '</div>' +
      '</div></div>';
  }
  function _renderSkeleton() {
    var ra = document.getElementById('results-area');
    if (!ra) return;
    ra.style.display = '';
    ra.innerHTML =
      '<div style="padding:1rem">' +
      _skelCard() + _skelCard() + _skelCard() +
      '<div style="margin-top:1rem">' + _skelRows(3, [100, 85, 70]) + '</div>' +
      '</div>';
  }

  // ── Language ──────────────────────────────────────────────────────────────
  var LANG = window.BIBCRIT_LANG || document.documentElement.lang || 'en';

  // ── Alignment config ──────────────────────────────────────────────────────
  var ALIGNMENT = {
    'lxx':           { cls: 'align-lxx',      label: 'LXX',          color: '#3a6bc4' },
    'mt':            { cls: 'align-mt',       label: 'MT',           color: '#28a745' },
    'independent':   { cls: 'align-indep',    label: 'Independent',  color: '#6c757d' },
    'conflation':    { cls: 'align-conflat',  label: 'Conflation',   color: '#e67e22' },
    'lxx_recension': { cls: 'align-lxx-rec',  label: 'LXX Recension', color: '#7b2d8b' },
  };

  // ── DOM refs ──────────────────────────────────────────────────────────────
  var selBook        = document.getElementById('sel-book');
  var selChapter     = document.getElementById('sel-chapter');
  var selVerse       = document.getElementById('sel-verse');
  var refInput       = document.getElementById('ref-input');
  var btnAnalyze     = document.getElementById('btn-analyze');
  var emptyState     = document.getElementById('empty-state');
  var loadingState   = document.getElementById('loading-state');
  var resultsArea    = document.getElementById('results-area');
  var passageHeading = document.getElementById('passage-heading');
  var corpusPanel    = document.getElementById('nt-ot-corpus-panel');

  if (!selBook || !btnAnalyze) return;  // guard: only run on nt-ot page

  // ── Init ──────────────────────────────────────────────────────────────────
  fetchBooks();

  document.querySelectorAll('.featured-ref').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      refInput.value = el.dataset.ref;
      analyze(el.dataset.ref);
    });
  });

  btnAnalyze.addEventListener('click', function () { analyze(refInput.value.trim()); });
  refInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') analyze(refInput.value.trim());
  });

  var _randomPassages = [
    'Matthew 1:23', 'Hebrews 1:6', 'Romans 15:12', 'Acts 15:17',
    'John 12:15', 'Matthew 2:15', '1 Peter 2:9', 'Hebrews 2:7',
  ];

  var btnRandom = document.getElementById('btn-random');
  if (btnRandom) {
    btnRandom.addEventListener('click', function () {
      var ref = _randomPassages[Math.floor(Math.random() * _randomPassages.length)];
      refInput.value = ref;
      analyze(ref);
    });
  }

  // ── Corpus browser ────────────────────────────────────────────────────────
  function fetchBooks() {
    fetch('/api/books?tradition=GNT')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.books || []).forEach(function (b) {
          var o = document.createElement('option');
          o.value = o.textContent = b;
          selBook.appendChild(o);
        });
      });
  }

  selBook.addEventListener('change', function () {
    selChapter.innerHTML = '<option value="">Ch\u2026</option>';
    selVerse.innerHTML   = '<option value="">Vs\u2026</option>';
    selChapter.disabled  = true;
    selVerse.disabled    = true;
    if (!selBook.value) return;
    fetch('/api/chapters?book=' + encodeURIComponent(selBook.value) + '&tradition=GNT')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.chapters || []).forEach(function (c) {
          var o = document.createElement('option');
          o.value = o.textContent = c;
          selChapter.appendChild(o);
        });
        selChapter.disabled = false;
      });
  });

  selChapter.addEventListener('change', function () {
    selVerse.innerHTML = '<option value="">Vs\u2026</option>';
    selVerse.disabled  = true;
    if (!selChapter.value) return;
    fetch('/api/verses?book=' + encodeURIComponent(selBook.value) +
          '&chapter=' + selChapter.value + '&tradition=GNT')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.verses || []).forEach(function (v) {
          var o = document.createElement('option');
          o.value = o.textContent = v;
          selVerse.appendChild(o);
        });
        selVerse.disabled = false;
      });
  });

  selVerse.addEventListener('change', function () {
    if (!selVerse.value) return;
    var ref = selBook.value + ' ' + selChapter.value + ':' + selVerse.value;
    refInput.value = ref;
    analyze(ref);
  });

  // ── OT book guard ─────────────────────────────────────────────────────────
  var OT_BOOKS = [
    'genesis','exodus','leviticus','numbers','deuteronomy','joshua','judges','ruth',
    '1 samuel','2 samuel','1 kings','2 kings','1 chronicles','2 chronicles',
    'ezra','nehemiah','esther','job','psalm','psalms','proverbs','ecclesiastes',
    'song of solomon','song of songs','isaiah','jeremiah','lamentations','ezekiel',
    'daniel','hosea','joel','amos','obadiah','jonah','micah','nahum','habakkuk',
    'zephaniah','haggai','zechariah','malachi',
    'gen','exo','exod','lev','num','deut','josh','judg','isa','jer','ezek','dan',
    'hos','amos','mic','zech','mal','psa','prov','ecc','neh','est',
    '1sam','2sam','1kgs','2kgs','1ki','2ki','1king','2king','1kings','2kings',
    '1chr','2chr','1chron','2chron','1chronicles','2chronicles',
  ];

  function _isOtRef(ref) {
    var first = ref.trim().toLowerCase().replace(/\s+\d.*$/, '').trim();
    return OT_BOOKS.indexOf(first) !== -1;
  }

  // ── Analysis (SSE) ────────────────────────────────────────────────────────
  function analyze(ref) {
    if (!ref) return;
    if (window.BibCrit_checkPassageLength && window.BibCrit_checkPassageLength(ref)) return;
    if (window.BibCrit_requireVerse && window.BibCrit_requireVerse(ref)) return;

    if (_isOtRef(ref)) {
      emptyState.style.display = 'block';
      var p = emptyState.querySelector('p');
      if (p) p.textContent = '\u26a0 "' + ref + '" is an Old Testament reference. This tool analyzes NT passages — try Matthew 1:23, Hebrews 1:6, or Romans 15:12.';
      return;
    }

    currentRef = ref;
    _finalHandled    = false;
    _partialData     = {};
    _sectionReceived = false;
    clearInterval(_timer);

    // Show compact spinner + skeleton immediately
    emptyState.style.display   = 'none';
    if (corpusPanel) { corpusPanel.innerHTML = ''; corpusPanel.style.display = 'none'; }
    if (resultsArea) resultsArea.style.display = '';
    if (passageHeading) {
      passageHeading.innerHTML =
        '<span class="ph-ref">' + _esc(ref) + '</span>' +
        '<span class="ph-tool">NT Use of OT</span>';
      passageHeading.style.display = 'flex';
    }
    if (loadingState) {
      loadingState.classList.add('is-compact');
      loadingState.style.display = 'block';
    }

    var stepEl  = document.getElementById('loading-step');
    var timerEl = document.getElementById('loading-timer');
    if (stepEl)  stepEl.textContent  = 'Preparing\u2026';
    if (timerEl) timerEl.textContent = '';

    var startTime = Date.now();
    var timerInterval = setInterval(function () {
      if (timerEl) {
        var s = Math.floor((Date.now() - startTime) / 1000);
        timerEl.textContent = s + 's';
      }
    }, 1000);
    _timer = timerInterval;
    _renderSkeleton();

    var es = new EventSource(
      '/api/nt-ot/stream?ref=' + encodeURIComponent(ref) + '&lang=' + encodeURIComponent(LANG)
    );

    es.onmessage = function (e) {
      var msg = JSON.parse(e.data);

      if (msg.type === 'step') {
        if (stepEl) stepEl.textContent = msg.msg;
      } else if (msg.type === 'section') {
        _renderSection(msg.key, msg.data);
      } else if (msg.type === 'error') {
        _finalHandled = true;
        _hideCompactSpinner();
        es.close();
        emptyState.style.display   = 'block';
        var h2 = emptyState.querySelector('h2');
        if (h2) h2.textContent = '\u26a0 ' + msg.msg;

      } else if (msg.type === 'done') {
        _finalHandled = true;
        _hideCompactSpinner();
        es.close();
        if (_sectionReceived) {
          _finalize(msg.data);
        } else {
          currentData = msg.data;
          history.replaceState(null, '', '/nt-ot?ref=' + encodeURIComponent(ref));
          if (typeof updateBudgetBar === 'function') updateBudgetBar();
          renderResults(msg.data);
        }
      }
    };

    es.onerror = function () {
      if (_finalHandled) return;
      _hideCompactSpinner();
      es.close();
      emptyState.style.display   = 'block';
    };
  }

  // ── Progressive section rendering ─────────────────────────────────────────
  function _renderCorpusPanel(gntText, enText) {
    if (!corpusPanel) return;
    var html = '<div class="bt-group-card" style="max-width:900px;margin:0 auto 1rem;padding:1rem 1.25rem;">';
    if (gntText) {
      html += '<div style="font-size:0.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
            + 'color:var(--muted);margin-bottom:0.4rem">Greek (GNT)</div>'
            + '<div class="greek-text verse-text" style="margin-bottom:' + (enText ? '0.9rem' : '0') + '">'
            + _esc(gntText) + '</div>';
    }
    if (enText) {
      html += '<div style="font-size:0.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
            + 'color:var(--muted);margin-bottom:0.4rem">English (WEB)</div>'
            + '<div style="font-size:1rem;line-height:1.7;color:var(--fg);font-style:italic">'
            + _esc(enText) + '</div>';
    }
    html += '</div>';
    corpusPanel.innerHTML = html;
    corpusPanel.style.display = '';
  }

  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived  = true;

    if (key === '_corpus') {
      _renderCorpusPanel(data.gnt_text || '', data.en_text || '');
      return;
    }

    if (key === 'citations') {
      // Hide loading and reveal results only when content is ready to show
      if (emptyState)   emptyState.style.display   = 'none';
      if (resultsArea)  resultsArea.style.display  = '';
      if (passageHeading) passageHeading.style.display = 'flex';
      // citations = array of allusion objects
      if (passageHeading) {
        passageHeading.innerHTML =
          '<span class="ph-ref">'  + _esc(currentRef) + '</span>' +
          '<span class="ph-tool">NT Use of OT</span>';
      }
      if (resultsArea) {
        resultsArea.innerHTML = '';
        var allusions = Array.isArray(data) ? data : (data || []);
        allusions.forEach(function (allusion) {
          resultsArea.appendChild(buildAllusionCard(allusion));
        });
      }
      staggerReveal(resultsArea, 30);
    }

    if (key === 'intertextual_analysis') {
      // summary-like text block
      if (resultsArea && data) {
        var summCard = buildSummaryCard({
          summary_technical: (data && data.summary_technical) || '',
          summary_plain:     (data && data.summary_plain)     || (typeof data === 'string' ? data : ''),
        });
        if (resultsArea.firstChild) {
          resultsArea.insertBefore(summCard, resultsArea.firstChild);
        } else {
          resultsArea.appendChild(summCard);
        }
        staggerReveal(summCard, 0);
      }
    }

    if (key === 'synthesis') {
      if (resultsArea && data) {
        var synCard = buildSummaryCard({
          summary_plain: typeof data === 'string' ? data : (data && (data.synthesis_plain || data.synthesis || '')),
        });
        resultsArea.appendChild(synCard);
        staggerReveal(synCard, 0);
      }
    }

    if (key === 'assessment') {
      if (resultsArea) {
        resultsArea.appendChild(buildHypothesisCard({ bibcrit_hypothesis: data, model_version: _partialData.model_version }));
        staggerReveal(resultsArea, 0);
      }
    }
  }

  function _finalize(data) {
    var merged = Object.assign({}, _partialData, data || {});
    currentData = merged;
    _hideCompactSpinner();
    history.replaceState(null, '', '/nt-ot?ref=' + encodeURIComponent(currentRef));
    if (typeof updateBudgetBar === 'function') updateBudgetBar();
    renderResults(merged);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  function renderResults(data) {
    if (!resultsArea) return;

    // Clear previous results
    resultsArea.innerHTML = '';

    // Passage heading + GNT verse text
    if (passageHeading) {
      passageHeading.innerHTML =
        '<span class="ph-ref">'  + _esc(data.reference || currentRef) + '</span>' +
        '<span class="ph-tool">NT Use of OT</span>';
      passageHeading.style.display = 'flex';
    }

    // Corpus panel (GNT + English) — use the persistent panel above resultsArea
    var _corpus = _partialData['_corpus'] || {};
    _renderCorpusPanel(
      _corpus.gnt_text || data.nt_text || '',
      _corpus.en_text  || ''
    );

    // Summary card
    if (data.summary_technical || data.summary_plain) {
      resultsArea.appendChild(buildSummaryCard(data));
    }

    // Allusion cards
    var allusions = data.allusions || [];
    allusions.forEach(function (allusion) {
      resultsArea.appendChild(buildAllusionCard(allusion));
    });

    // BibCrit hypothesis card
    if (data.bibcrit_hypothesis) {
      resultsArea.appendChild(buildHypothesisCard(data));
    }

    // Model attribution
    var modelAttr = document.getElementById('nt-ot-model-attr');
    if (modelAttr && data.model_version) {
      var _cachedDate = _formatCached(data.cached_at);
      modelAttr.textContent = 'Analysis by ' + _friendlyModel(data.model_version) + (_cachedDate ? ' · ' + _cachedDate : '');
      modelAttr.style.display = 'inline';
    }

    // Result actions (Scholar Rating, Copy, Download)
    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'nt_ot',
        getReference: function () { return currentRef; },
        getResultData: function () { return currentData || {}; },
      });
    }

    resultsArea.style.display = 'block';
    staggerReveal(resultsArea, 90);
  }

  // ── Card builders ─────────────────────────────────────────────────────────
  function buildSummaryCard(data) {
    var card = document.createElement('div');
    card.className = 'nt-ot-summary-card result-card';
    card.innerHTML =
      '<div class="summary-card-header">' +
        '<span class="summary-card-title">Summary</span>' +
      '</div>' +
      (data.summary_technical
        ? '<p class="technical-only">'  + _esc(data.summary_technical) + '</p>'
        : '') +
      (data.summary_plain
        ? '<p class="plain-highlight">' + _esc(data.summary_plain)     + '</p>'
        : '');
    return card;
  }

  function buildAllusionCard(a) {
    var alignment = a.nt_alignment || 'independent';
    var alignInfo = ALIGNMENT[alignment] || ALIGNMENT['independent'];
    var conf      = a.alignment_confidence || 0;
    var confTier  = conf >= 0.75 ? 'high' : conf >= 0.45 ? 'medium' : 'low';
    var confLabel = conf >= 0.75 ? 'HIGH' : conf >= 0.45 ? 'MEDIUM' : 'LOW';

    // Highlight the column matching nt_alignment
    var mtHighlight  = (alignment === 'mt')  ? ' text-form-highlight' : '';
    var lxxHighlight = (alignment === 'lxx' || alignment === 'lxx_recension') ? ' text-form-highlight' : '';

    var card = document.createElement('div');
    card.className = 'nt-ot-allusion-card result-card';
    card.style.borderLeftColor = alignInfo.color;

    card.innerHTML =
      // ── Card header ──────────────────────────────────────────────────────
      '<div class="allusion-card-header">' +
        '<span class="allusion-ot-ref">' + _esc(a.ot_reference || '') + '</span>' +
        '<span class="allusion-badges">' +
          '<span class="alignment-badge ' + alignInfo.cls + '" ' +
                'style="background:' + alignInfo.color + ';color:#fff;">' +
            _esc(alignInfo.label) +
          '</span>' +
          (a.contested
            ? '<span class="contested-badge">Contested</span>'
            : '') +
        '</span>' +
      '</div>' +

      // ── NT words cited ────────────────────────────────────────────────────
      (a.nt_words
        ? '<p class="allusion-nt-words">' +
            '<span class="field-label">NT words cited: </span>' +
            '<span class="greek-text">' + _esc(a.nt_words) + '</span>' +
          '</p>'
        : '') +

      // ── MT / LXX two-column comparison ───────────────────────────────────
      '<div class="text-form-columns">' +
        '<div class="text-form-col text-form-mt' + mtHighlight + '">' +
          '<div class="text-form-col-label">MT form</div>' +
          '<div class="text-form-col-value">' + _esc(a.ot_mt_form || '\u2014') + '</div>' +
        '</div>' +
        '<div class="text-form-col text-form-lxx' + lxxHighlight + '">' +
          '<div class="text-form-col-label">LXX form</div>' +
          '<div class="text-form-col-value">' + _esc(a.ot_lxx_form || '\u2014') + '</div>' +
        '</div>' +
      '</div>' +

      // ── Key word ──────────────────────────────────────────────────────────
      (a.key_word
        ? '<p class="allusion-key-word">' +
            '<span class="field-label">Key word: </span>' +
            '<strong class="greek-text">' + _esc(a.key_word) + '</strong>' +
          '</p>'
        : '') +

      // ── Technical analysis (scholar mode) ────────────────────────────────
      (a.textual_implication
        ? '<div class="technical-only allusion-implication">' +
            '<p>' + _esc(a.textual_implication) + '</p>' +
          '</div>'
        : '') +

      // ── Plain language (student mode) ────────────────────────────────────
      (a.textual_implication_plain
        ? '<div class="plain-highlight allusion-implication-plain">' +
            '<p>' + _esc(a.textual_implication_plain) + '</p>' +
          '</div>'
        : '') +

      // ── Scholarly note ────────────────────────────────────────────────────
      (a.scholarly_note
        ? '<p class="allusion-scholarly-note">' +
            '<span class="field-label">Scholarly note: </span>' +
            _esc(a.scholarly_note) +
          '</p>'
        : '') +

      // ── Confidence badge ──────────────────────────────────────────────────
      '<div class="allusion-card-footer">' +
        '<span class="confidence-badge confidence-' + confTier + '">' +
          confLabel + ' ' + Math.round(conf * 100) + '%' +
        '</span>' +
      '</div>';

    return card;
  }

  function buildHypothesisCard(data) {
    var h    = data.bibcrit_hypothesis || {};
    var conf = h.confidence || 0;
    var confTier  = conf >= 0.75 ? 'high' : conf >= 0.45 ? 'medium' : 'low';
    var confLabel = conf >= 0.75 ? 'HIGH' : conf >= 0.45 ? 'MEDIUM' : 'LOW';

    var card = document.createElement('div');
    card.className = 'nt-ot-hypothesis-card result-card hyp-card';
    card.innerHTML =
      '<div class="hyp-card-header">' +
        '<span class="hyp-card-title">\u2746 BibCrit Hypothesis</span>' +
        '<span class="hyp-card-subtitle">' + _esc(h.title || '') + '</span>' +
        '<span class="confidence-badge confidence-' + confTier + '">' + confLabel + '</span>' +
      '</div>' +
      (h.plain
        ? '<p class="hyp-card-plain plain-highlight">' + _esc(h.plain) + '</p>'
        : '') +
      (h.reasoning
        ? '<p class="hyp-card-reasoning technical-only">' + _esc(h.reasoning) + '</p>'
        : '') +
      '<p class="hyp-card-generated">generated by ' +
        _esc(_friendlyModel(data.model_version || 'BibCrit')) +
      '</p>';
    return card;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function _friendlyModel(modelId) {
    if (!modelId) return 'Claude';
    if (modelId.indexOf('opus')   !== -1) return 'Claude Opus';
    if (modelId.indexOf('sonnet') !== -1) return 'Claude Sonnet';
    if (modelId.indexOf('haiku')  !== -1) return 'Claude Haiku';
    return 'Claude';
  }

  function _formatCached(isoStr) {
    if (!isoStr) return '';
    try {
      var d = new Date(isoStr);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) { return ''; }
  }

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Public API ────────────────────────────────────────────────────────────
  window.ntOt = { analyze: analyze };

})();
