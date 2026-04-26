/**
 * source.js — BibCrit Source Criticism Tool (J/E/D/P)
 *
 * Responsibilities:
 *   - Corpus browser: cascading book/chapter/verse selects (MT tradition)
 *   - Fetch and render source analysis from /api/source/stream
 *   - Render color-coded source units, doublets table, competing positions
 *   - BibCrit hypothesis card
 */

(function () {
  'use strict';

  var LANG = window.BIBCRIT_LANG || document.documentElement.lang || 'en';

  var SOURCE_COLORS = {
    'J': { bg: '#fef9c3', border: '#ca8a04', text: '#92400e', badge: '#d97706' },
    'E': { bg: '#dcfce7', border: '#16a34a', text: '#14532d', badge: '#16a34a' },
    'D': { bg: '#dbeafe', border: '#2563eb', text: '#1e40af', badge: '#2563eb' },
    'P': { bg: '#f3e8ff', border: '#7c3aed', text: '#4c1d95', badge: '#7c3aed' },
    'R': { bg: '#f1f5f9', border: '#64748b', text: '#334155', badge: '#64748b' },
  };

  var selBook      = document.getElementById('sel-book');
  var selChapter   = document.getElementById('sel-chapter');
  var selVerse     = document.getElementById('sel-verse');
  var refInput     = document.getElementById('ref-input');
  var btnAnalyze   = document.getElementById('btn-analyze');
  var emptyState   = document.getElementById('empty-state');
  var loadingState = document.getElementById('loading-state');
  var resultsArea  = document.getElementById('results-area');
  var passageHdr   = document.getElementById('passage-heading');

  if (!selBook || !btnAnalyze) return;

  var _finalHandled   = false;
  var _partialData    = {};
  var _sectionReceived = false;
  var _currentRef     = '';
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
  function _renderSkeleton() {
    var ra = document.getElementById('results-area');
    if (!ra) return;
    ra.style.display = '';
    ra.innerHTML =
      '<div style="padding:1.5rem 1rem">' +
      '<div class="dss-skel-row" style="height:18px;width:55%;margin-bottom:1.5rem"></div>' +
      _skelRows(4, [100, 90, 78, 65]) +
      '<div class="dss-skel-row" style="height:14px;width:35%;margin-top:1.5rem;margin-bottom:.75rem"></div>' +
      _skelRows(3, [95, 82, 68]) +
      '</div>';
  }

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

  // ── Corpus browser ────────────────────────────────────────────────────────
  function fetchBooks() {
    fetch('/api/books?tradition=MT')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.books || []).forEach(function (b) {
          var o = document.createElement('option');
          o.value = b; o.textContent = b;
          selBook.appendChild(o);
        });
      }).catch(function () {});
  }

  selBook.addEventListener('change', function () {
    selChapter.innerHTML = '<option value="">Ch\u2026</option>';
    selChapter.disabled = true;
    selVerse.innerHTML = '<option value="">Vs\u2026</option>';
    selVerse.disabled = true;
    if (!selBook.value) return;
    fetch('/api/chapters?tradition=MT&book=' + encodeURIComponent(selBook.value))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.chapters || []).forEach(function (c) {
          var o = document.createElement('option');
          o.value = c; o.textContent = c;
          selChapter.appendChild(o);
        });
        selChapter.disabled = false;
      }).catch(function () {});
  });

  selChapter.addEventListener('change', function () {
    selVerse.innerHTML = '<option value="">Vs\u2026</option>';
    selVerse.disabled = true;
    if (!selBook.value || !selChapter.value) return;
    refInput.value = selBook.value + ' ' + selChapter.value;
    fetch('/api/verses?tradition=MT&book=' + encodeURIComponent(selBook.value) +
          '&chapter=' + encodeURIComponent(selChapter.value))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.verses || []).forEach(function (v) {
          var o = document.createElement('option');
          o.value = v; o.textContent = v;
          selVerse.appendChild(o);
        });
        selVerse.disabled = false;
      }).catch(function () {});
  });

  selVerse.addEventListener('change', function () {
    if (selBook.value && selChapter.value && selVerse.value) {
      refInput.value = selBook.value + ' ' + selChapter.value + ':' + selVerse.value;
    }
  });

  // ── SSE analysis ──────────────────────────────────────────────────────────
  function analyze(ref) {
    if (!ref) return;
    if (window.BibCrit_checkPassageLength && window.BibCrit_checkPassageLength(ref)) return;
    if (window.BibCrit_requireVerse && window.BibCrit_requireVerse(ref)) return;
    _currentRef      = ref;
    _finalHandled    = false;
    _partialData     = {};
    _sectionReceived = false;
    clearInterval(_timer);
    hide(emptyState);
    if (loadingState) {
      loadingState.classList.add('is-compact');
      loadingState.style.display = 'block';
    }
    if (passageHdr) {
      passageHdr.innerHTML = '<span class="ph-ref">' + escHtml(ref) + '</span>';
      show(passageHdr);
    }
    document.getElementById('loading-step').textContent = '\u2026';
    document.getElementById('loading-timer').textContent = '';

    var startTime = Date.now();
    var timerInterval = setInterval(function () {
      var sec = Math.floor((Date.now() - startTime) / 1000);
      document.getElementById('loading-timer').textContent =
        sec > 5 ? sec + 's elapsed' : '';
    }, 1000);
    _timer = timerInterval;
    _renderSkeleton();

    var url = '/api/source/stream?ref=' + encodeURIComponent(ref) + '&lang=' + LANG;
    var es = new EventSource(url);

    es.onmessage = function (e) {
      var msg = JSON.parse(e.data);
      if (msg.type === 'step') {
        document.getElementById('loading-step').textContent = msg.msg;
      } else if (msg.type === 'section') {
        _renderSection(msg.key, msg.data);
      } else if (msg.type === 'error') {
        _finalHandled = true;
        _hideCompactSpinner(); es.close();
        showToast(msg.msg); show(emptyState);
      } else if (msg.type === 'done') {
        _finalHandled = true;
        _hideCompactSpinner(); es.close();
        if (_sectionReceived) {
          _finalize(msg.data, ref);
        } else {
          renderResults(msg.data, ref);
        }
      }
    };

    es.onerror = function () {
      if (_finalHandled) return;
      _hideCompactSpinner(); es.close();
      showToast('Connection error. Please try again.');
      show(emptyState);
    };
  }

  // ── Progressive section rendering ─────────────────────────────────────────
  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived  = true;

    if (key === 'units') {
      // Hide loading and reveal results only when content is ready to show
      if (emptyState)   emptyState.style.display   = 'none';
      if (resultsArea)  resultsArea.style.display  = '';
      if (passageHdr) { passageHdr.innerHTML = '<span class="ph-ref">' + escHtml(_currentRef) + '</span>'; show(passageHdr); }
      // Render source units
      var units = Array.isArray(data) ? data : (data && data.source_units) || [];
      var partial = { source_units: units };
      renderResults(partial, _currentRef);
    }

    if (key === 'source_summary') {
      // re-render with accumulated units + summary
      var acc = Object.assign({}, _partialData.units ? { source_units: _partialData.units } : {},
        { synthesis: typeof data === 'string' ? data : (data && (data.synthesis || data.summary || '')) });
      renderResults(acc, _currentRef);
    }

    if (key === 'redaction_notes') {
      var accRed = Object.assign({},
        _partialData.units ? { source_units: _partialData.units } : {},
        { competing_positions: Array.isArray(data) ? data : (data && data.competing_positions) || [] });
      renderResults(accRed, _currentRef);
    }

    if (key === 'assessment') {
      var hypData = {
        bibcrit_hypothesis: data,
      };
      renderResults(hypData, _currentRef);
    }
  }

  function _finalize(data, ref) {
    _hideCompactSpinner();
    renderResults(data || _partialData, ref || _currentRef);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  function renderResults(data, ref) {
    passageHdr.innerHTML = '<span class="ph-ref">' + escHtml(data.passage || ref) + '</span>';
    show(passageHdr);
    resultsArea.innerHTML = '';

    // ── Scope note ────────────────────────────────────────────────────────
    if (data.scope_note) {
      var scopeDiv = document.createElement('div');
      scopeDiv.className = 'result-card';
      var scopeP = document.createElement('p');
      scopeP.className = 'muted';
      scopeP.textContent = data.scope_note;
      scopeDiv.appendChild(scopeP);
      resultsArea.appendChild(scopeDiv);
    }

    // ── Source units ──────────────────────────────────────────────────────
    var units = data.source_units || [];
    if (units.length) {
      var unitsDiv = document.createElement('div');
      unitsDiv.className = 'result-card';
      unitsDiv.innerHTML = '<h3 class="result-section-title">Source Attribution</h3>';

      units.forEach(function (u) {
        var colors = SOURCE_COLORS[u.source] || SOURCE_COLORS['R'];
        var unitDiv = document.createElement('div');
        unitDiv.className = 'source-unit';
        unitDiv.style.borderLeftColor = colors.border;
        unitDiv.style.background = colors.bg;

        var header = document.createElement('div');
        header.className = 'source-unit-header';

        var badge = document.createElement('span');
        badge.className = 'src-badge';
        badge.textContent = u.source || '?';
        badge.style.background = colors.badge;
        badge.style.color = '#fff';

        var verses = document.createElement('span');
        verses.className = 'source-unit-verses';
        verses.textContent = u.verses || '';

        var conf = document.createElement('span');
        conf.className = 'source-unit-conf';
        conf.textContent = Math.round((u.confidence || 0) * 100) + '% confidence';

        header.appendChild(badge);
        header.appendChild(verses);
        header.appendChild(conf);
        unitDiv.appendChild(header);

        if (u.divine_name_used) {
          var dname = document.createElement('p');
          dname.className = 'source-meta';
          dname.innerHTML = '<strong>Divine name:</strong> ' + escHtml(u.divine_name_used);
          unitDiv.appendChild(dname);
        }

        if (u.key_vocabulary && u.key_vocabulary.length) {
          var vocab = document.createElement('p');
          vocab.className = 'source-meta';
          vocab.innerHTML = '<strong>Key vocabulary:</strong> ' +
            u.key_vocabulary.map(escHtml).join(', ');
          unitDiv.appendChild(vocab);
        }

        if (u.theological_concerns) {
          var theo = document.createElement('p');
          theo.className = 'source-meta';
          theo.innerHTML = '<strong>Theological concerns:</strong> ' +
            escHtml(u.theological_concerns);
          unitDiv.appendChild(theo);
        }

        var summ = document.createElement('p');
        summ.textContent = u.summary || '';
        unitDiv.appendChild(summ);

        unitsDiv.appendChild(unitDiv);
      });

      resultsArea.appendChild(unitsDiv);
    }

    // ── Doublets ──────────────────────────────────────────────────────────
    var doublets = data.doublets || [];
    if (doublets.length) {
      var dDiv = document.createElement('div');
      dDiv.className = 'result-card';
      dDiv.innerHTML = '<h3 class="result-section-title">Doublets</h3>';
      doublets.forEach(function (d) {
        var row = document.createElement('div');
        row.className = 'doublet-row';
        row.innerHTML = '<strong>' + escHtml(d.unit_1_verses || '') + ' / ' +
          escHtml(d.unit_2_verses || '') + '</strong> \u2014 ' +
          escHtml(d.description || '') +
          '<br><span class="muted">' + escHtml(d.significance || '') + '</span>';
        dDiv.appendChild(row);
      });
      resultsArea.appendChild(dDiv);
    }

    // ── Competing positions ───────────────────────────────────────────────
    var positions = data.competing_positions || [];
    if (positions.length) {
      var posDiv = document.createElement('div');
      posDiv.className = 'result-card';
      posDiv.innerHTML = '<h3 class="result-section-title">Scholarly Positions</h3>';
      positions.forEach(function (pos) {
        var row = document.createElement('div');
        row.className = 'competing-position';
        row.innerHTML = '<strong>' + escHtml(pos.scholar || '') + ':</strong> ' +
          escHtml(pos.attribution || '') +
          (pos.note ? ' <span class="muted">(' + escHtml(pos.note) + ')</span>' : '');
        posDiv.appendChild(row);
      });
      resultsArea.appendChild(posDiv);
    }

    // ── Synthesis + framework note ────────────────────────────────────────
    if (data.synthesis) {
      var synthDiv = document.createElement('div');
      synthDiv.className = 'result-card';
      synthDiv.innerHTML = '<h3 class="result-section-title">Synthesis</h3>';
      var synthP = document.createElement('p');
      synthP.textContent = data.synthesis;
      synthDiv.appendChild(synthP);
      if (data.framework_note) {
        var fwNote = document.createElement('p');
        fwNote.className = 'muted';
        fwNote.textContent = data.framework_note;
        synthDiv.appendChild(fwNote);
      }
      resultsArea.appendChild(synthDiv);
    }

    // ── BibCrit hypothesis ────────────────────────────────────────────────
    var hyp = data.bibcrit_hypothesis;
    if (hyp && hyp.title) {
      var hypDiv = document.createElement('div');
      hypDiv.className = 'result-card bibcrit-hypothesis';
      hypDiv.innerHTML = '<h3 class="result-section-title">BibCrit Assessment</h3>' +
        '<p class="hyp-title">' + escHtml(hyp.title) + '</p>' +
        '<p>' + escHtml(hyp.reasoning || '') + '</p>';
      if (hyp.confidence) {
        hypDiv.innerHTML += '<p class="muted">Confidence: ' +
          Math.round(hyp.confidence * 100) + '%</p>';
      }
      resultsArea.appendChild(hypDiv);
    }

    show(resultsArea);
    if (window.staggerReveal) staggerReveal(resultsArea, 90);

    if (window.ResultActions) {
      ResultActions.attach(resultsArea, { reference: ref, tool: 'source', data: data });
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }
  function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;');
  }
  function showToast(msg) {
    var t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg; t.style.display = 'block';
    setTimeout(function () { t.style.display = 'none'; }, 4000);
  }

  window.sourceCrit = { analyze: analyze };

}());
