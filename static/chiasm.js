/**
 * chiasm.js — BibCrit Chiasm & Literary Structure Detector
 *
 * Responsibilities:
 *   - Corpus browser: cascading book/chapter/verse selects (MT tradition)
 *   - Fetch and render chiasm analysis from /api/chiasm/stream
 *   - Render the A-B-C-X-C'-B'-A' structure diagram with confidence bars
 *   - Render correspondences table and theological significance
 *   - BibCrit hypothesis card
 */

(function () {
  'use strict';

  var LANG = window.BIBCRIT_LANG || document.documentElement.lang || 'en';

  // ── Structure color config ────────────────────────────────────────────────
  var STRUCT_COLORS = {
    'A': '#2563eb', 'B': '#7c3aed', 'C': '#059669', 'D': '#d97706',
    'E': '#dc2626', 'F': '#0891b2',
    "A'": '#2563eb', "B'": '#7c3aed', "C'": '#059669', "D'": '#d97706',
    "E'": '#dc2626', "F'": '#0891b2',
    'X': '#1e1e3a',
  };

  // ── DOM refs ──────────────────────────────────────────────────────────────
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
    _currentRef      = ref;
    _finalHandled    = false;
    _partialData     = {};
    _sectionReceived = false;
    show(loadingState); hide(emptyState); hide(resultsArea); hide(passageHdr);
    document.getElementById('loading-step').textContent = '\u2026';
    document.getElementById('loading-timer').textContent = '';

    var startTime = Date.now();
    var timerInterval = setInterval(function () {
      var sec = Math.floor((Date.now() - startTime) / 1000);
      document.getElementById('loading-timer').textContent =
        sec > 5 ? sec + 's elapsed' : '';
    }, 1000);

    var url = '/api/chiasm/stream?ref=' + encodeURIComponent(ref) + '&lang=' + LANG;
    var es = new EventSource(url);

    es.onmessage = function (e) {
      var msg = JSON.parse(e.data);
      if (msg.type === 'step') {
        document.getElementById('loading-step').textContent = msg.msg;
      } else if (msg.type === 'section') {
        _renderSection(msg.key, msg.data);
      } else if (msg.type === 'error') {
        _finalHandled = true;
        clearInterval(timerInterval); es.close();
        hide(loadingState);
        showToast(msg.msg);
        show(emptyState);
      } else if (msg.type === 'done') {
        _finalHandled = true;
        clearInterval(timerInterval); es.close();
        if (_sectionReceived) {
          _finalize(msg.data, ref);
        } else {
          hide(loadingState);
          renderResults(msg.data, ref);
        }
      }
    };

    es.onerror = function () {
      if (_finalHandled) return;
      clearInterval(timerInterval); es.close();
      hide(loadingState);
      showToast('Connection error. Please try again.');
      show(emptyState);
    };
  }

  // ── Progressive section rendering ─────────────────────────────────────────
  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived  = true;

    if (key === 'structure') {
      // Hide loading and reveal results only when content is ready to show
      if (loadingState) loadingState.style.display = 'none';
      if (emptyState)   emptyState.style.display   = 'none';
      if (resultsArea)  resultsArea.style.display  = '';
      if (passageHdr) {
        passageHdr.textContent = _currentRef;
        show(passageHdr);
      }
      // Render structure diagram early with partial data
      var partial = Object.assign({ structure_detected: !!(data && (data.elements || data.structure_detected)) }, data || {});
      renderResults(partial, _currentRef);
    }

    if (key === 'parallel_analysis') {
      // Re-render with accumulated data (correspondences may be in here)
      var acc = Object.assign({}, _partialData.structure || {}, { correspondences: Array.isArray(data) ? data : (data && data.correspondences) || [] });
      renderResults(acc, _currentRef);
    }

    if (key === 'literary_function') {
      var sigData = Object.assign({}, _partialData.structure || {}, {
        theological_significance: typeof data === 'string' ? data : (data && (data.theological_significance || data.plain || '')),
      });
      renderResults(sigData, _currentRef);
    }

    if (key === 'assessment') {
      var hypData = Object.assign({}, _partialData.structure || {}, {
        bibcrit_hypothesis: data,
      });
      renderResults(hypData, _currentRef);
    }
  }

  function _finalize(data, ref) {
    hide(loadingState);
    renderResults(data || _partialData, ref || _currentRef);
  }

  // ── Render ────────────────────────────────────────────────────────────────
  function renderResults(data, ref) {
    passageHdr.textContent = data.passage || ref;
    show(passageHdr);

    resultsArea.innerHTML = '';

    if (!data.structure_detected) {
      resultsArea.innerHTML = '<div class="result-card"><p class="muted">' +
        (data.theological_significance || 'No chiastic structure detected in this passage.') +
        '</p></div>';
      show(resultsArea);
      if (window.staggerReveal) staggerReveal(resultsArea, 0);
      return;
    }

    // ── Structure diagram ─────────────────────────────────────────────────
    var diagramDiv = document.createElement('div');
    diagramDiv.className = 'result-card';
    diagramDiv.innerHTML = '<h3 class="result-section-title">Literary Structure \u2014 ' +
      capitalise(data.structure_type || 'concentric') + '</h3>';

    var diagram = document.createElement('div');
    diagram.className = 'chiasm-diagram';

    var els = data.elements || [];
    var pivotLabel = data.pivot ? data.pivot.label : null;
    var maxIndent  = Math.floor(els.length / 2);

    els.forEach(function (el, i) {
      var isPivot = el.label === pivotLabel;
      var indent  = isPivot ? maxIndent : Math.min(i, els.length - 1 - i);
      var color   = STRUCT_COLORS[el.label] || '#6b7280';

      var row = document.createElement('div');
      row.className = 'chiasm-row' + (isPivot ? ' chiasm-pivot' : '');
      row.style.paddingLeft = (indent * 24) + 'px';

      var badge = document.createElement('span');
      badge.className = 'chiasm-label';
      badge.textContent = el.label;
      badge.style.background = color;

      var content = document.createElement('div');
      content.className = 'chiasm-content';

      var verses = document.createElement('span');
      verses.className = 'chiasm-verses';
      verses.textContent = el.verses;

      var summary = document.createElement('span');
      summary.className = 'chiasm-summary';
      summary.textContent = el.summary;

      var conf = document.createElement('span');
      conf.className = 'chiasm-conf';
      var pct = Math.round((el.confidence || 0) * 100);
      conf.textContent = pct + '%';
      conf.title = 'Confidence: ' + pct + '%';

      content.appendChild(verses);
      content.appendChild(summary);
      content.appendChild(conf);
      row.appendChild(badge);
      row.appendChild(content);
      diagram.appendChild(row);
    });

    diagramDiv.appendChild(diagram);

    // ── Pivot note ────────────────────────────────────────────────────────
    if (data.pivot) {
      var pivotNote = document.createElement('div');
      pivotNote.className = 'chiasm-pivot-note';
      pivotNote.innerHTML = '<strong>' + escHtml(data.pivot.label) + ' \u2014 ' +
        escHtml(data.pivot.summary) + '</strong> ' +
        escHtml(data.pivot.theological_weight || '');
      diagramDiv.appendChild(pivotNote);
    }

    // ── Overall confidence ────────────────────────────────────────────────
    if (data.overall_confidence) {
      var confRow = document.createElement('div');
      confRow.className = 'chiasm-overall-conf';
      var pct = Math.round(data.overall_confidence * 100);
      confRow.innerHTML = 'Overall confidence: <strong>' + pct + '%</strong>';
      if (data.confidence_note) {
        confRow.innerHTML += ' \u2014 <span class="muted">' +
          escHtml(data.confidence_note) + '</span>';
      }
      diagramDiv.appendChild(confRow);
    }

    resultsArea.appendChild(diagramDiv);

    // ── Correspondences ───────────────────────────────────────────────────
    var corrList = data.correspondences || [];
    if (corrList.length) {
      var corrDiv = document.createElement('div');
      corrDiv.className = 'result-card';
      corrDiv.innerHTML = '<h3 class="result-section-title">Correspondences</h3>';
      var table = document.createElement('table');
      table.className = 'chiasm-corr-table';
      table.innerHTML = '<thead><tr><th>Pair</th><th>Evidence</th><th>Confidence</th></tr></thead>';
      var tbody = document.createElement('tbody');
      corrList.forEach(function (c) {
        var tr = document.createElement('tr');
        var pairLabel = Array.isArray(c.pair) ? c.pair.join(' / ') : (c.pair || '');
        tr.innerHTML = '<td><strong>' + escHtml(pairLabel) + '</strong></td>' +
          '<td>' + escHtml(c.evidence || '') + '</td>' +
          '<td>' + Math.round((c.confidence || 0) * 100) + '%</td>';
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      corrDiv.appendChild(table);
      resultsArea.appendChild(corrDiv);
    }

    // ── Theological significance + scholarly citations ─────────────────────
    if (data.theological_significance || data.scholarly_citations) {
      var sigDiv = document.createElement('div');
      sigDiv.className = 'result-card';
      sigDiv.innerHTML = '<h3 class="result-section-title">Theological Significance</h3>';
      if (data.theological_significance) {
        var p = document.createElement('p');
        p.textContent = data.theological_significance;
        sigDiv.appendChild(p);
      }
      if (data.methodology_citations) {
        var meth = document.createElement('p');
        meth.className = 'muted';
        meth.textContent = 'Methodology: ' + data.methodology_citations;
        sigDiv.appendChild(meth);
      }
      if (data.scholarly_citations) {
        var schol = document.createElement('p');
        schol.className = 'muted';
        schol.textContent = data.scholarly_citations;
        sigDiv.appendChild(schol);
      }
      resultsArea.appendChild(sigDiv);
    }

    // ── BibCrit hypothesis card ────────────────────────────────────────────
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

    // Result actions (copy / vote)
    if (window.ResultActions) {
      ResultActions.attach(resultsArea, { reference: ref, tool: 'chiasm', data: data });
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }
  function capitalise(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
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

  // Expose for autoload from template
  window.chiasm = { analyze: analyze };

}());
