/* BibCrit — Manuscript Transmission Genealogy */

(function () {
  'use strict';

  var selBook    = document.getElementById('sel-book');
  var refInput   = document.getElementById('ref-input');
  var btnAnalyze = document.getElementById('btn-analyze');
  var infoBanner = document.getElementById('genealogy-info-banner');
  var infoClose  = document.getElementById('genealogy-info-close');
  var emptyState = document.getElementById('empty-state');
  var suggestions = document.getElementById('genealogy-suggestions');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var results    = document.getElementById('genealogy-results');
  var bibSec     = document.getElementById('bibcrit-assessment');
  var bibBody    = document.getElementById('bibcrit-body');
  var exportRow  = document.getElementById('export-row');
  var btnShare   = document.getElementById('btn-share');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  // ── Book select → text input sync ──────────────────────────────────────
  if (selBook) {
    selBook.addEventListener('change', function() {
      var book = this.value;
      if (book && refInput) refInput.value = book;
    });
  }

  // If pre-filled from URL, sync the select
  if (refInput && refInput.value && selBook) {
    var preBook = refInput.value.trim();
    for (var i = 0; i < selBook.options.length; i++) {
      if (selBook.options[i].value === preBook) {
        selBook.selectedIndex = i;
        break;
      }
    }
  }

  // ── Info banner dismiss ─────────────────────────────────────────────────
  var _BANNER_VER = 'genealogy-info-v1';
  if (localStorage.getItem(_BANNER_VER) === '1' && infoBanner) {
    infoBanner.style.display = 'none';
  }
  if (infoClose) {
    infoClose.addEventListener('click', function () {
      if (infoBanner) infoBanner.style.display = 'none';
      localStorage.setItem(_BANNER_VER, '1');
    });
  }

  var _es           = null;
  var _timer        = null;
  var _currentBook  = '';
  var _finalHandled = false;
  var _lastData     = null;

  // ── Suggestion chips ────────────────────────────────────────────────────
  document.querySelectorAll('.num-sug-chip[data-book]').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var book = this.getAttribute('data-book');
      if (!book) return;
      if (refInput) refInput.value = book;
      // Sync the select
      if (selBook) {
        for (var i = 0; i < selBook.options.length; i++) {
          if (selBook.options[i].value === book) { selBook.selectedIndex = i; break; }
        }
      }
      analyze(book);
    });
  });

  // ── Analyze button ──────────────────────────────────────────────────────
  btnAnalyze.addEventListener('click', function () {
    var book = refInput ? refInput.value.trim() : '';
    if (!book) { showToast(window.t('err_enter_book', 'Please enter a book name.')); return; }
    analyze(book);
  });

  if (refInput) {
    refInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') btnAnalyze.click();
    });
    refInput.addEventListener('input', function () {
      if (this.value.trim() === '') {
        var resVisible  = results   && results.style.display   !== 'none';
        var loadVisible = loadState && loadState.style.display !== 'none';
        if (!resVisible && !loadVisible) {
          show(suggestions);
          show(emptyState);
        }
      }
    });
  }

  // ── Core analyze ────────────────────────────────────────────────────────
  function analyze(book) {
    if (!book) return;
    _currentBook  = book;

    if (_es) { _es.close(); _es = null; }
    clearInterval(_timer);
    _finalHandled = false;

    hide(suggestions);
    hide(emptyState);
    hide(results);
    hide(heading);
    show(loadState);
    setLoadingStep('Preparing…');

    var elapsed = 0;
    _timer = setInterval(function () {
      elapsed++;
      if (loadTimer) loadTimer.textContent = elapsed + 's';
    }, 1000);

    history.replaceState(null, '', '/genealogy?book=' + encodeURIComponent(book));

    _es = new EventSource('/api/genealogy/stream?book=' + encodeURIComponent(book) + '&lang=' + (window.bibcritLang || 'en'));

    _es.addEventListener('message', function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          setLoadingStep(msg.msg);
        } else if (msg.type === 'error') {
          _finalHandled = true;
          clearInterval(_timer);
          setLoadingStep('❌ ' + msg.msg);
          _es.close();
        } else if (msg.type === 'done') {
          _finalHandled = true;
          clearInterval(_timer);
          _es.close();
          renderGenealogy(msg.data);
        }
      } catch (_) { /* ignore */ }
    });

    _es.onerror = function () {
      if (_finalHandled) return;
      clearInterval(_timer);
      setLoadingStep('❌ ' + window.t('err_connection_step', 'Connection error. Please try again.'));
      if (_es) _es.close();
    };
  }

  // ── Render ───────────────────────────────────────────────────────────────
  function renderGenealogy(data) {
    _lastData = data;
    hide(loadState);

    // Heading
    show(heading);
    heading.innerHTML = '<span class="ph-ref">' + _esc(data.book || _currentBook) + '</span>' +
      '<span class="ph-meta"> — Manuscript Transmission</span>';

    // Stemma visualization
    renderStemma(data);

    // Archetype description
    var archSec  = document.getElementById('archetype-section');
    var archBody = document.getElementById('archetype-body');
    if (data.archetype_description && archSec && archBody) {
      archBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(data.archetype_description) + '</p>' +
        '</div>';
      show(archSec);
    }

    // Key divergences
    var divSec  = document.getElementById('divergences-section');
    var divList = document.getElementById('divergences-list');
    var divs    = data.key_divergences || [];
    if (divs.length && divSec && divList) {
      divList.innerHTML = '';
      divs.forEach(function (d) {
        var card = document.createElement('div');
        card.className = 'genealogy-card';
        card.innerHTML =
          (d.title    ? '<div class="div-card-title">'   + _esc(d.title)   + '</div>' : '') +
          (d.passage  ? '<div class="div-card-passage">' + _esc(d.passage) + '</div>' : '') +
          (d.plain    ? '<p class="div-analysis">'       + _esc(d.plain)   + '</p>'   : '') +
          (d.detail   ? '<p class="div-meta" style="font-style:italic;margin-top:6px">' + _esc(d.detail) + '</p>' : '');
        divList.appendChild(card);
      });
      show(divSec);
    }

    // Transmission narrative
    var narSec  = document.getElementById('narrative-section');
    var narBody = document.getElementById('narrative-body');
    var plain   = data.transmission_plain || '';
    if (plain && narSec && narBody) {
      narBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(plain) + '</p>' +
        '</div>';
      show(narSec);
    }

    // BibCrit assessment
    renderAssessment(data);

    show(results);
    if (exportRow) show(exportRow);

    // Inject Scholar Rating, Copy, Download into export-row (once only)
    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'genealogy',
        getReference: function() { return _currentBook; },
        getResultData: function() { return _lastData || {}; },
        getSvgEl: function() { return document.getElementById('stemma-svg'); },
      });
    }

    // Wire SBL/BibTeX (once only)
    if (exportRow && !exportRow._exportWired) {
      exportRow._exportWired = true;
      var _btnSbl    = document.getElementById('btn-sbl');
      var _btnBibtex = document.getElementById('btn-bibtex');

      if (_btnSbl) {
        _btnSbl.addEventListener('click', function() {
          fetch('/api/export/sbl?tool=genealogy&ref=' + encodeURIComponent(_currentBook))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              var text = (d.footnotes || [d.footnote]).join('\n\n');
              navigator.clipboard.writeText(text).catch(function(){});
              showToast(window.t('toast_sbl_copied_short', 'SBL footnotes copied!'));
            }).catch(function(){});
        });
      }
      if (_btnBibtex) {
        _btnBibtex.addEventListener('click', function() {
          fetch('/api/export/bibtex?tool=genealogy&ref=' + encodeURIComponent(_currentBook))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              navigator.clipboard.writeText(d.bibtex || '').catch(function(){});
              showToast(window.t('toast_bibtex_copied_short', 'BibTeX copied!'));
            }).catch(function(){});
        });
      }
    }
  }

  // ── Stemma SVG helpers ────────────────────────────────────────────────────

  function _nodeWidth(label, date) {
    var labelW = Math.max((label || '').length * 7, (date || '').length * 6);
    return Math.max(110, Math.min(200, labelW + 24));
  }

  function _splitLabel(label) {
    var parenIdx = label.indexOf('(');
    if (parenIdx > 0 && parenIdx < label.length - 1) {
      return [label.slice(0, parenIdx).trim(), label.slice(parenIdx).trim()];
    }
    if (label.length > 20) {
      var mid = Math.floor(label.length / 2);
      var spaceIdx = label.indexOf(' ', mid);
      if (spaceIdx > 0) return [label.slice(0, spaceIdx), label.slice(spaceIdx + 1)];
    }
    return [label];
  }

  // ── Stemma SVG ────────────────────────────────────────────────────────────
  function renderStemma(data) {
    var svg = document.getElementById('stemma-svg');
    if (!svg) return;
    svg.innerHTML = '';

    var nodes = data.stemma_nodes || [];
    var edges = data.stemma_edges || [];
    if (!nodes.length) return;

    // Tradition colors
    var TRAD_COLORS = {
      MT:           { fill: '#fef3c7', stroke: '#d97706', text: '#92400e' },
      LXX:          { fill: '#dbeafe', stroke: '#2563eb', text: '#1e40af' },
      DSS:          { fill: '#f3e8ff', stroke: '#9333ea', text: '#7e22ce' },
      SP:           { fill: '#d1fae5', stroke: '#059669', text: '#065f46' },
      Peshitta:     { fill: '#ffedd5', stroke: '#ea580c', text: '#9a3412' },
      Targum:       { fill: '#fee2e2', stroke: '#dc2626', text: '#991b1b' },
      Vulgate:      { fill: '#f1f5f9', stroke: '#64748b', text: '#334155' },
      archetype:    { fill: '#1e293b', stroke: '#1e293b', text: '#fff'    },
      intermediate: { fill: '#e2e8f0', stroke: '#94a3b8', text: '#334155' },
      recension:    { fill: '#ede9fe', stroke: '#7c3aed', text: '#4c1d95' },
      edition:      { fill: '#f0fdf4', stroke: '#16a34a', text: '#14532d' },
      translation:  { fill: '#fff7ed', stroke: '#c2410c', text: '#7c2d12' },
    };

    // Pre-compute per-node widths and line splits
    var nodeWidths = {};
    var nodeLines  = {};
    nodes.forEach(function (n) {
      var rawLabel = n.label || n.id;
      nodeLines[n.id]  = _splitLabel(rawLabel);
      nodeWidths[n.id] = _nodeWidth(rawLabel, n.date);
    });

    // Build adjacency for layout
    var childrenMap = {};
    var parentMap   = {};
    nodes.forEach(function (n) { childrenMap[n.id] = []; });
    edges.forEach(function (e) {
      if (childrenMap[e.from] !== undefined) childrenMap[e.from].push(e.to);
      parentMap[e.to] = e.from;
    });

    // Find roots (nodes with no parent)
    var roots = nodes.filter(function (n) { return !parentMap[n.id]; });
    if (!roots.length) roots = [nodes[0]];

    // Assign depth (BFS)
    var depth = {};
    var queue = roots.map(function (r) { return r.id; });
    roots.forEach(function (r) { depth[r.id] = 0; });
    var maxDepth = 0;
    while (queue.length) {
      var cur = queue.shift();
      (childrenMap[cur] || []).forEach(function (child) {
        if (depth[child] === undefined) {
          depth[child] = depth[cur] + 1;
          if (depth[child] > maxDepth) maxDepth = depth[child];
          queue.push(child);
        }
      });
    }
    // Any node without depth gets maxDepth
    nodes.forEach(function (n) { if (depth[n.id] === undefined) depth[n.id] = maxDepth; });

    // Group by depth level
    var levels = {};
    nodes.forEach(function (n) {
      var d = depth[n.id] || 0;
      if (!levels[d]) levels[d] = [];
      levels[d].push(n);
    });

    // Layout constants
    var H_GAP = 20, V_GAP = 70, PADDING = 20;
    var ROW_H = 52; // max node height (two-line)

    // Compute minimum SVG width based on widest level
    var minSvgW = 900;
    for (var dl = 0; dl <= maxDepth; dl++) {
      var ln = levels[dl] || [];
      var levelTotalW = ln.reduce(function (acc, n) { return acc + (nodeWidths[n.id] || 110); }, 0);
      levelTotalW += (ln.length - 1) * H_GAP + PADDING * 2;
      if (levelTotalW > minSvgW) minSvgW = levelTotalW;
    }

    // Assign x,y positions using per-node widths
    var positions = {};
    for (var d = 0; d <= maxDepth; d++) {
      var levelNodes = levels[d] || [];
      var totalW = levelNodes.reduce(function (acc, n) { return acc + (nodeWidths[n.id] || 110); }, 0);
      totalW += (levelNodes.length - 1) * H_GAP;
      var startX = (minSvgW - totalW) / 2;
      var y      = PADDING + d * (ROW_H + V_GAP);
      var cx     = startX;
      levelNodes.forEach(function (n) {
        positions[n.id] = { x: cx, y: y };
        cx += (nodeWidths[n.id] || 110) + H_GAP;
      });
    }

    // Compute actual content width (rightmost node edge + padding)
    var maxX = 0;
    nodes.forEach(function (n) {
      var pos = positions[n.id];
      if (pos) maxX = Math.max(maxX, pos.x + (nodeWidths[n.id] || 110));
    });
    var contentW = Math.max(minSvgW, maxX + PADDING);
    var svgH     = (maxDepth + 1) * (ROW_H + V_GAP) + PADDING * 2;

    // Set SVG dimensions
    svg.setAttribute('viewBox', '0 0 ' + contentW + ' ' + svgH);
    svg.setAttribute('width',   contentW);
    svg.setAttribute('height',  svgH);
    svg.style.minWidth = contentW + 'px';

    var ns = 'http://www.w3.org/2000/svg';

    // Draw edges first (behind nodes)
    edges.forEach(function (e) {
      var from = positions[e.from];
      var to   = positions[e.to];
      if (!from || !to) return;
      var fromH = (nodeLines[e.from] || []).length > 1 ? 52 : 44;
      var x1 = from.x + (nodeWidths[e.from] || 110) / 2;
      var y1 = from.y + fromH;
      var x2 = to.x   + (nodeWidths[e.to]   || 110) / 2;
      var y2 = to.y;
      var path = document.createElementNS(ns, 'path');
      var cy   = (y1 + y2) / 2;
      path.setAttribute('d',
        'M' + x1 + ',' + y1 +
        ' C' + x1 + ',' + cy +
        ' ' + x2 + ',' + cy +
        ' ' + x2 + ',' + y2
      );
      path.setAttribute('class', 'stemma-edge');
      svg.appendChild(path);
    });

    // Draw nodes
    nodes.forEach(function (n) {
      var pos = positions[n.id];
      if (!pos) return;

      var trad     = n.tradition || n.type || 'intermediate';
      var colors   = TRAD_COLORS[trad] || TRAD_COLORS['intermediate'];
      var nw       = nodeWidths[n.id] || 110;
      var lines    = nodeLines[n.id]  || [n.label || n.id];
      var twoLine  = lines.length > 1;
      var nodeH    = twoLine ? 52 : 44;

      var g = document.createElementNS(ns, 'g');
      g.setAttribute('class', 'stemma-node');
      g.setAttribute('transform', 'translate(' + pos.x + ',' + pos.y + ')');

      // Tooltip via title
      if (n.description) {
        var title = document.createElementNS(ns, 'title');
        title.textContent = n.description;
        g.appendChild(title);
      }

      var rect = document.createElementNS(ns, 'rect');
      rect.setAttribute('width',        nw);
      rect.setAttribute('height',       nodeH);
      rect.setAttribute('rx',           6);
      rect.setAttribute('fill',         colors.fill);
      rect.setAttribute('stroke',       colors.stroke);
      rect.setAttribute('stroke-width', '1.5');
      g.appendChild(rect);

      if (twoLine) {
        var l1 = document.createElementNS(ns, 'text');
        l1.setAttribute('x',           nw / 2);
        l1.setAttribute('y',           14);
        l1.setAttribute('text-anchor', 'middle');
        l1.setAttribute('fill',        colors.text);
        l1.setAttribute('font-family', "'Space Grotesk', sans-serif");
        l1.setAttribute('font-size',   '11');
        l1.setAttribute('font-weight', '700');
        l1.textContent = lines[0];
        g.appendChild(l1);

        var l2 = document.createElementNS(ns, 'text');
        l2.setAttribute('x',           nw / 2);
        l2.setAttribute('y',           26);
        l2.setAttribute('text-anchor', 'middle');
        l2.setAttribute('fill',        colors.text);
        l2.setAttribute('font-family', "'Space Grotesk', sans-serif");
        l2.setAttribute('font-size',   '11');
        l2.setAttribute('font-weight', '700');
        l2.textContent = lines[1];
        g.appendChild(l2);

        if (n.date) {
          var dateText = document.createElementNS(ns, 'text');
          dateText.setAttribute('x',           nw / 2);
          dateText.setAttribute('y',           38);
          dateText.setAttribute('text-anchor', 'middle');
          dateText.setAttribute('fill',        '#888');
          dateText.setAttribute('font-family', "'Space Grotesk', sans-serif");
          dateText.setAttribute('font-size',   '9');
          dateText.textContent = n.date;
          g.appendChild(dateText);
        }
      } else {
        var label = document.createElementNS(ns, 'text');
        label.setAttribute('x',           nw / 2);
        label.setAttribute('y',           16);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('fill',        colors.text);
        label.setAttribute('font-family', "'Space Grotesk', sans-serif");
        label.setAttribute('font-size',   '11');
        label.setAttribute('font-weight', '700');
        label.textContent = lines[0];
        g.appendChild(label);

        if (n.date) {
          var dateText = document.createElementNS(ns, 'text');
          dateText.setAttribute('x',           nw / 2);
          dateText.setAttribute('y',           30);
          dateText.setAttribute('text-anchor', 'middle');
          dateText.setAttribute('fill',        '#888');
          dateText.setAttribute('font-family', "'Space Grotesk', sans-serif");
          dateText.setAttribute('font-size',   '9');
          dateText.textContent = n.date;
          g.appendChild(dateText);
        }
      }

      svg.appendChild(g);
    });

    // Show section
    var sec = document.getElementById('stemma-section');
    if (sec) sec.style.display = '';
  }

  // ── Stemma fullscreen button ─────────────────────────────────────────────
  var fsBtn      = document.getElementById('stemma-fullscreen-btn');
  var stemmaWrap = document.getElementById('stemma-wrap');
  if (fsBtn && stemmaWrap) {
    fsBtn.addEventListener('click', function () {
      if (!document.fullscreenElement) {
        stemmaWrap.requestFullscreen().catch(function () {});
        fsBtn.querySelector('.material-symbols-outlined').textContent = 'fullscreen_exit';
      } else {
        document.exitFullscreen();
        fsBtn.querySelector('.material-symbols-outlined').textContent = 'fullscreen';
      }
    });
    document.addEventListener('fullscreenchange', function () {
      if (!document.fullscreenElement) {
        fsBtn.querySelector('.material-symbols-outlined').textContent = 'fullscreen';
      }
    });
  }

  // ── BibCrit assessment ───────────────────────────────────────────────────
  function renderAssessment(data) {
    var ass = data.bibcrit_assessment || {};
    if (!ass.title && !ass.plain) return;

    var conf    = ass.confidence || 0;
    var pct     = Math.round(conf * 100);
    var confCls = conf >= 0.75 ? 'badge-high' : conf >= 0.45 ? 'badge-medium' : 'badge-low';

    if (bibBody) {
      bibBody.innerHTML =
        '<div class="bt-group-card">' +
          (ass.title ? '<h3 style="margin:0 0 12px;font-size:16px">' + _esc(ass.title) + '</h3>' : '') +
          '<p class="div-analysis">' + _esc(ass.plain || '') + '</p>' +
          (ass.reasoning ? '<p class="div-meta" style="font-style:italic;margin-top:8px">' + _esc(ass.reasoning) + '</p>' : '') +
          (pct ? '<p style="margin-top:10px"><span class="conf-badge ' + confCls + '">Confidence: ' + pct + '%</span></p>' : '') +
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + '</p>' +
        '</div>';
    }
    if (bibSec) show(bibSec);
  }

  // ── Share button ─────────────────────────────────────────────────────────
  if (btnShare) {
    btnShare.addEventListener('click', function () {
      var shareToggle = document.getElementById('share-toggle');
      if (shareToggle) shareToggle.click();
    });
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  function setLoadingStep(msg) { if (loadStep) loadStep.textContent = msg; }
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    show(toast);
    setTimeout(function () { hide(toast); }, 2500);
  }

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _friendlyModel(modelId) {
    if (!modelId) return 'Claude';
    if (modelId.indexOf('opus')   !== -1) return 'Claude Opus';
    if (modelId.indexOf('sonnet') !== -1) return 'Claude Sonnet';
    if (modelId.indexOf('haiku')  !== -1) return 'Claude Haiku';
    return 'Claude';
  }

  // ── Public API ───────────────────────────────────────────────────────────
  window.genealogy = { analyze: analyze };

})();
