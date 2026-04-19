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

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
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
      var families = ['alexandrian', 'western', 'byzantine', 'caesarean'];
      families.forEach(function (f) {
        var fm = data.manuscript_families[f];
        if (!fm) return;
        var supportClass = 'support-' + (fm.support || 'unknown').replace(/_/g, '-');
        mfHtml += '<div class="ms-family-row">' +
          '<span class="ms-family-name">' + esc(f.charAt(0).toUpperCase() + f.slice(1)) + '</span>' +
          '<span class="ms-family-witnesses">' + esc((fm.witnesses || []).join(', ')) + '</span>' +
          '<span class="ms-support ' + supportClass + '">' + esc(fm.support || '') + '</span>' +
          '<p class="ms-family-note">' + esc(fm.note || '') + '</p></div>';
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
      btnSbl.onclick = function () { navigator.clipboard.writeText(data.citations.sbl); showToast('SBL copied!'); };
    }
    if (btnBibtex && data.citations && data.citations.bibtex) {
      btnBibtex.onclick = function () { navigator.clipboard.writeText(data.citations.bibtex); showToast('BibTeX copied!'); };
    }
    if (btnShare) {
      btnShare.onclick = function () {
        var url = window.location.origin + '/nt-text?ref=' + encodeURIComponent(_currentRef);
        navigator.clipboard.writeText(url); showToast('Link copied!');
      };
    }
  }

  function analyze(ref) {
    _currentRef = ref;
    setLoading(true);
    if (loadStep) loadStep.textContent = window.t ? window.t('loading_preparing', 'Preparing\u2026') : 'Preparing\u2026';

    // Hide all result sections
    ['gnt-text-display', 'metzger-section', 'ms-families-section', 'variant-section',
     'disputed-section', 'synthesis-section', 'bibcrit-assessment', 'export-row'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });

    var lang = new URLSearchParams(window.location.search).get('lang') || 'en';
    var url  = '/api/nt-text/stream?ref=' + encodeURIComponent(ref) + '&lang=' + lang;
    var es   = new EventSource(url);

    es.onmessage = function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          if (loadStep) loadStep.textContent = msg.msg;
        } else if (msg.type === 'done') {
          es.close(); renderResult(msg.data);
        } else if (msg.type === 'error') {
          es.close(); setLoading(false); showToast(msg.msg || 'Error', 5000);
        }
      } catch (_) {}
    };

    es.onerror = function () {
      es.close(); setLoading(false);
      showToast(window.t ? window.t('err_connection', 'Connection error') : 'Connection error', 5000);
    };
  }

  window.ntText = { analyze: analyze };
}());
