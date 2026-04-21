/* BibCrit — Second Temple Literature Bridge */

(function () {
  'use strict';

  // All OT + NT books (STL bridge applies to the full canon)
  var _ALL_BOOKS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36, 'Deuteronomy': 34,
    'Joshua': 24, 'Judges': 21, 'Ruth': 4, '1 Samuel': 31, '2 Samuel': 24,
    '1 Kings': 22, '2 Kings': 25, '1 Chronicles': 29, '2 Chronicles': 36,
    'Ezra': 10, 'Nehemiah': 13, 'Esther': 10, 'Job': 42, 'Psalms': 150,
    'Proverbs': 31, 'Ecclesiastes': 12, 'Song of Songs': 8, 'Isaiah': 66,
    'Jeremiah': 52, 'Lamentations': 5, 'Ezekiel': 48, 'Daniel': 12,
    'Hosea': 14, 'Joel': 3, 'Amos': 9, 'Obadiah': 1, 'Jonah': 4,
    'Micah': 7, 'Nahum': 3, 'Habakkuk': 3, 'Zephaniah': 3, 'Haggai': 2,
    'Zechariah': 14, 'Malachi': 4,
    'Matthew': 28, 'Mark': 16, 'Luke': 24, 'John': 21, 'Acts': 28,
    'Romans': 16, '1 Corinthians': 16, '2 Corinthians': 13, 'Galatians': 6,
    'Ephesians': 6, 'Philippians': 4, 'Colossians': 4,
    '1 Thessalonians': 5, '2 Thessalonians': 3, '1 Timothy': 6, '2 Timothy': 4,
    'Titus': 3, 'Philemon': 1, 'Hebrews': 13, 'James': 5,
    '1 Peter': 5, '2 Peter': 3, '1 John': 5, '2 John': 1, '3 John': 1,
    'Jude': 1, 'Revelation': 22,
  };

  // STL work display names
  var _WORK_LABELS = {
    '1_enoch':  '1 Enoch',
    'jubilees': 'Jubilees',
    'sirach':   'Sirach',
    '4_ezra':   '4 Ezra',
    'tobit':    'Tobit',
  };

  // Allusion type badge colours
  var _TYPE_COLORS = {
    'citation': '#15803d',
    'allusion': '#1d4ed8',
    'echo':     '#7c3aed',
    'parallel': '#b45309',
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
  var results    = document.getElementById('stl-results');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  var _timer = null;
  var _currentRef = '';
  var _finalHandled   = false;
  var _partialData    = {};
  var _sectionReceived = false;

  // Populate book dropdown
  if (selBook) {
    Object.keys(_ALL_BOOKS).forEach(function (b) {
      var opt = document.createElement('option');
      opt.value = b; opt.textContent = b;
      selBook.appendChild(opt);
    });
  }

  function _resetSelect(el, placeholder) {
    while (el.options.length > 1) el.remove(1);
    el.options[0].text = placeholder;
    el.disabled = true;
    el.value = '';
  }

  if (selBook) {
    selBook.addEventListener('change', function () {
      var book = this.value;
      _resetSelect(selChapter, 'Ch\u2026');
      _resetSelect(selVerse, 'Vs\u2026');
      if (!book) return;
      var numCh = _ALL_BOOKS[book] || 0;
      for (var i = 1; i <= numCh; i++) {
        var opt = document.createElement('option');
        opt.value = i; opt.textContent = i;
        selChapter.appendChild(opt);
      }
      selChapter.disabled = false;
    });
  }

  if (selChapter) {
    selChapter.addEventListener('change', function () {
      _resetSelect(selVerse, 'Vs\u2026');
      for (var v = 1; v <= 30; v++) {
        var opt = document.createElement('option');
        opt.value = v; opt.textContent = v;
        selVerse.appendChild(opt);
      }
      selVerse.disabled = false;
    });
  }

  if (selVerse) {
    selVerse.addEventListener('change', function () {
      if (selBook.value && selChapter.value && this.value) {
        refInput.value = selBook.value + ' ' + selChapter.value + ':' + this.value;
      }
    });
  }

  // Featured passage links
  document.querySelectorAll('.featured-ref').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.dataset.ref;
      if (ref) { refInput.value = ref; analyze(ref); }
    });
  });

  btnAnalyze.addEventListener('click', function () {
    var ref = refInput.value.trim();
    if (!ref) { showToast('Enter a passage reference first'); return; }
    analyze(ref);
  });

  refInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { var ref = this.value.trim(); if (ref) analyze(ref); }
  });

  // ── Helpers ───────────────────────────────────────────────────────────────

  function esc(s) {
    return String(s || '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function setText(id, html) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function showSection(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = '';
  }

  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(function () { toast.style.display = 'none'; }, 3000);
  }

  function staggerReveal(el, delay) {
    if (!el) return;
    el.style.opacity = '0';
    el.style.transform = 'translateY(8px)';
    el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    setTimeout(function () {
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }, delay || 0);
  }

  function _skelRows(n, widths) {
    return (widths || Array(n).fill(80)).map(function (w) {
      return '<div class="dss-skel-row" style="width:' + w + '%"></div>';
    }).join('');
  }

  // ── Skeleton ──────────────────────────────────────────────────────────────

  function _renderSkeleton() {
    var synthSec  = document.getElementById('synthesis-section');
    var synthBody = document.getElementById('synthesis-body');
    if (synthSec && synthBody) {
      synthBody.innerHTML = _skelRows(3, [100, 85, 70]);
      synthSec.style.display = '';
    }
    var allusionSec  = document.getElementById('allusions-section');
    var allusionBody = document.getElementById('allusions-body');
    if (allusionSec && allusionBody) {
      allusionBody.innerHTML = _skelRows(4, [100, 90, 80, 95]);
      allusionSec.style.display = '';
    }
  }

  // ── Progressive section rendering ─────────────────────────────────────────

  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived  = true;

    if (emptyState) emptyState.style.display = 'none';

    if (key === '_corpus') {
      // MT/LXX context texts — stored in _partialData for export access only
      return;
    }

    if (key === 'synthesis') {
      setText('synthesis-body', '<p>' + esc(String(data || '')) + '</p>');
      showSection('synthesis-section');
      staggerReveal(document.getElementById('synthesis-section'), 0);
    }

    if (key === 'allusions') {
      var allusions = Array.isArray(data) ? data : [];
      if (allusions.length === 0) {
        setText('allusions-body', '<p class="vc-note">No direct STL allusions identified for this passage.</p>');
      } else {
        var html = allusions.map(function (a) {
          var typeColor = _TYPE_COLORS[a.allusion_type] || '#374151';
          var workLabel = _WORK_LABELS[a.stl_work] || esc(a.stl_work || '');
          var confPct   = Math.round((a.confidence || 0) * 100);
          return (
            '<div class="variant-card stl-allusion-card">' +
              '<div class="stl-card-head">' +
                '<span class="stl-work-badge">' + workLabel + '</span>' +
                '<span class="stl-passage-ref">' + esc(a.stl_passage || '') + '</span>' +
                '<span class="badge" style="background:' + typeColor + ';color:#fff;margin-left:auto">' +
                  esc(a.allusion_type || '') +
                '</span>' +
              '</div>' +
              '<p class="vc-note stl-content">' + esc(a.stl_content || '') + '</p>' +
              '<div class="stl-canonical-elem"><strong>Canonical element:</strong> ' + esc(a.canonical_element || '') + '</div>' +
              '<p class="vc-note">' + esc(a.scholarly_note || '') + '</p>' +
              '<div class="stl-meta-row">' +
                '<span class="stl-dir-badge">→ ' + esc((a.directionality || '').replace(/_/g,' ')) + '</span>' +
                '<div class="confidence-bar" title="Confidence: ' + confPct + '%">' +
                  '<div class="confidence-fill" style="width:' + confPct + '%"></div>' +
                '</div>' +
              '</div>' +
              (a.relevance_to_dss ? '<p class="stl-dss-note">🗝 DSS: ' + esc(a.relevance_to_dss) + '</p>' : '') +
              (a.relevance_to_nt  ? '<p class="stl-nt-note">📖 NT: '  + esc(a.relevance_to_nt)  + '</p>' : '') +
            '</div>'
          );
        }).join('');
        setText('allusions-body', html);
      }
      showSection('allusions-section');
      staggerReveal(document.getElementById('allusions-section'), 0);
    }

    if (key === 'works_covered') {
      var works = data || {};
      var bars = Object.keys(_WORK_LABELS).map(function (slug) {
        var info  = works[slug] || { present: false, passage_count: 0 };
        var label = _WORK_LABELS[slug];
        var count = info.passage_count || 0;
        return (
          '<div class="stl-work-row">' +
            '<span class="stl-work-name">' + label + '</span>' +
            (info.present
              ? '<span class="stl-work-count stl-work-present">' + count + ' passage' + (count !== 1 ? 's' : '') + '</span>'
              : '<span class="stl-work-count stl-work-absent">–</span>'
            ) +
          '</div>'
        );
      }).join('');
      setText('works-body', '<div class="stl-works-grid">' + bars + '</div>');
      showSection('works-section');
      staggerReveal(document.getElementById('works-section'), 0);
    }

    if (key === 'dss_significance') {
      if (data) {
        setText('dss-sig-body', '<p>' + esc(String(data)) + '</p>');
        showSection('dss-sig-section');
        staggerReveal(document.getElementById('dss-sig-section'), 0);
      }
    }

    if (key === 'nt_significance') {
      if (data) {
        setText('nt-sig-body', '<p>' + esc(String(data)) + '</p>');
        showSection('nt-sig-section');
        staggerReveal(document.getElementById('nt-sig-section'), 0);
      }
    }

    if (key === 'directionality_summary') {
      if (data) {
        setText('dir-body', '<p>' + esc(String(data)) + '</p>');
        showSection('dir-section');
        staggerReveal(document.getElementById('dir-section'), 0);
      }
    }

    if (key === 'assessment') {
      var a = data || {};
      var aHtml = '';
      if (a.title)      aHtml += '<h3 class="bc-title">' + esc(a.title) + '</h3>';
      if (a.plain)      aHtml += '<p class="bc-plain">' + esc(a.plain) + '</p>';
      if (a.reasoning)  aHtml += '<p>' + esc(a.reasoning) + '</p>';
      if (a.next_steps) aHtml += '<p><strong>Next steps:</strong> ' + esc(a.next_steps) + '</p>';
      if (typeof a.confidence === 'number') {
        aHtml += '<div class="confidence-bar"><div class="confidence-fill" style="width:' +
                 (a.confidence * 100).toFixed(0) + '%"></div></div>';
      }
      var bibSecEl  = document.getElementById('bibcrit-assessment');
      var bibBodyEl = document.getElementById('bibcrit-body');
      if (bibBodyEl) bibBodyEl.innerHTML = aHtml;
      if (bibSecEl)  bibSecEl.style.display = '';
      if (bibSecEl)  staggerReveal(bibSecEl, 0);
    }
  }

  // ── Full render (cache hit or done) ──────────────────────────────────────

  function renderResult(data) {
    ['synthesis','allusions','works_covered','dss_significance',
     'nt_significance','directionality_summary','assessment'].forEach(function (k) {
      if (k in data) _renderSection(k, data[k]);
    });

    // Export row
    var expRow = document.getElementById('export-row');
    if (expRow && (data.citations || {}).sbl) expRow.style.display = '';

    // Copy buttons
    var btnSbl = document.getElementById('btn-sbl');
    if (btnSbl && data.citations && data.citations.sbl) {
      btnSbl.onclick = function () {
        navigator.clipboard.writeText(data.citations.sbl).then(function () {
          showToast('SBL footnote copied!');
        });
      };
    }
    var btnBibtex = document.getElementById('btn-bibtex');
    if (btnBibtex && data.citations && data.citations.bibtex) {
      btnBibtex.onclick = function () {
        navigator.clipboard.writeText(data.citations.bibtex).then(function () {
          showToast('BibTeX copied!');
        });
      };
    }

    // Share button
    var btnShare = document.getElementById('btn-share');
    if (btnShare) {
      btnShare.onclick = function () {
        var url = window.location.origin + '/stl?ref=' + encodeURIComponent(_currentRef);
        navigator.clipboard.writeText(url).then(function () { showToast('Link copied!'); });
      };
    }
  }

  function _hideCompactSpinner() {
    if (loadState) { loadState.classList.remove('is-compact'); loadState.style.display = 'none'; }
    if (_timer) { clearInterval(_timer); _timer = null; }
    if (loadTimer) loadTimer.textContent = '';
  }

  function _finalize(data) {
    _partialData = Object.assign(_partialData, data || {});
    _hideCompactSpinner();
    renderResult(_partialData);
  }

  // ── Main analyze function ─────────────────────────────────────────────────

  function analyze(ref) {
    _currentRef      = ref;
    _finalHandled    = false;
    _partialData     = {};
    _sectionReceived = false;

    if (emptyState) emptyState.style.display = 'none';
    if (results)    results.style.display    = 'block';

    // Reset all sections
    ['synthesis-section','allusions-section','works-section',
     'dss-sig-section','nt-sig-section','dir-section',
     'bibcrit-assessment','export-row'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });

    if (loadState) {
      loadState.classList.add('is-compact');
      loadState.style.display = 'block';
    }
    if (loadStep) loadStep.textContent = 'Analyzing \u2014 this may take 40\u201360 seconds\u2026';
    if (_timer) clearInterval(_timer);

    // Timer
    var elapsed = 0;
    _timer = setInterval(function () {
      elapsed++;
      if (loadTimer) loadTimer.textContent = elapsed + 's';
    }, 1000);

    if (heading) {
      heading.textContent = ref;
      heading.style.display = '';
    }

    _renderSkeleton();

    // Update URL without reload
    if (window.history && window.history.replaceState) {
      var newUrl = window.location.pathname + '?ref=' + encodeURIComponent(ref);
      window.history.replaceState(null, '', newUrl);
    }

    // Language
    var lang = new URLSearchParams(window.location.search).get('lang') || 'en';
    var url  = '/api/stl/stream?ref=' + encodeURIComponent(ref) + '&lang=' + encodeURIComponent(lang);

    var es = new EventSource(url);

    es.onmessage = function (e) {
      var msg;
      try { msg = JSON.parse(e.data); } catch (_) { return; }

      if (msg.type === 'step') {
        if (loadStep) loadStep.textContent = msg.msg || '';
      } else if (msg.type === 'section') {
        if (loadState) loadState.classList.add('is-compact');
        _renderSection(msg.key, msg.data);
      } else if (msg.type === 'done') {
        if (!_finalHandled) {
          _finalHandled = true;
          es.close();
          _finalize(msg.data);
        }
      } else if (msg.type === 'error') {
        es.close();
        _hideCompactSpinner();
        if (results) results.style.display = 'none';
        if (emptyState) emptyState.style.display = '';
        showToast(msg.msg || 'Analysis error');
      }
    };

    es.onerror = function () {
      if (!_finalHandled) {
        es.close();
        _hideCompactSpinner();
        showToast('Connection error — please try again');
      }
    };
  }

  // Expose for auto-trigger in template
  window.stl = { analyze: analyze };

})();
