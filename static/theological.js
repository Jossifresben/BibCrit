/* BibCrit — Theological Revision Detector */

(function () {
  'use strict';

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
  var corpusPanel    = document.getElementById('theo-corpus-panel');

  if (!btnAnalyze) return;

  // ── Corpus browser ──────────────────────────────────────────────────────────
  if (selBook) {
    fetch('/api/books?tradition=MT')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        (data.books || []).forEach(function (book) {
          var opt = document.createElement('option');
          opt.value = book; opt.textContent = book;
          selBook.appendChild(opt);
        });
      }).catch(function () {});

    selBook.addEventListener('change', function () {
      var book = selBook.value;
      selChapter.innerHTML = '<option value="">' + (window.t ? window.t('passage_ch', 'Ch\u2026') : 'Ch\u2026') + '</option>';
      selChapter.disabled = !book;
      selVerse.innerHTML = '<option value="">' + (window.t ? window.t('passage_vs', 'Vs\u2026') : 'Vs\u2026') + '</option>';
      selVerse.disabled = true;
      if (!book) return;
      fetch('/api/chapters?book=' + encodeURIComponent(book) + '&tradition=MT')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          (data.chapters || []).forEach(function (ch) {
            var opt = document.createElement('option');
            opt.value = ch; opt.textContent = ch;
            selChapter.appendChild(opt);
          });
          selChapter.disabled = false;
        });
    });

    selChapter.addEventListener('change', function () {
      var book = selBook.value, ch = selChapter.value;
      selVerse.innerHTML = '<option value="">' + (window.t ? window.t('passage_vs', 'Vs\u2026') : 'Vs\u2026') + '</option>';
      selVerse.disabled = !ch;
      if (!ch) return;
      fetch('/api/verses?book=' + encodeURIComponent(book) + '&chapter=' + ch + '&tradition=MT')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          (data.verses || []).forEach(function (v) {
            var opt = document.createElement('option');
            opt.value = v; opt.textContent = v;
            selVerse.appendChild(opt);
          });
          selVerse.disabled = false;
        });
    });

    selVerse.addEventListener('change', function () {
      if (selBook.value && selChapter.value && selVerse.value) {
        refInput.value = selBook.value + ' ' + selChapter.value + ':' + selVerse.value;
      }
    });
  }

  var _es           = null;
  var _timer        = null;
  var _currentRef   = '';
  var _finalHandled = false;
  var _activeFilter = '';
  var _lastData     = null;
  var _partialData    = {};   // accumulates section key/value pairs during streaming
  var _sectionReceived = false;  // true once any section event has been handled

  // ── Skeleton helpers ──────────────────────────────────────────────────────
  function _skelRows(n, widths) {
    var html = '', pcts = widths || [100, 88, 72, 58, 45];
    for (var i = 0; i < n; i++)
      html += '<div class="dss-skel-row" style="height:12px;width:' + (pcts[i] || 55) + '%"></div>';
    return html;
  }
  function _hideCompactSpinner() {
    if (loadState) { loadState.classList.remove('is-compact'); loadState.style.display = 'none'; }
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
    var revList = document.getElementById('revision-list');
    // Write skeleton into child body refs — not into parent sections —
    // so module-level body references (summaryBody, overallBody, bibBody) stay attached.
    if (summarySection) summarySection.style.display = '';
    if (summaryBody)    summaryBody.innerHTML = '<div style="padding:1rem">' + _skelRows(3, [100, 85, 70]) + '</div>';
    if (revList)        { revList.style.display = ''; revList.innerHTML = _skelCard() + _skelCard(); }
    if (overallSection) overallSection.style.display = '';
    if (overallBody)    overallBody.innerHTML = '<div style="padding:1rem">' + _skelRows(3, [95, 80, 65]) + '</div>';
    if (bibSec)         bibSec.style.display = '';
    if (bibBody)        bibBody.innerHTML = '<div style="padding:1rem">' + _skelRows(3, [95, 80, 65]) + '</div>';
  }

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
    if (window.BibCrit_checkPassageLength && window.BibCrit_checkPassageLength(ref)) return;
    if (window.BibCrit_requireVerse && window.BibCrit_requireVerse(ref)) return;
    _currentRef  = ref;
    _activeFilter = '';

    if (_es) { _es.close(); _es = null; }
    clearInterval(_timer);
    _finalHandled = false;
    _partialData     = {};
    _sectionReceived = false;

    hide(suggestions);
    hide(emptyState);
    if (corpusPanel) { corpusPanel.innerHTML = ''; corpusPanel.style.display = 'none'; }
    if (results) results.style.display = '';
    if (loadState) {
      loadState.classList.add('is-compact');
      loadState.style.display = 'block';
    }
    if (heading) {
      heading.innerHTML = '<span class="ph-ref">' + _esc(_currentRef) + '</span>';
      show(heading);
    }
    setLoadingStep(window.t('loading_preparing', 'Preparing…'));

    var elapsed = 0;
    _timer = setInterval(function () {
      elapsed++;
      if (loadTimer) loadTimer.textContent = elapsed + 's';
    }, 1000);
    _renderSkeleton();

    history.replaceState(null, '', '/theological?ref=' + encodeURIComponent(ref));

    _es = new EventSource('/api/theological/stream?ref=' + encodeURIComponent(ref) + '&lang=' + (window.bibcritLang || 'en'));

    _es.addEventListener('message', function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          setLoadingStep(msg.msg);
        } else if (msg.type === 'section') {
          _renderSection(msg.key, msg.data);
        } else if (msg.type === 'error') {
          _finalHandled = true;
          _hideCompactSpinner();
          setLoadingStep('❌ ' + msg.msg);
          _es.close();
        } else if (msg.type === 'done') {
          _finalHandled = true;
          _hideCompactSpinner();
          _es.close();
          if (_sectionReceived) {
            _finalize(msg.data);
          } else {
            renderRevisions(msg.data);  // cache-hit fallback: done without sections
          }
        }
      } catch (_) { /* ignore */ }
    });

    _es.onerror = function () {
      if (_finalHandled) return;
      _hideCompactSpinner();
      setLoadingStep('❌ ' + window.t('err_connection_step', 'Connection error. Please try again.'));
      if (_es) _es.close();
    };
  }

  function _renderCorpusPanel(mtText, lxxText) {
    if (!corpusPanel) return;
    var html = '<div class="bt-group-card" style="max-width:900px;margin:0 auto 1rem;padding:1rem 1.25rem;">';
    if (mtText) {
      html += '<div style="font-size:0.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
            + 'color:var(--muted);margin-bottom:0.4rem">Hebrew (MT)</div>'
            + '<div class="hebrew-text verse-text" style="margin-bottom:' + (lxxText ? '0.9rem' : '0') + '">'
            + _esc(mtText) + '</div>';
    }
    if (lxxText) {
      html += '<div style="font-size:0.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
            + 'color:var(--muted);margin-bottom:0.4rem">Greek (LXX)</div>'
            + '<div class="greek-text verse-text">' + _esc(lxxText) + '</div>';
    }
    html += '</div>';
    corpusPanel.innerHTML = html;
    corpusPanel.style.display = '';
  }

  // ── Progressive section rendering ────────────────────────────────────────
  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived  = true;

    if (key === '_corpus') {
      _renderCorpusPanel(data.mt_text || '', data.lxx_text || '');
      return;
    }

    // Reveal results container, hide loading / empty states
    if (results)    results.style.display    = '';
    if (emptyState) emptyState.style.display = 'none';

    // Heading: render as soon as scope is known
    if ((key === 'scope' || key === 'scope_type') && heading && _partialData.scope) {
      var _hRef  = _esc(_partialData.scope);
      var _hMeta = _partialData.scope_type
        ? ' <span class="ph-meta">— ' +
            _esc(_partialData.scope_type.charAt(0).toUpperCase() +
                 _partialData.scope_type.slice(1)) + '</span>'
        : '';
      heading.innerHTML = '<span class="ph-ref">' + _hRef + '</span>' + _hMeta;
      show(heading);
    }

    // Summary section: render as soon as summary_plain arrives
    if ((key === 'summary' || key === 'summary_plain' || key === 'dominant_strategy') &&
        summarySection && summaryBody &&
        (_partialData.summary_plain || _partialData.summary)) {
      var summ = _partialData.summary_plain || _partialData.summary || '';
      summaryBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(summ) + '</p>' +
          (_partialData.summary && _partialData.summary !== summ
            ? '<p class="div-meta" style="margin-top:8px;font-style:italic">' +
                _esc(_partialData.summary) + '</p>'
            : '') +
          (_partialData.dominant_strategy
            ? '<p style="margin-top:8px;font-size:0.875rem;color:var(--fg)"><strong>' +
                window.t('theo_dominant_strategy', 'Dominant strategy:') + '</strong> ' +
                _esc(_partialData.dominant_strategy) + '</p>'
            : '') +
        '</div>';
      show(summarySection);
      staggerReveal(summarySection, 0);
    }

    // Revisions: render cards as soon as the array arrives
    if (key === 'revisions') {
      var revisions = (data || []).slice().sort(function (a, b) {
        return (b.confidence || 0) - (a.confidence || 0);
      });

      var types = [];
      revisions.forEach(function (r) {
        var t = r.revision_type || '';
        if (t && types.indexOf(t) === -1) types.push(t);
      });

      if (filterChips && types.length > 1) {
        filterChips.innerHTML = '';
        var allBtn = document.createElement('button');
        allBtn.className = 'theo-filter-chip active';
        allBtn.textContent = window.t('filter_all', 'All');
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
        revisionList.innerHTML =
          '<p style="padding:1rem;color:var(--muted);text-align:center">' +
            window.t('theo_no_revisions', 'No theologically motivated revisions identified.') +
          '</p>';
      }
      staggerReveal(revisionList, 30);
    }

    // Overall assessment: render as soon as either field arrives
    if ((key === 'overall_assessment' || key === 'overall_plain') &&
        overallSection && overallBody &&
        (_partialData.overall_plain || _partialData.overall_assessment)) {
      var overall = _partialData.overall_plain || _partialData.overall_assessment || '';
      overallBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(overall) + '</p>' +
          (_partialData.overall_assessment && _partialData.overall_assessment !== overall
            ? '<p class="div-meta" style="margin-top:8px;font-style:italic">' +
                _esc(_partialData.overall_assessment) + '</p>'
            : '') +
        '</div>';
      show(overallSection);
      staggerReveal(overallSection, 0);
    }

    // BibCrit assessment
    if (key === 'bibcrit_assessment') {
      renderAssessment({ bibcrit_assessment: data,
                         model_version: _partialData.model_version });
      if (bibSec) staggerReveal(bibSec, 0);
    }
  }

  function _finalize(data) {
    _lastData = data || _partialData;
    _hideCompactSpinner();

    // Refresh heading with authoritative scope from final data
    if (heading && data) {
      var _hRef  = _esc(data.scope || _currentRef);
      var _hMeta = data.scope_type
        ? ' <span class="ph-meta">— ' +
            _esc(data.scope_type.charAt(0).toUpperCase() +
                 data.scope_type.slice(1)) + '</span>'
        : '';
      heading.innerHTML = '<span class="ph-ref">' + _hRef + '</span>' + _hMeta;
      show(heading);
    }

    // Re-render summary with complete data (dominant_strategy may have arrived late)
    if (data && summarySection && summaryBody &&
        (data.summary_plain || data.summary)) {
      var summ = data.summary_plain || data.summary || '';
      summaryBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(summ) + '</p>' +
          (data.summary && data.summary !== summ
            ? '<p class="div-meta" style="margin-top:8px;font-style:italic">' +
                _esc(data.summary) + '</p>'
            : '') +
          (data.dominant_strategy
            ? '<p style="margin-top:8px;font-size:0.875rem;color:var(--fg)"><strong>' +
                window.t('theo_dominant_strategy', 'Dominant strategy:') + '</strong> ' +
                _esc(data.dominant_strategy) + '</p>'
            : '') +
        '</div>';
      show(summarySection);
    }

    if (exportRow) show(exportRow);
    staggerReveal(results, 90);

    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'theological',
        getReference: function() { return _currentRef; },
        getResultData: function() { return _lastData || {}; },
      });
    }

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

  // ── Render ───────────────────────────────────────────────────────────────
  function renderRevisions(data) {
    _lastData = data;
    _hideCompactSpinner();

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
            ? '<p style="margin-top:8px;font-size:0.875rem;color:var(--fg)"><strong>' + window.t('theo_dominant_strategy', 'Dominant strategy:') + '</strong> ' + _esc(data.dominant_strategy) + '</p>'
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
      allBtn.textContent = window.t('filter_all', 'All');
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
      revisionList.innerHTML = '<p style="padding:1rem;color:var(--muted);text-align:center">' + window.t('theo_no_revisions', 'No theologically motivated revisions identified.') + '</p>';
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

    staggerReveal(results, 90);
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
          '<div class="theo-reading-label">' + window.t('theo_mt_reading_label', 'MT / Earlier Reading') + '</div>' +
          '<div class="theo-reading-text">' + _esc(rev.mt_reading || '') + '</div>' +
        '</div>' +
        '<div class="theo-reading-box">' +
          '<div class="theo-reading-label">' + _esc(rev.tradition || window.t('theo_revised_reading_label', 'Revised Reading')) + '</div>' +
          '<div class="theo-reading-text">' + _esc(rev.revised_reading || '') + '</div>' +
        '</div>' +
      '</div>' +

      '<p class="div-analysis">' + _esc(rev.evidence_plain || '') + '</p>' +
      (rev.evidence && rev.evidence !== rev.evidence_plain
        ? '<p class="div-meta" style="font-style:italic;margin-top:6px">' + _esc(rev.evidence) + '</p>'
        : '') +
      (citations ? '<p class="theo-scholars">' + window.t('theo_sources_label', 'Sources:') + ' ' + _esc(citations) + '</p>' : '') +
      (rev.counter_arguments
        ? '<div class="theo-counter"><strong>' + window.t('theo_counter_arg_label', 'Counter-argument:') + '</strong> ' + _esc(rev.counter_arguments) + '</div>'
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
          (pct ? '<p style="margin-top:10px"><span class="conf-badge ' + confCls + '">' + window.t('num_confidence_label', 'Confidence:') + ' ' + pct + '%</span></p>' : '') +
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + (_formatCached(data.cached_at) ? ' · ' + _esc(_formatCached(data.cached_at)) : '') + '</p>' +
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
    var map = {
      anthropomorphism_avoidance: 'theo_type_anthropomorphism_avoidance',
      messianic_heightening:      'theo_type_messianic_heightening',
      harmonization:              'theo_type_harmonization',
      softening:                  'theo_type_softening',
      proto_rabbinic:             'theo_type_proto_rabbinic',
      eschatological_sharpening:  'theo_type_eschatological_sharpening',
    };
    var fallbacks = {
      anthropomorphism_avoidance: 'Anthropomorphism Avoidance',
      messianic_heightening:      'Messianic Heightening',
      harmonization:              'Harmonization',
      softening:                  'Softening',
      proto_rabbinic:             'Proto-Rabbinic',
      eschatological_sharpening:  'Eschatological Sharpening',
    };
    if (map[slug]) return window.t(map[slug], fallbacks[slug]);
    return (slug || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
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

  function _formatCached(isoStr) {
    if (!isoStr) return '';
    try {
      var d = new Date(isoStr);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) { return ''; }
  }

  // ── Public API ───────────────────────────────────────────────────────────
  window.theological = { analyze: analyze };

})();
