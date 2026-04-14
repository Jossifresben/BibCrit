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
    show(loadingState); hide(emptyState); hide(resultsArea); hide(passageHdr);
    document.getElementById('loading-step').textContent = '\u2026';
    document.getElementById('loading-timer').textContent = '';

    var startTime = Date.now();
    var timerInterval = setInterval(function () {
      var sec = Math.floor((Date.now() - startTime) / 1000);
      document.getElementById('loading-timer').textContent =
        sec > 5 ? sec + 's elapsed' : '';
    }, 1000);

    var url = '/api/source/stream?ref=' + encodeURIComponent(ref) + '&lang=' + LANG;
    var es = new EventSource(url);

    es.onmessage = function (e) {
      var msg = JSON.parse(e.data);
      if (msg.type === 'step') {
        document.getElementById('loading-step').textContent = msg.msg;
      } else if (msg.type === 'error') {
        clearInterval(timerInterval); es.close();
        hide(loadingState); showToast(msg.msg); show(emptyState);
      } else if (msg.type === 'done') {
        clearInterval(timerInterval); es.close();
        hide(loadingState);
        renderResults(msg.data, ref);
      }
    };

    es.onerror = function () {
      clearInterval(timerInterval); es.close();
      hide(loadingState);
      showToast('Connection error. Please try again.');
      show(emptyState);
    };
  }

  // ── Render ────────────────────────────────────────────────────────────────
  function renderResults(data, ref) {
    passageHdr.textContent = data.passage || ref;
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
