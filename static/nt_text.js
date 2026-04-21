/* BibCrit — NT Textual Tradition Analyzer */

(function () {
  'use strict';

  var _NT_BOOKS = {
    'Matthew': 28, 'Mark': 16, 'Luke': 24, 'John': 21, 'Acts': 28,
    'Romans': 16, '1 Corinthians': 16, '2 Corinthians': 13,
    'Galatians': 6, 'Ephesians': 6, 'Philippians': 4, 'Colossians': 4,
    '1 Thessalonians': 5, '2 Thessalonians': 3, '1 Timothy': 6,
    '2 Timothy': 4, 'Titus': 3, 'Philemon': 1, 'Hebrews': 13,
    'James': 5, '1 Peter': 5, '2 Peter': 3, '1 John': 5,
    '2 John': 1, '3 John': 1, 'Jude': 1, 'Revelation': 22,
  };

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
  var results    = document.getElementById('nt-text-results');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  var _timer = null;
  var _currentRef = '';
  var _finalHandled   = false;
  var _partialData    = {};
  var _sectionReceived = false;

  if (selBook) {
    Object.keys(_NT_BOOKS).forEach(function (b) {
      var opt = document.createElement('option');
      opt.value = b; opt.textContent = b;
      selBook.appendChild(opt);
    });
  }

  function _resetSelect(el, ph) {
    while (el.options.length > 1) el.remove(1);
    el.options[0].text = ph;
    el.disabled = true; el.value = '';
  }

  if (selBook) {
    selBook.addEventListener('change', function () {
      _resetSelect(selChapter, 'Ch\u2026');
      _resetSelect(selVerse, 'Vs\u2026');
      var n = _NT_BOOKS[this.value] || 0;
      for (var i = 1; i <= n; i++) {
        var o = document.createElement('option');
        o.value = i; o.textContent = i; selChapter.appendChild(o);
      }
      if (n) selChapter.disabled = false;
    });
  }

  if (selChapter) {
    selChapter.addEventListener('change', function () {
      _resetSelect(selVerse, 'Vs\u2026');
      for (var v = 1; v <= 30; v++) {
        var o = document.createElement('option');
        o.value = v; o.textContent = v; selVerse.appendChild(o);
      }
      selVerse.disabled = false;
    });
  }

  if (selVerse) {
    selVerse.addEventListener('change', function () {
      var b = selBook ? selBook.value : '';
      var c = selChapter ? selChapter.value : '';
      if (b && c && this.value) refInput.value = b + ' ' + c + ':' + this.value;
    });
  }

  document.querySelectorAll('.featured-ref').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.dataset.ref;
      if (ref) { refInput.value = ref; analyze(ref); }
    });
  });

  btnAnalyze.addEventListener('click', function () {
    var ref = (refInput ? refInput.value : '').trim();
    if (!ref) { showToast(window.t ? window.t('err_enter_passage', 'Please enter a passage') : 'Please enter a passage'); return; }
    analyze(ref);
  });

  if (refInput) refInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') btnAnalyze.click(); });

  function showToast(msg, dur) {
    if (!toast) return;
    toast.textContent = msg; toast.style.display = 'block';
    setTimeout(function () { toast.style.display = 'none'; }, dur || 3000);
  }

  function setLoading(on) {
    if (on && emptyState) emptyState.style.display = 'none'; // only hide; renderResult shows results explicitly
    if (loadState)  loadState.style.display  = on ? 'block' : 'none';
    if (results)    results.style.display    = on ? 'none' : 'block';
    if (on && _timer) clearInterval(_timer);
    if (on && loadTimer) {
      var s = 0; loadTimer.textContent = '';
      _timer = setInterval(function () { loadTimer.textContent = (++s) + 's'; }, 1000);
    } else if (loadTimer) { loadTimer.textContent = ''; }
  }

  function _hideCompactSpinner() {
    if (_timer) { clearInterval(_timer); _timer = null; }
    if (loadTimer) loadTimer.textContent = '';
    if (loadState) { loadState.classList.remove('is-compact'); loadState.style.display = 'none'; }
  }

  function _skelRows(n, widths) {
    var html = '';
    var pcts = widths || [100, 88, 72, 58, 45];
    for (var i = 0; i < n; i++) {
      html += '<div class="dss-skel-row" style="height:12px;width:' + (pcts[i % pcts.length] || 55) + '%"></div>';
    }
    return html;
  }

  function _renderSkeleton() {
    var gntSec = document.getElementById('gnt-text-display');
    var gntEl  = document.getElementById('gnt-text-body');
    if (gntEl)  gntEl.innerHTML  = _skelRows(4, [100, 88, 76, 60]);
    if (gntSec) gntSec.style.display = '';

    var mSec  = document.getElementById('metzger-section');
    var badge = document.getElementById('metzger-badge');
    var just  = document.getElementById('metzger-justification');
    if (badge) badge.innerHTML = '<div class="dss-skel-row" style="height:28px;width:40px"></div>';
    if (just)  just.innerHTML  = _skelRows(2, [100, 70]);
    if (mSec)  mSec.style.display = '';

    var mfSec = document.getElementById('ms-families-section');
    var mfEl  = document.getElementById('ms-families-body');
    if (mfEl)  mfEl.innerHTML  = _skelRows(4, [100, 80, 100, 80]);
    if (mfSec) mfSec.style.display = '';

    var synSec = document.getElementById('synthesis-section');
    var synEl  = document.getElementById('synthesis-body');
    if (synEl)  synEl.innerHTML  = _skelRows(3, [100, 85, 65]);
    if (synSec) synSec.style.display = '';
  }

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  var _SUPPORT_LABELS = {
    'sides_with_received': 'Sides with received',
    'sides_with_critical': 'Sides with critical',
    'split':               'Split evidence',
    'not_applicable':      'N/A',
    'unknown':             'Unknown',
  };

  function _supportLabel(s) { return _SUPPORT_LABELS[s] || (s || '').replace(/_/g, ' '); }

  function _buildFamilyHtml(fKey, fm) {
    var supportClass = 'ms-support support-' + (fm.support || 'unknown').replace(/_/g, '-');
    return '<div class="ms-family-row">' +
      '<div class="ms-family-header">' +
        '<span class="ms-family-name">' + esc(fKey.charAt(0).toUpperCase() + fKey.slice(1)) + '</span>' +
        '<span class="' + supportClass + '">' + esc(_supportLabel(fm.support)) + '</span>' +
      '</div>' +
      (fm.witnesses && fm.witnesses.length
        ? '<div class="ms-family-witnesses">' + esc(fm.witnesses.join(', ')) + '</div>' : '') +
      '<p class="ms-family-note">' + esc(fm.note || '') + '</p>' +
    '</div>';
  }

  function renderResult(data) {
    if (_timer) { clearInterval(_timer); _timer = null; }
    if (loadTimer) loadTimer.textContent = '';
    setLoading(false);
    if (heading) { heading.textContent = data.reference || _currentRef; heading.style.display = ''; }

    // GNT text
    if (data.gnt_text) {
      var gntEl = document.getElementById('gnt-text-body');
      var gntSec = document.getElementById('gnt-text-display');
      if (gntEl) gntEl.textContent = data.gnt_text;
      if (gntSec) gntSec.style.display = '';
    }

    // Metzger rating
    if (data.metzger_rating && data.metzger_rating.rating) {
      var badge = document.getElementById('metzger-badge');
      var just  = document.getElementById('metzger-justification');
      var mSec  = document.getElementById('metzger-section');
      var r     = data.metzger_rating.rating.toUpperCase();
      if (badge) {
        badge.textContent = r;
        badge.className = 'ms-rating-badge rating-' + r.toLowerCase();
      }
      if (just) just.textContent = data.metzger_rating.justification || '';
      if (mSec) mSec.style.display = '';
    }

    // Manuscript families
    if (data.manuscript_families) {
      var mfHtml = '';
      ['alexandrian', 'western', 'byzantine', 'caesarean'].forEach(function (f) {
        var fm = data.manuscript_families[f];
        if (fm) mfHtml += _buildFamilyHtml(f, fm);
      });
      var mfEl  = document.getElementById('ms-families-body');
      var mfSec = document.getElementById('ms-families-section');
      if (mfEl) mfEl.innerHTML = mfHtml;
      if (mfSec && mfHtml) mfSec.style.display = '';
    }

    // Variant register
    if (data.variant_register && data.variant_register.length) {
      var vrHtml = data.variant_register.map(function (v, i) {
        return '<div class="variant-card">' +
          '<div class="vc-type">Variant ' + (i + 1) + '</div>' +
          '<p class="vc-text">' + esc(v.variant_text || '') + '</p>' +
          '<div class="vc-pair"><span class="vc-label">Support:</span> ' + esc(v.manuscript_support || '') + '</div>' +
          '<div class="vc-pair">' +
            '<span class="vc-label">Intrinsic:</span> ' + esc(v.intrinsic_probability || '') +
            ' &nbsp;|&nbsp; <span class="vc-label">Transcriptional:</span> ' + esc(v.transcriptional_probability || '') +
          '</div>' +
          '<p class="vc-note">' + esc(v.assessment || '') + '</p></div>';
      }).join('');
      var vrEl  = document.getElementById('variant-body');
      var vrSec = document.getElementById('variant-section');
      if (vrEl) vrEl.innerHTML = vrHtml;
      if (vrSec) vrSec.style.display = '';
    }

    // Disputed passage
    if (data.disputed_passage) {
      var dp = data.disputed_passage;
      var dpHtml =
        '<div class="disputed-designation">' + esc(dp.designation || '') + '</div>' +
        '<div class="dp-row"><strong>Evidence for inclusion:</strong> ' + esc(dp.manuscript_evidence_for || '') + '</div>' +
        '<div class="dp-row"><strong>Evidence against:</strong> ' + esc(dp.manuscript_evidence_against || '') + '</div>' +
        '<div class="dp-row"><strong>Internal evidence:</strong> ' + esc(dp.internal_evidence || '') + '</div>' +
        '<div class="dp-row"><strong>Scholarly consensus:</strong> ' + esc(dp.scholarly_consensus || '') + '</div>' +
        '<div class="dp-row"><strong>In major translations:</strong> ' + esc(dp.pastoral_note || '') + '</div>';
      var dpEl  = document.getElementById('disputed-body');
      var dpSec = document.getElementById('disputed-section');
      if (dpEl) dpEl.innerHTML = dpHtml;
      if (dpSec) dpSec.style.display = '';
    }

    // Synthesis
    if (data.synthesis) {
      var synEl  = document.getElementById('synthesis-body');
      var synSec = document.getElementById('synthesis-section');
      if (synEl) synEl.textContent = data.synthesis;
      if (synSec) synSec.style.display = '';
    }

    // Assessment
    if (data.assessment) {
      var a = data.assessment;
      var aHtml = '';
      if (a.title)    aHtml += '<h3 class="bc-title">' + esc(a.title) + '</h3>';
      if (a.plain)    aHtml += '<p class="bc-plain">' + esc(a.plain) + '</p>';
      if (a.reasoning) aHtml += '<p>' + esc(a.reasoning) + '</p>';
      if (a.recommended_reading) aHtml += '<p><strong>Recommended edition:</strong> ' + esc(a.recommended_reading) + '</p>';
      if (a.open_questions) aHtml += '<p><strong>Open questions:</strong> ' + esc(a.open_questions) + '</p>';
      if (typeof a.confidence === 'number') {
        aHtml += '<div class="confidence-bar"><div class="confidence-fill" style="width:' + (a.confidence * 100).toFixed(0) + '%"></div></div>';
      }
      var bibBody = document.getElementById('bibcrit-body');
      var bibSec  = document.getElementById('bibcrit-assessment');
      if (bibBody) bibBody.innerHTML = aHtml;
      if (bibSec)  bibSec.style.display = '';
    }

    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';
    _wireExport(data);
  }

  function _wireExport(data) {
    var btnSbl    = document.getElementById('btn-sbl');
    var btnBibtex = document.getElementById('btn-bibtex');
    var btnShare  = document.getElementById('btn-share');
    if (btnSbl && data.citations && data.citations.sbl) {
      btnSbl.onclick = function () { navigator.clipboard.writeText(data.citations.sbl); showToast(window.t ? window.t('toast_sbl_copied_short', 'SBL copied!') : 'SBL copied!'); };
    }
    if (btnBibtex && data.citations && data.citations.bibtex) {
      btnBibtex.onclick = function () { navigator.clipboard.writeText(data.citations.bibtex); showToast(window.t ? window.t('toast_bibtex_copied_short', 'BibTeX copied!') : 'BibTeX copied!'); };
    }
    if (btnShare) {
      btnShare.onclick = function () {
        var url = window.location.origin + '/nt-text?ref=' + encodeURIComponent(_currentRef);
        navigator.clipboard.writeText(url); showToast(window.t ? window.t('toast_link_copied', 'Link copied!') : 'Link copied!');
      };
    }
  }

  // ── Progressive section rendering ─────────────────────────────────────────
  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived  = true;

    if (emptyState)  emptyState.style.display  = 'none';

    if (key === 'metzger_rating') {
      var r = data && data.rating ? data.rating.toUpperCase() : '';
      var badge = document.getElementById('metzger-badge');
      var just  = document.getElementById('metzger-justification');
      var mSec  = document.getElementById('metzger-section');
      if (badge) { badge.textContent = r; badge.className = 'ms-rating-badge rating-' + r.toLowerCase(); }
      if (just) just.textContent = (data && data.justification) || '';
      if (mSec) { mSec.style.display = ''; staggerReveal(mSec, 0); }
    }

    if (key === '_corpus') {
      var gntEl  = document.getElementById('gnt-text-body');
      var gntSec = document.getElementById('gnt-text-display');
      if (gntEl && data.gnt_text) {
        gntEl.textContent = data.gnt_text;
        if (gntSec) { gntSec.style.display = ''; staggerReveal(gntSec, 0); }
      }
      return;
    }

    if (key === 'manuscript_families') {
      var mfHtml = '';
      ['alexandrian', 'western', 'byzantine', 'caesarean'].forEach(function (f) {
        var fm = data && data[f];
        if (fm) mfHtml += _buildFamilyHtml(f, fm);
      });
      var mfEl  = document.getElementById('ms-families-body');
      var mfSec = document.getElementById('ms-families-section');
      if (mfEl) mfEl.innerHTML = mfHtml;
      if (mfSec && mfHtml) { mfSec.style.display = ''; staggerReveal(mfSec, 0); }
    }

    if (key === 'variant_register') {
      var vrArr = Array.isArray(data) ? data : (data || []);
      if (vrArr.length) {
        var vrHtml = vrArr.map(function (v, i) {
          return '<div class="variant-card">' +
            '<div class="vc-type">Variant ' + (i + 1) + '</div>' +
            '<p class="vc-text">' + esc(v.variant_text || '') + '</p>' +
            '<div class="vc-pair"><span class="vc-label">Support:</span> ' + esc(v.manuscript_support || '') + '</div>' +
            '<div class="vc-pair">' +
              '<span class="vc-label">Intrinsic:</span> ' + esc(v.intrinsic_probability || '') +
              ' &nbsp;|&nbsp; <span class="vc-label">Transcriptional:</span> ' + esc(v.transcriptional_probability || '') +
            '</div>' +
            '<p class="vc-note">' + esc(v.assessment || '') + '</p></div>';
        }).join('');
        var vrEl  = document.getElementById('variant-body');
        var vrSec = document.getElementById('variant-section');
        if (vrEl) vrEl.innerHTML = vrHtml;
        if (vrSec) { vrSec.style.display = ''; staggerReveal(vrSec, 0); }
      }
    }

    if (key === 'disputed_passage') {
      if (data) {
        var dpHtml =
          '<div class="disputed-designation">' + esc(data.designation || '') + '</div>' +
          '<div class="dp-row"><strong>Evidence for inclusion:</strong> ' + esc(data.manuscript_evidence_for || '') + '</div>' +
          '<div class="dp-row"><strong>Evidence against:</strong> ' + esc(data.manuscript_evidence_against || '') + '</div>' +
          '<div class="dp-row"><strong>Internal evidence:</strong> ' + esc(data.internal_evidence || '') + '</div>' +
          '<div class="dp-row"><strong>Scholarly consensus:</strong> ' + esc(data.scholarly_consensus || '') + '</div>' +
          '<div class="dp-row"><strong>In major translations:</strong> ' + esc(data.pastoral_note || '') + '</div>';
        var dpEl  = document.getElementById('disputed-body');
        var dpSec = document.getElementById('disputed-section');
        if (dpEl) dpEl.innerHTML = dpHtml;
        if (dpSec) { dpSec.style.display = ''; staggerReveal(dpSec, 0); }
      }
    }

    if (key === 'synthesis') {
      var synText = typeof data === 'string' ? data : (data && (data.synthesis || data.plain || ''));
      var synEl  = document.getElementById('synthesis-body');
      var synSec = document.getElementById('synthesis-section');
      if (synEl) synEl.textContent = synText || '';
      if (synSec && synText) { synSec.style.display = ''; staggerReveal(synSec, 0); }
    }

    if (key === 'assessment') {
      var a = data || {};
      var aHtml = '';
      if (a.title)    aHtml += '<h3 class="bc-title">' + esc(a.title) + '</h3>';
      if (a.plain)    aHtml += '<p class="bc-plain">' + esc(a.plain) + '</p>';
      if (a.reasoning) aHtml += '<p>' + esc(a.reasoning) + '</p>';
      if (a.recommended_reading) aHtml += '<p><strong>Recommended edition:</strong> ' + esc(a.recommended_reading) + '</p>';
      if (a.open_questions) aHtml += '<p><strong>Open questions:</strong> ' + esc(a.open_questions) + '</p>';
      if (typeof a.confidence === 'number') {
        aHtml += '<div class="confidence-bar"><div class="confidence-fill" style="width:' + (a.confidence * 100).toFixed(0) + '%"></div></div>';
      }
      var bibBodyEl = document.getElementById('bibcrit-body');
      var bibSecEl  = document.getElementById('bibcrit-assessment');
      if (bibBodyEl) bibBodyEl.innerHTML = aHtml;
      if (bibSecEl)  { bibSecEl.style.display = ''; staggerReveal(bibSecEl, 0); }
    }
  }

  function _finalize(data) {
    _partialData = Object.assign(_partialData, data || {});
    _hideCompactSpinner();
    renderResult(_partialData);
  }

  function analyze(ref) {
    _currentRef      = ref;
    _finalHandled    = false;
    _partialData     = {};
    _sectionReceived = false;

    if (emptyState) emptyState.style.display = 'none';

    // Compact spinner strip at top
    if (_timer) clearInterval(_timer);
    if (loadState) {
      loadState.classList.add('is-compact');
      loadState.style.display = 'block';
    }
    if (loadStep) loadStep.textContent = window.t ? window.t('step_generating', 'Analyzing \u2014 this may take 40\u201360 seconds\u2026') : 'Analyzing \u2014 this may take 40\u201360 seconds\u2026';
    if (loadTimer) {
      var s = 0; loadTimer.textContent = '';
      _timer = setInterval(function () { loadTimer.textContent = (++s) + 's'; }, 1000);
    }

    // Show heading and results immediately
    if (heading) {
      heading.innerHTML = '<span class="ph-ref">' + ref + '</span>';
      heading.style.display = '';
    }
    if (results) results.style.display = 'block';

    // Hide non-skeleton sections
    ['variant-section', 'disputed-section', 'bibcrit-assessment', 'export-row'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });

    _renderSkeleton();

    var lang = new URLSearchParams(window.location.search).get('lang') || 'en';
    var url  = '/api/nt-text/stream?ref=' + encodeURIComponent(ref) + '&lang=' + lang;
    var es   = new EventSource(url);

    es.onmessage = function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          if (loadStep) loadStep.textContent = msg.msg;
        } else if (msg.type === 'section') {
          _renderSection(msg.key, msg.data);
        } else if (msg.type === 'done') {
          _finalHandled = true;
          es.close();
          if (_sectionReceived) {
            _finalize(msg.data);
          } else {
            _hideCompactSpinner();
            renderResult(msg.data);
          }
        } else if (msg.type === 'error') {
          _finalHandled = true;
          es.close(); _hideCompactSpinner(); showToast(msg.msg || 'Error', 5000);
        }
      } catch (_) {}
    };

    es.onerror = function () {
      if (_finalHandled) return;
      es.close(); _hideCompactSpinner();
      showToast(window.t ? window.t('err_connection', 'Connection error') : 'Connection error', 5000);
    };
  }

  window.ntText = { analyze: analyze };
}());
