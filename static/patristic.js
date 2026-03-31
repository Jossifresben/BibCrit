/* BibCrit — Patristic Citation Tracker */

(function () {
  'use strict';

  var refInput   = document.getElementById('ref-input');
  var btnAnalyze = document.getElementById('btn-analyze');
  var infoBanner = document.getElementById('patristic-info-banner');
  var infoClose  = document.getElementById('patristic-info-close');
  var emptyState = document.getElementById('empty-state');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var results    = document.getElementById('patristic-results');
  var distSection  = document.getElementById('distribution-section');
  var distBar      = document.getElementById('distribution-bar');
  var periodSection = document.getElementById('period-section');
  var periodBody    = document.getElementById('period-body');
  var filterChips  = document.getElementById('filter-chips');
  var citationList = document.getElementById('citation-list');
  var variantsSec  = document.getElementById('variants-section');
  var variantsBody = document.getElementById('variants-body');
  var synthSec     = document.getElementById('synthesis-section');
  var synthBody    = document.getElementById('synthesis-body');
  var bibSec     = document.getElementById('bibcrit-assessment');
  var bibBody    = document.getElementById('bibcrit-body');
  var exportRow  = document.getElementById('export-row');
  var btnShare   = document.getElementById('btn-share');
  var suggestions  = document.getElementById('pat-suggestions');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  // ── Info banner dismiss ─────────────────────────────────────────────────
  var _BANNER_VER = 'patristic-info-v1';
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
    if (!ref) { showToast(window.t('err_enter_ref', 'Please enter a passage reference.')); return; }
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

    history.replaceState(null, '', '/patristic?ref=' + encodeURIComponent(ref));

    _es = new EventSource('/api/patristic/stream?ref=' + encodeURIComponent(ref) + '&lang=' + (window.bibcritLang || 'en'));

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
          renderPatristic(msg.data);
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
  function renderPatristic(data) {
    _lastData = data;
    hide(loadState);

    show(heading);
    var total = data.total_citations_found || (data.citations || []).length;
    var _hRef  = _esc(data.reference || _currentRef);
    var _hMeta = total ? ' <span class="ph-meta">— ' + total + ' citation' + (total === 1 ? '' : 's') + ' found</span>' : '';
    heading.innerHTML = '<span class="ph-ref">' + _hRef + '</span>' + _hMeta;

    // Distribution bar
    renderDistributionBar(data);

    // Period summary
    var period = data.period_summary || '';
    if (period && periodSection && periodBody) {
      periodBody.innerHTML = '<div class="bt-group-card"><p class="div-analysis">' + _esc(period) + '</p></div>';
      show(periodSection);
    }

    // Citations
    var citations = data.citations || [];

    // Build filter chips
    var forms = [];
    citations.forEach(function (c) {
      var f = c.text_form || '';
      if (f && forms.indexOf(f) === -1) forms.push(f);
    });

    if (filterChips && forms.length > 1) {
      filterChips.innerHTML = '';
      var allBtn = document.createElement('button');
      allBtn.className = 'theo-filter-chip active';
      allBtn.textContent = 'All';
      allBtn.addEventListener('click', function () {
        _activeFilter = '';
        _updateFilterChips(filterChips, '');
        _applyFilter(citations);
      });
      filterChips.appendChild(allBtn);

      forms.forEach(function (f) {
        var btn = document.createElement('button');
        btn.className = 'theo-filter-chip';
        btn.textContent = _textFormLabel(f);
        btn.setAttribute('data-form', f);
        btn.addEventListener('click', function () {
          _activeFilter = f;
          _updateFilterChips(filterChips, f);
          _applyFilter(citations);
        });
        filterChips.appendChild(btn);
      });
      show(filterChips);
    }

    if (citationList) {
      citationList.innerHTML = '';
      citations.forEach(function (cit) {
        citationList.appendChild(_buildCitationCard(cit));
      });
    }

    if (!citations.length && citationList) {
      citationList.innerHTML = '<p style="padding:1rem;color:var(--muted);text-align:center">No patristic citations found for this passage.</p>';
    }

    // Notable variants
    renderNotableVariants(data);

    // Synthesis
    var synth = data.transmission_synthesis_plain || data.transmission_synthesis || '';
    if (synth && synthSec && synthBody) {
      synthBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(synth) + '</p>' +
          (data.transmission_synthesis && data.transmission_synthesis !== synth
            ? '<p class="div-meta" style="margin-top:8px;font-style:italic">' + _esc(data.transmission_synthesis) + '</p>'
            : '') +
        '</div>';
      show(synthSec);
    }

    // BibCrit assessment
    renderAssessment(data);

    show(results);
    if (exportRow) show(exportRow);

    // Inject Scholar Rating, Copy, Download into export-row (once only)
    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'patristic',
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
          fetch('/api/export/sbl?tool=patristic&ref=' + encodeURIComponent(_currentRef))
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
          fetch('/api/export/bibtex?tool=patristic&ref=' + encodeURIComponent(_currentRef))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              navigator.clipboard.writeText(d.bibtex || '').catch(function(){});
              showToast(window.t('toast_bibtex_copied_short', 'BibTeX copied!'));
            }).catch(function(){});
        });
      }
    }
  }

  // ── Distribution bar ─────────────────────────────────────────────────────
  function renderDistributionBar(data) {
    if (!distBar) return;

    var dist = data.text_form_distribution || {};
    var total = 0;
    var FORMS = ['closer_to_lxx', 'closer_to_mt', 'mixed', 'independent', 'uncertain'];
    var COLORS = {
      closer_to_lxx: '#3a6bc4',
      closer_to_mt:  '#c0892a',
      mixed:         '#8e44ad',
      independent:   '#e67e22',
      uncertain:     '#95a5a6',
    };

    FORMS.forEach(function (f) { total += (dist[f] || 0); });

    if (!total) {
      distBar.innerHTML = '<p style="color:var(--muted);font-size:0.875rem">No distribution data available.</p>';
      return;
    }

    var bar = document.createElement('div');
    bar.className = 'pat-dist-bar';

    var legend = document.createElement('div');
    legend.className = 'pat-dist-legend';

    FORMS.forEach(function (f) {
      var count = dist[f] || 0;
      if (!count) return;
      var pct = Math.round((count / total) * 100);

      var seg = document.createElement('div');
      seg.className = 'pat-dist-segment';
      seg.style.flex = String(count);
      seg.style.background = COLORS[f] || '#888';
      seg.title = _textFormLabel(f) + ': ' + count;
      if (pct >= 15) seg.textContent = pct + '%';
      bar.appendChild(seg);

      var li = document.createElement('div');
      li.className = 'pat-dist-legend-item';
      li.innerHTML =
        '<span class="pat-dist-swatch" style="background:' + (COLORS[f] || '#888') + '"></span>' +
        '<span>' + _esc(_textFormLabel(f)) + ': <strong>' + count + '</strong></span>';
      legend.appendChild(li);
    });

    distBar.innerHTML = '';
    distBar.appendChild(bar);
    distBar.appendChild(legend);
    if (distSection) show(distSection);
  }

  // ── Citation cards ────────────────────────────────────────────────────────
  function _buildCitationCard(cit) {
    var card = document.createElement('div');
    card.className = 'pat-citation-card';
    card.setAttribute('data-form', cit.text_form || '');

    var conf    = cit.text_form_confidence || 0;
    var pct     = Math.round(conf * 100);
    var confCls = conf >= 0.75 ? 'badge-high' : conf >= 0.45 ? 'badge-medium' : 'badge-low';

    var tfBadgeClass = 'pat-tf-' + (cit.text_form || 'uncertain').replace(/[^a-z_]/g, '_');

    card.innerHTML =
      '<div class="pat-card-header">' +
        '<span class="pat-father-name">' + _esc(cit.father || '') + '</span>' +
        '<span class="pat-dates">' + _esc(cit.dates_ce || '') + '</span>' +
        '<span class="pat-region-badge">' + _esc(cit.region || '') + '</span>' +
        '<span class="pat-text-form-badge ' + tfBadgeClass + '">' + _esc(_textFormLabel(cit.text_form || '')) + '</span>' +
        (pct ? '<span class="conf-badge ' + confCls + '" style="margin-left:auto">' + pct + '%</span>' : '') +
      '</div>' +

      '<p class="pat-work-ref">' +
        _esc(cit.work || '') +
        (cit.chapter_section ? ' ' + _esc(cit.chapter_section) : '') +
      '</p>' +

      (cit.cited_text ? '<div class="pat-cited-text">' + _esc(cit.cited_text) + '</div>' : '') +

      '<div class="pat-subfields">' +
        (cit.text_form_note
          ? '<span class="pat-subfield-label">Text Form Note</span>' + _esc(cit.text_form_note)
          : '') +
        (cit.theological_use
          ? '<span class="pat-subfield-label">Theological Use</span>' + _esc(cit.theological_use)
          : '') +
        (cit.transmission_implication
          ? '<span class="pat-subfield-label">Transmission Implication</span>' + _esc(cit.transmission_implication)
          : '') +
      '</div>';

    return card;
  }

  // ── Notable variants ──────────────────────────────────────────────────────
  function renderNotableVariants(data) {
    var variants = data.notable_variants || [];
    if (!variants.length || !variantsSec || !variantsBody) return;

    variantsBody.innerHTML = '';
    variants.forEach(function (v) {
      var card = document.createElement('div');
      card.className = 'pat-variant-card';

      var tfBadgeClass = 'pat-tf-' + (v.text_form_alignment || 'uncertain').replace(/[^a-z_]/g, '_');
      var fathers = (v.fathers_using_it || []).join(', ');

      card.innerHTML =
        '<div class="pat-variant-reading">' + _esc(v.reading || '') + '</div>' +
        '<p class="pat-variant-fathers">Used by: ' + _esc(fathers) + '</p>' +
        '<span class="pat-text-form-badge ' + tfBadgeClass + '">' + _esc(_textFormLabel(v.text_form_alignment || '')) + '</span>' +
        (v.significance ? '<p style="font-size:0.875rem;margin-top:0.5rem;line-height:1.7;color:var(--fg)">' + _esc(v.significance) + '</p>' : '');

      variantsBody.appendChild(card);
    });
    show(variantsSec);
  }

  function _updateFilterChips(container, activeForm) {
    container.querySelectorAll('.theo-filter-chip').forEach(function (btn) {
      var f = btn.getAttribute('data-form') || '';
      var isAll = !f;
      btn.classList.toggle('active', activeForm === '' ? isAll : f === activeForm);
    });
  }

  function _applyFilter(citations) {
    if (!citationList) return;
    citationList.querySelectorAll('.pat-citation-card').forEach(function (card, idx) {
      if (!_activeFilter) {
        card.classList.remove('hidden');
      } else {
        var cit = citations[idx];
        card.classList.toggle('hidden', !cit || cit.text_form !== _activeFilter);
      }
    });
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
  function _textFormLabel(slug) {
    var labels = {
      closer_to_lxx: 'Closer to LXX',
      closer_to_mt:  'Closer to MT',
      mixed:         'Mixed',
      independent:   'Independent',
      uncertain:     'Uncertain',
    };
    return labels[slug] || (slug || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
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
  window.patristic = { analyze: analyze };

})();
