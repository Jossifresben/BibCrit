/* BibCrit — Theological Revision Detector */

(function () {
  'use strict';

  var refInput   = document.getElementById('ref-input');
  var btnAnalyze = document.getElementById('btn-analyze');
  var infoBanner = document.getElementById('theological-info-banner');
  var infoClose  = document.getElementById('theological-info-close');
  var emptyState = document.getElementById('empty-state');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var results    = document.getElementById('theological-results');
  var summarySection = document.getElementById('summary-section');
  var summaryBody    = document.getElementById('summary-body');
  var filterChips    = document.getElementById('filter-chips');
  var revisionList   = document.getElementById('revision-list');
  var overallSection = document.getElementById('overall-section');
  var overallBody    = document.getElementById('overall-body');
  var bibSec     = document.getElementById('bibcrit-assessment');
  var bibBody    = document.getElementById('bibcrit-body');
  var exportRow  = document.getElementById('export-row');
  var btnShare   = document.getElementById('btn-share');
  var suggestions    = document.getElementById('theo-suggestions');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  // ── Info banner dismiss ─────────────────────────────────────────────────
  var _BANNER_VER = 'theological-info-v1';
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
  var _finalHandled = false;
  var _activeFilter = '';
  var _lastData     = null;

  // ── Suggestion chips ────────────────────────────────────────────────────
  document.querySelectorAll('.num-sug-chip[data-ref]').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var ref = this.getAttribute('data-ref');
      if (!ref) return;
      if (refInput) refInput.value = ref;
      analyze(ref);
    });
  });

  // ── Featured passage links ──────────────────────────────────────────────
  document.querySelectorAll('.featured-ref[data-ref]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.getAttribute('data-ref');
      if (ref && refInput) refInput.value = ref;
      analyze(ref);
    });
  });

  // ── Analyze button ──────────────────────────────────────────────────────
  btnAnalyze.addEventListener('click', function () {
    var ref = refInput ? refInput.value.trim() : '';
    if (!ref) { showToast(window.t('err_enter_passage', 'Please enter a book name or passage.')); return; }
    analyze(ref);
  });

  if (refInput) {
    refInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') btnAnalyze.click();
    });
    refInput.addEventListener('input', function () {
      if (this.value.trim() === '') {
        var resVisible  = results  && results.style.display  !== 'none';
        var loadVisible = loadState && loadState.style.display !== 'none';
        if (!resVisible && !loadVisible) {
          show(suggestions);
          show(emptyState);
        }
      }
    });
  }

  // ── Core analyze ────────────────────────────────────────────────────────
  function analyze(ref) {
    if (!ref) return;
    _currentRef  = ref;
    _activeFilter = '';

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

    history.replaceState(null, '', '/theological?ref=' + encodeURIComponent(ref));

    _es = new EventSource('/api/theological/stream?ref=' + encodeURIComponent(ref) + '&lang=' + (window.bibcritLang || 'en'));

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
          renderRevisions(msg.data);
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
  function renderRevisions(data) {
    _lastData = data;
    hide(loadState);

    show(heading);
    var _hRef  = _esc(data.scope || _currentRef);
    var _hMeta = data.scope_type ? ' <span class="ph-meta">— ' + _esc(data.scope_type.charAt(0).toUpperCase() + data.scope_type.slice(1)) + '</span>' : '';
    heading.innerHTML = '<span class="ph-ref">' + _hRef + '</span>' + _hMeta;

    // Summary
    var summ = data.summary_plain || data.summary || '';
    if (summ && summarySection && summaryBody) {
      summaryBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(summ) + '</p>' +
          (data.summary && data.summary !== summ
            ? '<p class="div-meta" style="margin-top:8px;font-style:italic">' + _esc(data.summary) + '</p>'
            : '') +
          (data.dominant_strategy
            ? '<p style="margin-top:8px;font-size:0.875rem;color:var(--fg)"><strong>Dominant strategy:</strong> ' + _esc(data.dominant_strategy) + '</p>'
            : '') +
        '</div>';
      show(summarySection);
    }

    // Revision cards — sorted by confidence desc
    var revisions = (data.revisions || []).slice().sort(function (a, b) {
      return (b.confidence || 0) - (a.confidence || 0);
    });

    // Build filter chips from unique types
    var types = [];
    revisions.forEach(function (r) {
      var t = r.revision_type || '';
      if (t && types.indexOf(t) === -1) types.push(t);
    });

    if (filterChips && types.length > 1) {
      filterChips.innerHTML = '';
      var allBtn = document.createElement('button');
      allBtn.className = 'theo-filter-chip active';
      allBtn.textContent = 'All';
      allBtn.addEventListener('click', function () {
        _activeFilter = '';
        _updateFilterChips(filterChips, '');
        _applyFilter(revisions);
      });
      filterChips.appendChild(allBtn);

      types.forEach(function (t) {
        var btn = document.createElement('button');
        btn.className = 'theo-filter-chip';
        btn.textContent = _revisionTypeLabel(t);
        btn.setAttribute('data-type', t);
        btn.addEventListener('click', function () {
          _activeFilter = t;
          _updateFilterChips(filterChips, t);
          _applyFilter(revisions);
        });
        filterChips.appendChild(btn);
      });
      show(filterChips);
    }

    if (revisionList) {
      revisionList.innerHTML = '';
      revisions.forEach(function (rev) {
        revisionList.appendChild(_buildRevisionCard(rev));
      });
    }

    if (!revisions.length && revisionList) {
      revisionList.innerHTML = '<p style="padding:1rem;color:var(--muted);text-align:center">No theologically motivated revisions identified.</p>';
    }

    // Overall assessment
    var overall = data.overall_plain || data.overall_assessment || '';
    if (overall && overallSection && overallBody) {
      overallBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(overall) + '</p>' +
          (data.overall_assessment && data.overall_assessment !== overall
            ? '<p class="div-meta" style="margin-top:8px;font-style:italic">' + _esc(data.overall_assessment) + '</p>'
            : '') +
        '</div>';
      show(overallSection);
    }

    // BibCrit assessment
    renderAssessment(data);

    show(results);
    if (exportRow) show(exportRow);

    // Inject Scholar Rating, Copy, Download into export-row (once only)
    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'theological',
        getReference: function() { return _currentRef; },
        getResultData: function() { return _lastData || {}; },
      });
    }

    // Wire SBL/BibTeX (once only)
    if (exportRow && !exportRow._exportWired) {
      exportRow._exportWired = true;
      var _btnSbl    = document.getElementById('btn-sbl');
      var _btnBibtex = document.getElementById('btn-bibtex');

      if (_btnSbl) {
        _btnSbl.addEventListener('click', function() {
          fetch('/api/export/sbl?tool=theological&ref=' + encodeURIComponent(_currentRef))
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
          fetch('/api/export/bibtex?tool=theological&ref=' + encodeURIComponent(_currentRef))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              navigator.clipboard.writeText(d.bibtex || '').catch(function(){});
              showToast(window.t('toast_bibtex_copied_short', 'BibTeX copied!'));
            }).catch(function(){});
        });
      }
    }
  }

  function _updateFilterChips(container, activeType) {
    container.querySelectorAll('.theo-filter-chip').forEach(function (btn) {
      var t = btn.getAttribute('data-type') || '';
      var isAll = !t;
      btn.classList.toggle('active', activeType === '' ? isAll : t === activeType);
    });
  }

  function _applyFilter(revisions) {
    if (!revisionList) return;
    revisionList.querySelectorAll('.theo-revision-card').forEach(function (card, idx) {
      if (!_activeFilter) {
        card.classList.remove('hidden');
      } else {
        var rev = revisions[idx];
        card.classList.toggle('hidden', !rev || rev.revision_type !== _activeFilter);
      }
    });
  }

  function _buildRevisionCard(rev) {
    var card = document.createElement('div');
    card.className = 'theo-revision-card';

    var conf    = rev.confidence || 0;
    var pct     = Math.round(conf * 100);
    var confCls = conf >= 0.75 ? 'badge-high' : conf >= 0.45 ? 'badge-medium' : 'badge-low';

    var citations = (rev.scholarly_citations || []).join('; ');

    card.innerHTML =
      '<div class="theo-card-header">' +
        '<span class="theo-ref-label">' + _esc(rev.reference || '') + '</span>' +
        _traditionBadge(rev.tradition) +
        '<span class="theo-type-badge">' + _esc(_revisionTypeLabel(rev.revision_type || '')) + '</span>' +
        '<span class="conf-badge ' + confCls + '" style="margin-left:auto">' + pct + '%</span>' +
      '</div>' +

      '<div class="theo-readings">' +
        '<div class="theo-reading-box">' +
          '<div class="theo-reading-label">MT / Earlier Reading</div>' +
          '<div class="theo-reading-text">' + _esc(rev.mt_reading || '') + '</div>' +
        '</div>' +
        '<div class="theo-reading-box">' +
          '<div class="theo-reading-label">' + _esc(rev.tradition || 'Revised') + ' Reading</div>' +
          '<div class="theo-reading-text">' + _esc(rev.revised_reading || '') + '</div>' +
        '</div>' +
      '</div>' +

      '<p class="div-analysis">' + _esc(rev.evidence_plain || '') + '</p>' +
      (rev.evidence && rev.evidence !== rev.evidence_plain
        ? '<p class="div-meta" style="font-style:italic;margin-top:6px">' + _esc(rev.evidence) + '</p>'
        : '') +
      (citations ? '<p class="theo-scholars">Sources: ' + _esc(citations) + '</p>' : '') +
      (rev.counter_arguments
        ? '<div class="theo-counter"><strong>Counter-argument:</strong> ' + _esc(rev.counter_arguments) + '</div>'
        : '');

    return card;
  }

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
  function _revisionTypeLabel(slug) {
    var labels = {
      anthropomorphism_avoidance: 'Anthropomorphism Avoidance',
      messianic_heightening:      'Messianic Heightening',
      harmonization:              'Harmonization',
      softening:                  'Softening',
      proto_rabbinic:             'Proto-Rabbinic',
      eschatological_sharpening:  'Eschatological Sharpening',
    };
    return labels[slug] || (slug || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function _traditionBadge(tradition) {
    var cls = {
      LXX:      'theo-tradition-lxx',
      Targum:   'theo-tradition-targum',
      Peshitta: 'theo-tradition-peshitta',
      Vulgate:  'theo-tradition-vulgate',
      SP:       'theo-tradition-sp',
      MT:       'theo-tradition-mt',
    };
    var c = cls[tradition] || 'theo-tradition-lxx';
    return '<span class="theo-tradition-badge ' + c + '">' + _esc(tradition || '') + '</span>';
  }

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
  window.theological = { analyze: analyze };

})();
