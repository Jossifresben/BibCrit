/* BibCrit — Scribal Tendency Profiler */

(function () {
  'use strict';

  var selBook    = document.getElementById('sel-book');
  var selBook2   = document.getElementById('sel-book-2');
  var chkCompare = document.getElementById('chk-compare');
  var compareWrap = document.getElementById('compare-wrap');
  var btnAnalyze = document.getElementById('btn-analyze');
  var infoBanner  = document.getElementById('scribal-info-banner');
  var infoClose   = document.getElementById('scribal-info-close');
  var emptyState = document.getElementById('empty-state');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var radarArea       = document.getElementById('radar-area');
  var radarSvg        = document.getElementById('radar-chart');
  var radarLegend     = document.getElementById('radar-legend');
  var btnExpand       = document.getElementById('btn-radar-expand');
  var radarModal      = document.getElementById('radar-modal');
  var radarModalSvg   = document.getElementById('radar-chart-modal');
  var radarModalClose = document.getElementById('radar-modal-close');
  var radarModalLegend = document.getElementById('radar-modal-legend');
  var overallDiv = document.getElementById('scribal-overall');
  var tabsArea   = document.getElementById('tabs-area');
  var tabsNav    = document.getElementById('tabs-nav');
  var tabsBody   = document.getElementById('tabs-body');
  var exportRow  = document.getElementById('export-row');
  var btnSbl     = document.getElementById('btn-sbl');
  var toast      = document.getElementById('toast');

  if (!selBook || !btnAnalyze) return;

  // ── Info banner dismiss ─────────────────────────────────────────────────
  var _BANNER_VER = 'scribal-info-v2';   // bump to re-show after content changes
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
  var _timerInt     = null;
  var _data1        = null;
  var _finalHandled = false;
  var _data2      = null;
  var _currentBook = '';
  var _lastData    = null;

  // Radar color palette per series
  var SERIES_COLORS = ['#3a6bc4', '#e67e22'];

  // Five dimensions in display order
  var DIMS = [
    { key: 'literalness',                label: 'Literalness' },
    { key: 'anthropomorphism_reduction', label: 'Anthrop. Reduction' },
    { key: 'messianic_heightening',      label: 'Messianic Heightening' },
    { key: 'harmonization',              label: 'Harmonization' },
    { key: 'paraphrase_rate',            label: 'Paraphrase Rate' },
  ];

  // ── Compare toggle ──────────────────────────────────────────────────────
  if (chkCompare) {
    chkCompare.addEventListener('change', function () {
      if (compareWrap) compareWrap.style.display = this.checked ? '' : 'none';
    });
  }

  // ── Book selector mutual exclusion ──────────────────────────────────────
  // When a book is chosen in one selector, remove it from the other
  // and restore the previously-excluded option if deselected.
  function _syncBookSelectors(changed, other) {
    var chosenVal = changed.value;

    // Collect all canonical book options from sel-book (source of truth)
    var allBooks = [];
    selBook.querySelectorAll('option').forEach(function(opt) {
      if (opt.value) allBooks.push({ value: opt.value, text: opt.text });
    });

    // Rebuild the 'other' selector: all books except the one just chosen
    var prevOtherVal = other.value;
    // Keep placeholder option
    while (other.options.length > 1) other.remove(1);
    allBooks.forEach(function(book) {
      if (book.value !== chosenVal) {
        var opt = document.createElement('option');
        opt.value = book.value;
        opt.textContent = book.text;
        other.appendChild(opt);
      }
    });
    // Restore previous selection if it's still available
    if (prevOtherVal && prevOtherVal !== chosenVal) {
      other.value = prevOtherVal;
    }
  }

  if (selBook && selBook2) {
    selBook.addEventListener('change', function() {
      _syncBookSelectors(selBook, selBook2);
    });
    selBook2.addEventListener('change', function() {
      _syncBookSelectors(selBook2, selBook);
    });
  }

  // ── Featured passage links ──────────────────────────────────────────────
  document.querySelectorAll('.featured-ref[data-book]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var b = this.getAttribute('data-book');
      if (b && selBook) selBook.value = b;
      analyze(b);
    });
  });

  // ── Analyze button ──────────────────────────────────────────────────────
  btnAnalyze.addEventListener('click', function () {
    var book = selBook ? selBook.value.trim() : '';
    if (!book) { showToast(window.t('err_select_book', 'Please select a book first.')); return; }
    analyze(book);
  });

  // ── Core analyze function ───────────────────────────────────────────────
  function analyze(book) {
    if (!book) return;
    _currentBook = book;
    _data1 = null;
    _data2 = null;

    if (_es) { _es.close(); _es = null; }
    clearInterval(_timerInt);
    _finalHandled = false;

    hide(emptyState);
    hide(radarArea);
    hide(tabsArea);
    hide(heading);
    show(loadState);
    setLoadingStep('Preparing…');

    var elapsed = 0;
    _timerInt = setInterval(function () {
      elapsed++;
      if (loadTimer) loadTimer.textContent = elapsed + 's';
    }, 1000);

    history.replaceState(null, '', '/scribal?book=' + encodeURIComponent(book));

    _es = new EventSource('/api/scribal/stream?book=' + encodeURIComponent(book) + '&lang=' + (window.bibcritLang || 'en'));

    _es.addEventListener('message', function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          setLoadingStep(msg.msg);
        } else if (msg.type === 'error') {
          _finalHandled = true;
          clearInterval(_timerInt);
          setLoadingStep('❌ ' + msg.msg);
          _es.close();
        } else if (msg.type === 'done') {
          _finalHandled = true;
          clearInterval(_timerInt);
          _es.close();
          _data1 = msg.data;

          // If compare mode is on, fetch second book
          var book2 = chkCompare && chkCompare.checked && selBook2 ? selBook2.value.trim() : '';
          if (book2 && book2 !== book) {
            setLoadingStep('Loading comparison book…');
            fetchSecond(book2, function (d2) {
              _data2 = d2;
              renderScribal(_data1, _data2);
            });
          } else {
            renderScribal(_data1, null);
          }
        }
      } catch (err) { /* ignore */ }
    });

    _es.onerror = function () {
      if (_finalHandled) return;   // already handled via 'error' or 'done' message
      clearInterval(_timerInt);
      setLoadingStep('❌ ' + window.t('err_connection_step', 'Connection error. Please try again.'));
      if (_es) _es.close();
    };
  }

  function fetchSecond(book2, cb) {
    var url = '/api/scribal/stream?book=' + encodeURIComponent(book2) + '&lang=' + (window.bibcritLang || 'en');
    var es2 = new EventSource(url);
    es2.addEventListener('message', function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'done') { es2.close(); cb(msg.data); }
        else if (msg.type === 'error') { es2.close(); cb(null); }
      } catch (_) { /* ignore */ }
    });
    es2.onerror = function () { es2.close(); cb(null); };
  }

  // ── Render ──────────────────────────────────────────────────────────────
  function renderScribal(data, data2) {
    _lastData = data;
    hide(loadState);

    // Heading
    show(heading);
    var bookLabel  = data.book || _currentBook;
    var bookLabel2 = data2 ? (data2.book || '') : null;
    var translatorName  = data.translator_name  || bookLabel;
    var translatorName2 = data2 ? (data2.translator_name || bookLabel2) : null;

    if (data2 && !data2.error) {
      heading.innerHTML =
        '<div class="scribal-heading-inner">' +
          '<span class="tradition-badge lxx-badge scribal-heading-badge">LXX</span>' +
          '<div class="scribal-heading-text">' +
            '<h1 class="scribal-heading-title">' +
              '<span style="color:' + SERIES_COLORS[0] + '">' + _esc(translatorName) + '</span>' +
              '<span style="color:var(--muted);font-weight:400;font-size:1.1rem;margin:0 10px">vs</span>' +
              '<span style="color:' + SERIES_COLORS[1] + '">' + _esc(translatorName2) + '</span>' +
            '</h1>' +
            '<span class="scribal-heading-sub">Scribal Tendency Comparison · ' + _esc(bookLabel) + ' &amp; ' + _esc(bookLabel2) + '</span>' +
          '</div>' +
        '</div>';
    } else {
      heading.innerHTML =
        '<div class="scribal-heading-inner">' +
          '<span class="tradition-badge lxx-badge scribal-heading-badge">LXX</span>' +
          '<div class="scribal-heading-text">' +
            '<h1 class="scribal-heading-title">' + _esc(translatorName) + '</h1>' +
            '<span class="scribal-heading-sub">Scribal Tendency Profile · ' + _esc(bookLabel) + '</span>' +
          '</div>' +
        '</div>';
    }

    // Radar
    show(radarArea);
    drawRadarAll(data, data2);

    // Overall assessment
    renderOverall(data, data2);

    // Dimension tabs — pass both datasets
    buildTabs(data, data2);

    // Export
    show(tabsArea);
    if (exportRow) show(exportRow);

    // Inject Scholar Rating, Copy, Download into export-row (once only)
    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'scribal',
        getReference: function() { return _currentBook; },
        getResultData: function() { return _lastData || {}; },
      });
    }

    // Wire BibTeX (once only; SBL already wired below)
    if (exportRow && !exportRow._exportWired) {
      exportRow._exportWired = true;
      var _btnBibtex = document.getElementById('btn-bibtex');
      if (_btnBibtex) {
        _btnBibtex.addEventListener('click', function() {
          fetch('/api/export/bibtex?tool=scribal&ref=' + encodeURIComponent(_currentBook))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              navigator.clipboard.writeText(d.bibtex || '').catch(function(){});
              showToast(window.t('toast_bibtex_copied_short', 'BibTeX copied!'));
            }).catch(function(){});
        });
      }
    }
  }

  // ── Radar chart (D3 v7) ─────────────────────────────────────────────────
  function drawRadarAll(data, data2) {
    if (!radarSvg || typeof d3 === 'undefined') return; // d3 guard

    var series = [{ data: data, color: SERIES_COLORS[0], label: data.book || _currentBook }];
    if (data2 && !data2.error) {
      series.push({ data: data2, color: SERIES_COLORS[1], label: data2.book || 'Comparison' });
    }

    // Draw into main chart
    _drawInto(radarSvg, series);

    // Mirror into modal SVG
    if (radarModalSvg) _drawInto(radarModalSvg, series);

    // Legend — only in comparison mode
    var legendEls = [radarLegend, radarModalLegend];
    legendEls.forEach(function (leg) {
      if (!leg) return;
      leg.innerHTML = '';
      if (series.length > 1) {
        leg.style.display = '';
        series.forEach(function (s) {
          var item = document.createElement('div');
          item.className = 'scribal-legend-item';
          item.innerHTML =
            '<span class="scribal-legend-swatch" style="background:' + s.color + '"></span>' +
            '<span>' + _esc(s.label) + '</span>';
          leg.appendChild(item);
        });
      } else {
        leg.style.display = 'none';
      }
    });
  }

  // Expand / close modal
  if (btnExpand) {
    btnExpand.addEventListener('click', function () {
      if (radarModal) radarModal.style.display = 'flex';
    });
  }
  if (radarModalClose) {
    radarModalClose.addEventListener('click', function () {
      if (radarModal) radarModal.style.display = 'none';
    });
  }
  if (radarModal) {
    radarModal.addEventListener('click', function (e) {
      if (e.target === radarModal) radarModal.style.display = 'none';
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && radarModal.style.display !== 'none') {
        radarModal.style.display = 'none';
      }
    });
  }

  function _drawInto(svgNode, series) {
    if (!svgNode || !series.length) return;

    // Clear previous
    while (svgNode.firstChild) svgNode.removeChild(svgNode.firstChild);

    var svgEl = d3.select(svgNode);
    var cx = 360, cy = 235, r = 155;
    var n = DIMS.length;
    var angleStep = (2 * Math.PI) / n;
    var levels = [0.2, 0.4, 0.6, 0.8, 1.0];

    // Helper: polar to cartesian
    function pt(val, i) {
      var angle = angleStep * i - Math.PI / 2;
      return {
        x: cx + r * val * Math.cos(angle),
        y: cy + r * val * Math.sin(angle),
      };
    }

    // Grid pentagons
    var gridG = svgEl.append('g').attr('class', 'radar-grid');
    levels.forEach(function (lv) {
      var pts = DIMS.map(function (_, i) { return pt(lv, i); });
      gridG.append('polygon')
        .attr('points', pts.map(function (p) { return p.x + ',' + p.y; }).join(' '))
        .attr('fill', 'none')
        .attr('stroke', 'var(--border, #ddd)')
        .attr('stroke-width', 0.75);
    });

    // Axis lines + labels
    var axisG = svgEl.append('g').attr('class', 'radar-axes');
    DIMS.forEach(function (dim, i) {
      var p = pt(1.0, i);
      axisG.append('line')
        .attr('x1', cx).attr('y1', cy)
        .attr('x2', p.x).attr('y2', p.y)
        .attr('stroke', 'var(--border, #ddd)')
        .attr('stroke-width', 0.75);

      var lp = pt(1.24, i);
      var anchor = lp.x < cx - 6 ? 'end' : lp.x > cx + 6 ? 'start' : 'middle';
      axisG.append('text')
        .attr('x', lp.x).attr('y', lp.y)
        .attr('text-anchor', anchor)
        .attr('dominant-baseline', 'middle')
        .attr('font-size', '12')
        .attr('font-weight', '500')
        .attr('fill', 'var(--fg, #333)')
        .text(dim.label);
    });

    // Data polygons (one per series, drawn back-to-front)
    series.forEach(function (s, si) {
      var profile = s.data.translator_profile || {};
      var vals = DIMS.map(function (dim) {
        return Math.max(0, Math.min(1, parseFloat(profile[dim.key]) || 0));
      });

      var pts = vals.map(function (v, i) { return pt(v, i); });
      var pointsStr = pts.map(function (p) { return p.x + ',' + p.y; }).join(' ');

      svgEl.append('polygon')
        .attr('points', pointsStr)
        .attr('fill', s.color)
        .attr('fill-opacity', series.length === 1 ? 0.2 : 0.15)
        .attr('stroke', s.color)
        .attr('stroke-width', 2)
        .attr('stroke-linejoin', 'round');

      // Vertex dots
      pts.forEach(function (p, i) {
        svgEl.append('circle')
          .attr('cx', p.x).attr('cy', p.y).attr('r', 4)
          .attr('fill', s.color)
          .attr('stroke', 'var(--bg, white)')
          .attr('stroke-width', 1.5)
          .style('cursor', 'pointer')
          .on('click', (function (dimIdx) {
            return function () { activateTab('dim-panel-' + dimIdx); };
          })(i));
      });
    });
  }

  // ── Overall assessment ──────────────────────────────────────────────────
  function renderOverall(data, data2) {
    if (!overallDiv) return;

    function _card(d, color) {
      var ass = d.bibcrit_assessment || {};
      return '<div class="scribal-overall-card" style="border-left-color:' + color + '">' +
        '<div class="scribal-overall-book-label" style="color:' + color + '">' + _esc(d.book || '') + '</div>' +
        (ass.title ? '<h3 class="scribal-overall-title">' + _esc(ass.title) + '</h3>' : '') +
        '<p class="div-analysis">' + _esc(d.overall_plain || '') + '</p>' +
        (ass.plain ? '<p class="div-meta" style="margin-top:8px">' + _esc(ass.plain) + '</p>' : '') +
        '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(d.model_version)) + '</p>' +
      '</div>';
    }

    if (data2 && !data2.error) {
      overallDiv.innerHTML =
        '<div class="scribal-overall-compare">' +
          _card(data,  SERIES_COLORS[0]) +
          _card(data2, SERIES_COLORS[1]) +
        '</div>';
    } else {
      var ass = data.bibcrit_assessment || {};
      overallDiv.innerHTML =
        '<div class="scribal-overall-card">' +
          (ass.title ? '<h3 class="scribal-overall-title">' + _esc(ass.title) + '</h3>' : '') +
          '<p class="div-analysis">' + _esc(data.overall_plain || '') + '</p>' +
          (ass.plain ? '<p class="div-meta" style="margin-top:8px">' + _esc(ass.plain) + '</p>' : '') +
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + '</p>' +
        '</div>';
    }
  }

  function _friendlyModel(modelId) {
    if (!modelId) return 'Claude';
    if (modelId.indexOf('opus') !== -1)    return 'Claude Opus';
    if (modelId.indexOf('sonnet') !== -1)  return 'Claude Sonnet';
    if (modelId.indexOf('haiku') !== -1)   return 'Claude Haiku';
    return 'Claude';
  }

  // ── Tabs ────────────────────────────────────────────────────────────────
  function buildTabs(data, data2) {
    tabsNav.innerHTML = '';
    tabsBody.innerHTML = '';

    var dims1 = (data.dimensions || []).slice().sort(function (a, b) { return (b.score || 0) - (a.score || 0); });

    // Build a lookup map for data2 dimensions by key
    var dims2Map = {};
    if (data2 && !data2.error) {
      (data2.dimensions || []).forEach(function (d) { dims2Map[d.dimension] = d; });
    }

    var comparing = data2 && !data2.error;

    dims1.forEach(function (dim, idx) {
      var panelId  = 'dim-panel-' + idx;
      var label    = _dimLabel(dim.dimension);
      var score1   = dim.score || 0;
      var pct1     = Math.round(score1 * 100);
      var confCls1 = score1 >= 0.75 ? 'badge-high' : score1 >= 0.45 ? 'badge-medium' : 'badge-low';

      // Tab button — show both scores when comparing
      var btn = document.createElement('button');
      btn.className = 'tab-btn' + (idx === 0 ? ' active' : '');
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-selected', idx === 0 ? 'true' : 'false');
      btn.setAttribute('data-panel', panelId);

      if (comparing) {
        var dim2   = dims2Map[dim.dimension] || {};
        var score2 = dim2.score || 0;
        var pct2   = Math.round(score2 * 100);
        btn.innerHTML = label +
          '<span class="conf-badge ' + confCls1 + '" style="margin-left:5px;background:' + SERIES_COLORS[0] + ';color:#fff">' + pct1 + '%</span>' +
          '<span class="conf-badge" style="margin-left:3px;background:' + SERIES_COLORS[1] + ';color:#fff">' + pct2 + '%</span>';
      } else {
        btn.innerHTML = label +
          '<span class="conf-badge ' + confCls1 + '" style="margin-left:5px">' + pct1 + '%</span>';
      }

      btn.addEventListener('click', function () { activateTab(panelId); });
      tabsNav.appendChild(btn);

      // Panel — side-by-side when comparing
      var panel = document.createElement('div');
      panel.id = panelId;
      panel.className = 'tab-panel' + (idx === 0 ? ' active' : '');
      panel.setAttribute('role', 'tabpanel');

      if (comparing) {
        var dim2 = dims2Map[dim.dimension] || {};
        panel.innerHTML =
          '<div class="scribal-compare-panels">' +
            '<div class="scribal-compare-col">' +
              '<div class="scribal-compare-col-label" style="color:' + SERIES_COLORS[0] + '">' + _esc(data.book || '') + '</div>' +
              renderDimPanel(dim) +
            '</div>' +
            '<div class="scribal-compare-col">' +
              '<div class="scribal-compare-col-label" style="color:' + SERIES_COLORS[1] + '">' + _esc(data2.book || '') + '</div>' +
              renderDimPanel(dim2.dimension ? dim2 : { dimension: dim.dimension, score: 0, summary_plain: 'No data for this dimension.', examples: [] }) +
            '</div>' +
          '</div>';
      } else {
        panel.innerHTML = renderDimPanel(dim);
      }

      tabsBody.appendChild(panel);
    });
  }

  function renderDimPanel(dim) {
    var score  = (dim.score || 0);
    var pct    = Math.round(score * 100);
    var confCls = score >= 0.75 ? 'badge-high' : score >= 0.45 ? 'badge-medium' : 'badge-low';

    var html =
      '<div class="bt-group-card">' +
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">' +
          '<span class="conf-badge ' + confCls + '" style="font-size:13px;padding:3px 10px">' + pct + '%</span>' +
          '<strong style="font-size:16px">' + _dimLabel(dim.dimension) + '</strong>' +
        '</div>' +
        '<p class="hyp-card-plain">' + _esc(dim.summary_plain || '') + '</p>' +
        (dim.summary ? '<p class="hyp-card-reasoning">' + _esc(dim.summary) + '</p>' : '');

    // Examples table
    var examples = dim.examples || [];
    if (examples.length) {
      html += '<table class="dim-examples-table"><thead><tr>' +
        '<th>Reference</th><th>MT</th><th>LXX</th><th>Note</th>' +
        '</tr></thead><tbody>';
      examples.forEach(function (ex) {
        html += '<tr>' +
          '<td class="dim-ex-ref">' + _esc(ex.reference || '') + '</td>' +
          '<td class="dim-ex-mt">' + _esc(ex.mt_text || '') + '</td>' +
          '<td class="dim-ex-lxx">' + _esc(ex.lxx_text || '') + '</td>' +
          '<td class="dim-ex-note">' + _esc(ex.note || '') + '</td>' +
          '</tr>';
      });
      html += '</tbody></table>';
    }

    html += '</div>';
    return html;
  }

  function activateTab(panelId) {
    tabsNav.querySelectorAll('.tab-btn').forEach(function (b) {
      var active = b.getAttribute('data-panel') === panelId;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    tabsBody.querySelectorAll('.tab-panel').forEach(function (p) {
      p.classList.toggle('active', p.id === panelId);
    });
  }

  // ── SBL Export ──────────────────────────────────────────────────────────
  if (btnSbl) {
    btnSbl.addEventListener('click', function () {
      if (!_currentBook) return;
      fetch('/api/scribal/export/sbl?book=' + encodeURIComponent(_currentBook))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var text = (data.footnotes || []).join('\n\n');
          if (!text) { showToast('No footnotes generated.'); return; }
          navigator.clipboard.writeText(text).then(function () {
            showToast(window.t('toast_sbl_copied_short', 'SBL footnotes copied!'));
          });
        })
        .catch(function () { showToast('Export failed.'); });
    });
  }

  // ── Helpers ─────────────────────────────────────────────────────────────
  function setLoadingStep(msg) {
    if (loadStep) loadStep.textContent = msg;
  }

  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function showToast(msg, ms) {
    if (!toast) return;
    toast.textContent = msg;
    show(toast);
    setTimeout(function () { hide(toast); }, ms || 2500);
  }

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _dimLabel(key) {
    var labels = {
      literalness:                'Literalness',
      anthropomorphism_reduction: 'Anthropomorphism Reduction',
      messianic_heightening:      'Messianic Heightening',
      harmonization:              'Harmonization',
      paraphrase_rate:            'Paraphrase Rate',
    };
    return labels[key] || (key || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  // ── Public API ───────────────────────────────────────────────────────────
  window.scribal = { analyze: analyze };

})();
