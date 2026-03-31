/* BibCrit — Numerical Discrepancy Modeler */

(function () {
  'use strict';

  var selPassage  = document.getElementById('sel-passage');
  var refInput    = document.getElementById('ref-input');
  var btnAnalyze  = document.getElementById('btn-analyze');
  var infoBanner  = document.getElementById('numerical-info-banner');
  var infoClose   = document.getElementById('numerical-info-close');
  var emptyState  = document.getElementById('empty-state');
  var loadState   = document.getElementById('loading-state');
  var loadStep    = document.getElementById('loading-step');
  var loadTimer   = document.getElementById('loading-timer');
  var heading     = document.getElementById('passage-heading');
  var results     = document.getElementById('numerical-results');
  var tableWrap   = document.getElementById('num-table-wrap');
  var timelineSvg = document.getElementById('num-timeline');
  var systematic  = document.getElementById('num-systematic');
  var tabsArea    = document.getElementById('tabs-area');
  var tabsNav     = document.getElementById('tabs-nav');
  var tabsBody    = document.getElementById('tabs-body');
  var toast       = document.getElementById('toast');

  if (!btnAnalyze) return;

  // ── Info banner dismiss ─────────────────────────────────────────────────
  var _BANNER_VER = 'numerical-info-v1';
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
  var _currentRef   = '';
  var _finalHandled = false;  // true once 'done' or 'error' SSE message received
  var _lastData     = null;

  var TRAD_COLORS = {
    mt:  'var(--mt-color, #c0892a)',
    lxx: 'var(--lxx-color, #3a6bc4)',
    sp:  'var(--sp-color, #2c7c5f)',
  };

  // ── Passage select ──────────────────────────────────────────────────────
  if (selPassage) {
    selPassage.addEventListener('change', function () {
      var ref = this.value;
      if (ref && refInput) refInput.value = ref;
    });
  }

  // ── Featured passage links ──────────────────────────────────────────────
  document.querySelectorAll('.featured-ref[data-ref]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.getAttribute('data-ref');
      if (ref && refInput) refInput.value = ref;
      if (ref && selPassage) selPassage.value = ref;
      analyze(ref);
    });
  });

  // ── Suggestion chips ────────────────────────────────────────────────────
  var suggestionsEl = document.getElementById('num-suggestions');

  document.querySelectorAll('.num-sug-chip[data-ref]').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var ref = this.getAttribute('data-ref');
      if (!ref) return;
      if (refInput)    refInput.value    = ref;
      if (selPassage)  selPassage.value  = ref;
      analyze(ref);
    });
  });

  // ── Analyze button ──────────────────────────────────────────────────────
  btnAnalyze.addEventListener('click', function () {
    var ref = (refInput ? refInput.value.trim() : '') ||
              (selPassage ? selPassage.value.trim() : '');
    if (!ref) { showToast(window.t('err_select_passage', 'Please select or enter a passage.')); return; }
    analyze(ref);
  });

  // Enter key on text input
  if (refInput) {
    refInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') btnAnalyze.click();
    });
    // Restore suggestions + empty state when input is cleared
    refInput.addEventListener('input', function () {
      if (this.value.trim() === '') {
        // Only restore if no results are currently shown
        var resultsVisible = results && results.style.display !== 'none';
        var loadVisible    = loadState && loadState.style.display !== 'none';
        if (!resultsVisible && !loadVisible) {
          show(suggestionsEl);
          show(emptyState);
        }
      }
    });
  }

  // ── Core analyze ────────────────────────────────────────────────────────
  function analyze(ref) {
    if (!ref) return;
    _currentRef = ref;

    if (_es) { _es.close(); _es = null; }
    clearInterval(_timer);
    _finalHandled = false;

    hide(suggestionsEl);
    hide(emptyState);
    hide(results);
    hide(tabsArea);
    hide(heading);
    show(loadState);
    setLoadingStep('Preparing…');

    var elapsed = 0;
    _timer = setInterval(function () {
      elapsed++;
      if (loadTimer) loadTimer.textContent = elapsed + 's';
    }, 1000);

    history.replaceState(null, '', '/numerical?ref=' + encodeURIComponent(ref));

    _es = new EventSource('/api/numerical/stream?ref=' + encodeURIComponent(ref) + '&lang=' + (window.bibcritLang || 'en'));

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
          renderNumerical(msg.data);
        }
      } catch (_) { /* ignore */ }
    });

    _es.onerror = function () {
      if (_finalHandled) return;   // already handled via 'error' or 'done' message
      clearInterval(_timer);
      setLoadingStep('❌ ' + window.t('err_connection_step', 'Connection error. Please try again.'));
      if (_es) _es.close();
    };
  }

  // ── Render ───────────────────────────────────────────────────────────────
  function renderNumerical(data) {
    _lastData = data;
    hide(loadState);

    show(heading);
    var _hRef  = _esc(data.reference || _currentRef);
    var _hMeta = data.subject ? ' <span class="ph-meta">— ' + _esc(data.subject) + '</span>' : '';
    heading.innerHTML = '<span class="ph-ref">' + _hRef + '</span>' + _hMeta;

    renderTable(data.figures || []);
    renderTimeline(data.figures || []);
    renderSystematic(data.systematic_analysis || {});
    buildTheoryTabs(data.theories || [], data);

    show(results);
    show(tabsArea);

    var exportRow = document.getElementById('export-row');
    if (exportRow) show(exportRow);

    // Inject Scholar Rating, Copy, Download into export-row (once only)
    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'numerical',
        getReference: function() { return _currentRef; },
        getResultData: function() { return _lastData || {}; },
        getSvgEl: function() { return document.getElementById('num-timeline'); },
      });
    }

    // Wire SBL/BibTeX (once only)
    if (exportRow && !exportRow._exportWired) {
      exportRow._exportWired = true;
      var _btnSbl    = document.getElementById('btn-sbl');
      var _btnBibtex = document.getElementById('btn-bibtex');

      if (_btnSbl) {
        _btnSbl.addEventListener('click', function() {
          fetch('/api/export/sbl?tool=numerical&ref=' + encodeURIComponent(_currentRef))
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
          fetch('/api/export/bibtex?tool=numerical&ref=' + encodeURIComponent(_currentRef))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              navigator.clipboard.writeText(d.bibtex || '').catch(function(){});
              showToast(window.t('toast_bibtex_copied_short', 'BibTeX copied!'));
            }).catch(function(){});
        });
      }
    }
  }

  // ── Table ─────────────────────────────────────────────────────────────
  function renderTable(figures) {
    if (!tableWrap) return;
    var hasSP = figures.some(function (f) {
      return f.sp_value !== null && f.sp_value !== undefined && f.sp_value !== 0;
    });

    var html = '<table class="num-table"><thead><tr>' +
      '<th>Name</th>' +
      '<th><span style="color:var(--mt-color)">MT</span></th>' +
      '<th><span style="color:var(--lxx-color)">LXX</span></th>' +
      (hasSP ? '<th><span style="color:var(--sp-color,#2c7c5f)">SP</span></th>' : '') +
      '<th>Divergence</th></tr></thead><tbody>';

    figures.forEach(function (f) {
      var dtype    = f.divergence_type || 'none';
      var rowCls   = dtype !== 'none' && dtype !== 'minor' ? ' class="num-row-divergent"' : '';
      var diffHtml = dtype === 'none'
        ? '<span class="num-diff-badge num-diff-none">none</span>'
        : '<span class="num-diff-badge num-diff-significant">' + _esc(dtype) + '</span>';

      html += '<tr' + rowCls + '>' +
        '<td><strong>' + _esc(f.name || '') + '</strong>' +
          (f.note ? '<br><small style="color:var(--muted);font-size:11px">' + _esc(f.note) + '</small>' : '') +
        '</td>' +
        '<td><span class="num-value mt">' + _numVal(f.mt_value) + '</span></td>' +
        '<td><span class="num-value lxx">' + _numVal(f.lxx_value) + '</span></td>' +
        (hasSP ? '<td><span class="num-value sp">' + _numVal(f.sp_value) + '</span></td>' : '') +
        '<td>' + diffHtml + '</td>' +
        '</tr>';
    });

    html += '</tbody></table>';
    tableWrap.innerHTML = html;
  }

  function _numVal(v) {
    if (v === null || v === undefined) return '–';
    return String(v);
  }

  // ── Timeline SVG ─────────────────────────────────────────────────────
  var NS = 'http://www.w3.org/2000/svg';
  var TRAD = [
    { key: 'mt',  color: '#c0892a', label: 'MT'  },
    { key: 'lxx', color: '#3a6bc4', label: 'LXX' },
    { key: 'sp',  color: '#2c7c5f', label: 'SP'  },
  ];

  function _svgEl(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(e);
    return e;
  }
  function _svgTxt(str, attrs, parent) {
    var e = _svgEl('text', attrs, parent);
    e.textContent = str;
    return e;
  }

  // Group lifespan figures { ageBirth, remaining, total } by patriarch name
  function _groupPatriarchs(figures) {
    var groups = {}, order = [];
    figures.forEach(function (f) {
      var nm = (f.name || '').trim();
      var patriarch = nm.replace(/\s*\(.*$/, '').trim();
      if (!patriarch) return;
      var type = /age at/i.test(nm)    ? 'ageBirth'  :
                 /remaining/i.test(nm) ? 'remaining' :
                 /total/i.test(nm)     ? 'total'     : null;
      if (!type) return;
      if (!groups[patriarch]) { groups[patriarch] = {}; order.push(patriarch); }
      groups[patriarch][type] = f;
    });
    return { groups: groups, order: order };
  }

  function renderTimeline(figures) {
    if (!timelineSvg) return;
    timelineSvg.innerHTML = '';

    // Remove any stale toggle from a previous render
    var prevToggle = timelineSvg.parentElement &&
                     timelineSvg.parentElement.querySelector('.num-timeline-toggle');
    if (prevToggle) prevToggle.remove();

    var plotFigs = figures.filter(function (f) {
      return f.mt_value || f.lxx_value || f.sp_value;
    });
    if (!plotFigs.length) { timelineSvg.setAttribute('height', '0'); return; }

    // Detect lifespan pattern (Genesis 5/11 style)
    var isLifespan = plotFigs.some(function (f) {
      return /age at|remaining years|total lifespan/i.test(f.name || '');
    });

    if (isLifespan) {
      _renderGroupedChart(plotFigs);
    } else {
      _renderSimpleChart(plotFigs);
    }
  }

  function _renderGroupedChart(figures) {
    var parent = timelineSvg.parentElement;
    var grouped = _groupPatriarchs(figures);
    var order   = grouped.order;
    var groups  = grouped.groups;

    // ── View toggle ─────────────────────────────────────────────────────────
    var _mode = localStorage.getItem('num-timeline-mode') || 'stacked';
    var toggleDiv = document.createElement('div');
    toggleDiv.className = 'num-timeline-toggle';
    toggleDiv.innerHTML =
      '<span class="num-tl-label">View:</span>' +
      '<button class="num-tl-btn' + (_mode === 'stacked' ? ' active' : '') + '" data-mode="stacked">Age + Remaining</button>' +
      '<button class="num-tl-btn' + (_mode === 'total' ? ' active' : '') + '" data-mode="total">Total only</button>';
    parent.insertBefore(toggleDiv, timelineSvg);

    function draw(mode) {
      timelineSvg.innerHTML = '';

      // Determine which traditions have any data in this dataset
      var activeTrad = TRAD.filter(function (t) {
        return order.some(function (p) {
          var g = groups[p];
          var f = g.total || g.ageBirth;
          return f && f[t.key + '_value'];
        });
      });

      // Max value (for scale)
      var maxVal = 0;
      order.forEach(function (p) {
        var g = groups[p];
        var f = g.total || g.ageBirth;
        if (!f) return;
        activeTrad.forEach(function (t) {
          maxVal = Math.max(maxVal, f[t.key + '_value'] || 0);
        });
      });
      if (!maxVal) maxVal = 1000;

      var viewW  = 740;
      var labelW = 130;
      var numW   = 44;
      var areaW  = viewW - labelW - numW;
      var barH   = 12;
      var barGap = 3;
      var groupH = activeTrad.length * (barH + barGap) + 12;
      var legendH = 30;
      var totalH  = legendH + order.length * groupH + 6;

      timelineSvg.setAttribute('viewBox', '0 0 ' + viewW + ' ' + totalH);
      timelineSvg.setAttribute('width', '100%');
      timelineSvg.setAttribute('height', totalH);

      // ── Legend ────────────────────────────────────────────────────────────
      var lx = labelW;
      activeTrad.forEach(function (t) {
        _svgEl('rect', { x: lx, y: 8, width: 12, height: 9, fill: t.color, rx: 2 }, timelineSvg);
        _svgTxt(t.label, { x: lx + 16, y: 17, 'font-size': '11', fill: 'var(--muted,#888)', 'font-family': 'sans-serif' }, timelineSvg);
        lx += 48;
      });
      if (mode === 'stacked') {
        _svgEl('rect', { x: lx + 6, y: 8, width: 20, height: 9, fill: '#888', 'fill-opacity': '0.22', rx: 2 }, timelineSvg);
        _svgTxt('darker = age-at-birth · lighter = remaining', { x: lx + 30, y: 17, 'font-size': '10', fill: 'var(--muted,#888)', 'font-family': 'sans-serif' }, timelineSvg);
      }

      // ── Rows ──────────────────────────────────────────────────────────────
      order.forEach(function (patriarch, pi) {
        var g  = groups[patriarch];
        var y0 = legendH + pi * groupH;

        // Zebra stripe
        if (pi % 2 === 0) {
          _svgEl('rect', { x: 0, y: y0 - 1, width: viewW, height: groupH - 1,
            fill: 'currentColor', 'fill-opacity': '0.03' }, timelineSvg);
        }

        // Patriarch name (vertically centred across the tradition bars)
        var midY = y0 + (activeTrad.length * (barH + barGap) - barGap) / 2 + 4;
        _svgTxt(patriarch, { x: labelW - 8, y: midY, 'text-anchor': 'end',
          'font-size': '12', 'font-weight': '500',
          fill: 'var(--fg,#222)', 'font-family': 'sans-serif' }, timelineSvg);

        activeTrad.forEach(function (t, ti) {
          var by         = y0 + ti * (barH + barGap);
          var birthVal   = (g.ageBirth   && g.ageBirth[t.key   + '_value'])   || 0;
          var remainVal  = (g.remaining  && g.remaining[t.key  + '_value'])   || 0;
          var totalVal   = (g.total      && g.total[t.key      + '_value'])   || (birthVal + remainVal);
          if (!totalVal && !birthVal) return;

          var scale = areaW / maxVal;

          if (mode === 'stacked' && birthVal && remainVal) {
            var bw1 = Math.max(2, birthVal  * scale);
            var bw2 = Math.max(2, remainVal * scale);
            // Birth segment (solid)
            _svgEl('rect', { x: labelW, y: by, width: bw1, height: barH,
              fill: t.color, 'fill-opacity': '0.9', rx: 2 }, timelineSvg);
            // Remaining segment (pale)
            _svgEl('rect', { x: labelW + bw1, y: by, width: bw2, height: barH,
              fill: t.color, 'fill-opacity': '0.3', rx: 2 }, timelineSvg);
            // Divider tick
            _svgEl('line', { x1: labelW + bw1, y1: by, x2: labelW + bw1, y2: by + barH,
              stroke: 'white', 'stroke-width': '1', 'stroke-opacity': '0.7' }, timelineSvg);
            // Total label
            _svgTxt(String(totalVal || birthVal + remainVal), {
              x: labelW + bw1 + bw2 + 4, y: by + barH - 1,
              'font-size': '10', fill: 'var(--muted,#888)', 'font-family': 'sans-serif'
            }, timelineSvg);
          } else {
            var useVal = totalVal || birthVal;
            var bw     = Math.max(2, useVal * scale);
            _svgEl('rect', { x: labelW, y: by, width: bw, height: barH,
              fill: t.color, 'fill-opacity': '0.82', rx: 2 }, timelineSvg);
            _svgTxt(String(useVal), {
              x: labelW + bw + 4, y: by + barH - 1,
              'font-size': '10', fill: 'var(--muted,#888)', 'font-family': 'sans-serif'
            }, timelineSvg);
          }
        });
      });
    }

    draw(_mode);

    toggleDiv.querySelectorAll('.num-tl-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        _mode = this.getAttribute('data-mode');
        localStorage.setItem('num-timeline-mode', _mode);
        toggleDiv.querySelectorAll('.num-tl-btn').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        draw(_mode);
      });
    });
  }

  function _renderSimpleChart(figures) {
    var allVals = [];
    figures.forEach(function (f) {
      if (f.mt_value)  allVals.push(f.mt_value);
      if (f.lxx_value) allVals.push(f.lxx_value);
      if (f.sp_value)  allVals.push(f.sp_value);
    });
    var maxVal   = Math.max.apply(null, allVals) || 1;
    var viewW    = 740;
    var labelW   = 150;
    var areaW    = viewW - labelW - 44;
    var barH     = 10;
    var rowH     = 42;
    var legendH  = 30;
    var totalH   = legendH + figures.length * rowH + 10;

    timelineSvg.setAttribute('viewBox', '0 0 ' + viewW + ' ' + totalH);
    timelineSvg.setAttribute('width', '100%');
    timelineSvg.setAttribute('height', totalH);

    var lx = labelW;
    TRAD.forEach(function (t) {
      _svgEl('rect', { x: lx, y: 8, width: 12, height: 9, fill: t.color, rx: 2 }, timelineSvg);
      _svgTxt(t.label, { x: lx + 16, y: 17, 'font-size': '11', fill: 'var(--muted,#888)', 'font-family': 'sans-serif' }, timelineSvg);
      lx += 50;
    });

    figures.forEach(function (f, ri) {
      var y0 = legendH + ri * rowH;
      _svgTxt(f.name || '', { x: labelW - 6, y: y0 + 18, 'text-anchor': 'end',
        'font-size': '11', fill: 'var(--fg,#222)', 'font-family': 'sans-serif' }, timelineSvg);

      TRAD.forEach(function (t, ti) {
        var val = f[t.key + '_value'];
        if (!val) return;
        var bw = Math.max(2, (val / maxVal) * areaW);
        var by = y0 + ti * (barH + 3);
        _svgEl('rect', { x: labelW, y: by, width: bw, height: barH,
          fill: t.color, 'fill-opacity': '0.8', rx: 2 }, timelineSvg);
        _svgTxt(String(val), { x: labelW + bw + 4, y: by + barH - 1,
          'font-size': '10', fill: 'var(--muted,#888)', 'font-family': 'sans-serif' }, timelineSvg);
      });
    });
  }

  // ── Systematic analysis ───────────────────────────────────────────────
  function renderSystematic(sa) {
    if (!systematic) return;
    var badge = sa.is_systematic
      ? '<span class="conf-badge badge-high" style="margin-right:8px">Systematic</span>'
      : '<span class="conf-badge badge-low" style="margin-right:8px">Not systematic</span>';

    systematic.innerHTML =
      '<div class="num-systematic-card">' +
        badge +
        '<p style="margin:8px 0 0;font-size:15px;line-height:1.75">' +
          _esc(sa.pattern_plain || sa.pattern || '') +
        '</p>' +
        (sa.pattern && sa.pattern !== sa.pattern_plain
          ? '<p style="font-style:italic;color:var(--muted);font-size:13px;margin-top:6px">' + _esc(sa.pattern) + '</p>'
          : '') +
      '</div>';
  }

  // ── Theory tabs ───────────────────────────────────────────────────────
  function buildTheoryTabs(theories, data) {
    tabsNav.innerHTML = '';
    tabsBody.innerHTML = '';

    // Sort by score descending
    theories = theories.slice().sort(function (a, b) { return (b.score || 0) - (a.score || 0); });

    theories.forEach(function (theory, idx) {
      var panelId  = 'theory-panel-' + idx;
      var score    = theory.score || 0;
      var pct      = Math.round(score * 100);
      var confCls  = score >= 0.75 ? 'badge-high' : score >= 0.45 ? 'badge-medium' : 'badge-low';

      // Tab button
      var btn = document.createElement('button');
      btn.className = 'tab-btn' + (idx === 0 ? ' active' : '');
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-selected', idx === 0 ? 'true' : 'false');
      btn.setAttribute('data-panel', panelId);
      btn.innerHTML = _esc(theory.name || theory.slug || '') +
        '<span class="conf-badge ' + confCls + '" style="margin-left:5px">' + pct + '%</span>';
      btn.addEventListener('click', function () { activateTab(panelId); });
      tabsNav.appendChild(btn);

      // Panel
      var panel = document.createElement('div');
      panel.id = panelId;
      panel.className = 'tab-panel' + (idx === 0 ? ' active' : '');
      panel.innerHTML = renderTheoryPanel(theory, data);
      tabsBody.appendChild(panel);
    });

    // BibCrit Assessment tab
    if (data.bibcrit_assessment && (data.bibcrit_assessment.title || data.bibcrit_assessment.plain)) {
      var assId  = 'theory-panel-assessment';
      var assBtn = document.createElement('button');
      assBtn.className = 'tab-btn';
      assBtn.setAttribute('role', 'tab');
      assBtn.setAttribute('aria-selected', 'false');
      assBtn.setAttribute('data-panel', assId);
      assBtn.innerHTML = '<span class="tradition-badge analysis-badge" style="font-size:10px">BibCrit Assessment</span>';
      assBtn.addEventListener('click', function () { activateTab(assId); });
      tabsNav.appendChild(assBtn);

      var assPanel = document.createElement('div');
      assPanel.id = assId;
      assPanel.className = 'tab-panel';
      assPanel.innerHTML = renderAssessmentPanel(data);
      tabsBody.appendChild(assPanel);
    }
  }

  function renderTheoryPanel(theory, data) {
    var score   = theory.score || 0;
    var pct     = Math.round(score * 100);
    var confCls = score >= 0.75 ? 'badge-high' : score >= 0.45 ? 'badge-medium' : 'badge-low';

    var html =
      '<div class="bt-group-card">' +
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">' +
          '<span class="conf-badge ' + confCls + '" style="font-size:13px;padding:3px 10px">' + pct + '%</span>' +
          '<strong style="font-size:15px">' + _esc(theory.name || '') + '</strong>' +
        '</div>' +

        // Confidence bar
        '<div class="num-conf-bar-wrap">' +
          '<div class="num-conf-track">' +
            '<div class="num-conf-bar" style="width:' + pct + '%"></div>' +
          '</div>' +
          '<div class="num-conf-label">Confidence: ' + pct + '%</div>' +
        '</div>' +

        '<p class="div-analysis">' + _esc(theory.summary_plain || '') + '</p>' +
        (theory.summary ? '<p class="div-meta" style="font-style:italic;margin-top:8px">' + _esc(theory.summary) + '</p>' : '');

    // Evidence
    var ev = theory.supporting_evidence || [];
    if (ev.length) {
      html += '<div style="margin-top:14px"><strong style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">Supporting Evidence</strong><ul style="margin:6px 0 0 16px;padding:0">';
      ev.forEach(function (e) { html += '<li style="margin-bottom:5px;line-height:1.6;font-size:14px">' + _esc(e) + '</li>'; });
      html += '</ul></div>';
    }

    // Weaknesses
    var wk = theory.weaknesses || [];
    if (wk.length) {
      html += '<div style="margin-top:10px"><strong style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">Weaknesses</strong><ul style="margin:6px 0 0 16px;padding:0">';
      wk.forEach(function (w) { html += '<li style="margin-bottom:5px;line-height:1.6;font-size:14px">' + _esc(w) + '</li>'; });
      html += '</ul></div>';
    }

    html += '</div>';
    return html;
  }

  function renderAssessmentPanel(data) {
    var ass = data.bibcrit_assessment || {};
    var conf = ass.confidence || 0;
    var pct  = Math.round(conf * 100);
    var confCls = conf >= 0.75 ? 'badge-high' : conf >= 0.45 ? 'badge-medium' : 'badge-low';

    return '<div class="bt-group-card">' +
      (ass.title ? '<h3 style="margin:0 0 12px;font-size:16px">' + _esc(ass.title) + '</h3>' : '') +
      '<p class="div-analysis">' + _esc(ass.plain || '') + '</p>' +
      (ass.reasoning ? '<p class="div-meta" style="font-style:italic;margin-top:8px">' + _esc(ass.reasoning) + '</p>' : '') +
      (pct ? '<p style="margin-top:10px"><span class="conf-badge ' + confCls + '">Confidence: ' + pct + '%</span></p>' : '') +
      '<p class="div-meta" style="margin-top:8px">' + _esc(data.overall_plain || '') + '</p>' +
      '</div>';
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

  // ── Public API ───────────────────────────────────────────────────────────
  window.numerical = { analyze: analyze };

})();
