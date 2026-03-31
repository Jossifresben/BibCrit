/* BibCrit — DSS Bridge Tool */

(function () {
  'use strict';

  var selBook    = document.getElementById('sel-book');
  var selChapter = document.getElementById('sel-chapter');
  var selVerse   = document.getElementById('sel-verse');
  var refInput   = document.getElementById('ref-input');
  var btnAnalyze = document.getElementById('btn-analyze');
  var infoBanner = document.getElementById('dss-info-banner');
  var infoClose  = document.getElementById('dss-info-close');
  var emptyState = document.getElementById('empty-state');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var results    = document.getElementById('dss-results');
  var msList     = document.getElementById('manuscript-list');
  var synthSec   = document.getElementById('synthesis-section');
  var synthBody  = document.getElementById('synthesis-body');
  var bibSec     = document.getElementById('bibcrit-assessment');
  var bibBody    = document.getElementById('bibcrit-body');
  var exportRow  = document.getElementById('export-row');
  var btnShare   = document.getElementById('btn-share');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  // ── Info banner dismiss ─────────────────────────────────────────────────
  var _BANNER_VER = 'dss-info-v1';
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
  var _lastData     = null;

  // ── DSS coverage: books and chapters with known DSS witnesses ─────────
  // Chapters listed are those with at least one attested DSS fragment.
  var _DSS_COVERAGE = {
    // Torah — substantial coverage across multiple 4Q/1Q manuscripts
    'Genesis':      [1,2,3,4,5,6,7,8,9,10,11,12,17,18,19,22,24,25,26,27,28,29,30,31,32,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50],
    'Exodus':       [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40],
    'Leviticus':    [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27],
    'Numbers':      [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36],
    'Deuteronomy':  [1,2,4,5,6,7,8,9,10,11,12,13,14,17,20,22,23,24,25,26,27,28,29,30,31,32,33,34],
    // Former Prophets — fragmentary
    'Joshua':       [2,3,4,5,6,7,8,10,17],
    'Judges':       [6,8,9,19,21],
    'Ruth':         [1,2,3,4],
    '1 Samuel':     [1,2,16,18,19,21,23,25],
    '2 Samuel':     [2,5,6,14,15,16,22,23],
    '1 Kings':      [7,8,12,22],
    '2 Kings':      [5,6,7,19,23],
    // Latter Prophets — 1QIsa-a is nearly complete for Isaiah
    'Isaiah':       (function(){var a=[];for(var i=1;i<=66;i++)a.push(i);return a;}()),
    'Jeremiah':     [7,8,9,10,12,15,17,19,22,25,26,27,28,29,30,31,32,33,43,44,46,47,48,49,50,51],
    'Ezekiel':      [1,4,5,7,10,11,13,16,23,24,41],
    // Minor Prophets (Nahal Hever scroll and Qumran fragments)
    'Hosea':        [1,2,3,4,5,6,7,8,9,10,11,12,13,14],
    'Joel':         [1,2,3],
    'Amos':         [1,2,3,4,5,6,7,8,9],
    'Jonah':        [1,2,3,4],
    'Micah':        [1,2,3,4,5,6,7],
    'Nahum':        [1,2,3],
    'Habakkuk':     [1,2,3],
    'Zephaniah':    [1,2,3],
    'Haggai':       [1,2],
    'Zechariah':    [1,2,3,4,5,6,7,8,9,10,11,12,13,14],
    'Malachi':      [1,2,3,4],
    // Writings
    'Psalms':       [1,2,5,6,7,8,9,11,12,13,14,15,16,17,18,19,22,23,24,25,26,27,28,29,30,31,32,33,35,37,38,39,40,41,45,49,51,52,53,54,56,57,59,62,63,66,67,68,69,71,77,78,81,86,88,89,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,109,112,113,114,116,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,138,139,141,143,144,145,146,147,148,149,150],
    'Proverbs':     [1,2,3,4,5,6,7,8,9,12,13,14,15],
    'Job':          [3,4,8,9,13,14,17,19,21,26,27,28,31,33,35,36,37,38,39,40,41,42],
    'Song of Songs':[1,2,3,4,5,6,7,8],
    'Lamentations': [1,2,3,4,5],
    'Ecclesiastes': [1,2,3,4,5,6,7,8,9,10,11,12],
    'Ezra':         [4,5,6],
    'Daniel':       [1,2,3,4,5,6,7,8,9,10,11,12],
    '1 Chronicles': [26,27,28,29],
    '2 Chronicles': [27,28,29,32,33,34,35],
  };

  // ── Standard verse counts per chapter (MT/Protestant versification) ────
  var _VERSE_COUNTS = {
    'Genesis':      [31,25,24,26,32,22,24,22,29,32,32,20,18,24,21,16,27,33,38,18,34,24,20,67,34,35,46,22,35,43,55,32,20,31,29,43,36,30,23,23,57,38,34,34,28,34,31,22,33,26],
    'Exodus':       [22,25,22,31,23,30,25,32,35,29,10,51,22,31,27,36,16,27,25,26,36,31,33,18,40,37,21,43,46,38,18,35,23,35,35,38,29,31,43,38],
    'Leviticus':    [17,16,17,35,19,30,38,36,24,20,47,8,59,57,33,34,16,30,24,33,3,17,17,10,22,21,28],
    'Numbers':      [54,34,51,49,31,27,89,26,23,36,35,16,33,45,41,50,13,32,22,29,35,41,30,25,18,65,23,31,40,16,54,42,56,29,34,13],
    'Deuteronomy':  [46,37,29,49,33,25,26,20,29,22,32,32,18,29,23,22,20,22,21,20,23,30,25,22,19,19,26,68,29,20,30,52,29,12],
    'Joshua':       [18,24,17,24,15,27,26,35,27,43,23,24,33,15,63,10,18,28,51,9,45,34,16,33],
    'Judges':       [36,23,31,24,31,40,25,35,57,18,40,15,25,20,20,31,13,31,30,48,25],
    'Ruth':         [22,23,18,22],
    '1 Samuel':     [28,36,21,22,12,21,17,22,27,27,15,25,23,52,35,23,58,30,24,42,15,23,29,22,44,25,12,25,11,31,13],
    '2 Samuel':     [27,32,39,12,25,23,29,18,13,19,27,31,39,33,37,23,29,33,43,26,22,51,39,25],
    '1 Kings':      [53,46,28,34,18,38,51,66,28,29,43,33,34,31,34,34,24,46,21,43,29,53],
    '2 Kings':      [18,25,27,44,27,33,20,29,37,36,21,21,25,29,38,20,41,37,37,21,26,20,37,20,30],
    'Isaiah':       [31,22,26,6,30,13,25,22,21,34,16,6,22,32,9,14,14,7,25,6,17,25,18,23,12,21,13,29,24,33,9,20,24,17,10,22,38,22,8,31,29,25,28,28,25,13,15,22,26,11,23,15,12,17,13,12,21,14,21,22,11,12,19,12,25,24],
    'Jeremiah':     [19,37,25,31,31,30,34,22,26,25,23,17,27,22,21,21,27,23,15,18,14,30,40,10,38,24,22,17,32,24,40,44,26,22,19,32,21,28,18,16,18,22,13,30,5,28,7,47,39,46,64,34],
    'Ezekiel':      [28,10,27,21,45,13,12,20,72,30,23,16,20,28,26,16,24,22,26,15,24,22,23,17,17,14,29,35,11,24,17,21,26,17,22,19,30,19,26,28,20,28,18,39,40,34,16,34],
    'Hosea':        [11,23,5,19,15,11,16,14,17,15,12,14,16,9],
    'Joel':         [20,32,21],
    'Amos':         [15,16,15,13,27,14,17,14,15],
    'Jonah':        [17,10,10,11],
    'Micah':        [16,13,12,13,15,16,20],
    'Nahum':        [15,13,19],
    'Habakkuk':     [17,20,19],
    'Zephaniah':    [18,15,20],
    'Haggai':       [15,23],
    'Zechariah':    [21,13,10,14,11,15,14,23,17,12,17,14,9,21],
    'Malachi':      [14,17,18,6],
    'Psalms':       [6,12,8,8,12,10,17,9,20,18,7,8,6,7,5,11,15,50,14,9,13,31,6,10,22,12,14,9,11,12,24,11,22,22,28,12,40,22,13,17,13,11,5,26,17,11,9,14,20,23,19,9,6,7,23,13,11,11,17,12,8,12,11,10,13,20,7,35,36,5,24,20,28,23,10,12,20,72,13,19,16,8,18,12,13,17,7,18,52,17,16,15,5,23,11,13,12,9,9,5,8,28,22,35,45,48,43,13,31,7,10,10,9,8,18,19,2,29,176,7,8,9,4,8,5,6,5,8,8,3,18,3,3,21,26,9,8,24,14,10,8,12,15,21,10,20,14,9,6],
    'Proverbs':     [33,22,35,27,23,35,27,36,18,32,31,28,25,35,33,33,28,24,29,30,31,29,35,34,28,28,27,28,27,33,31],
    'Job':          [22,17,16,21,17,21,11,16,22,16,16,13,17,19,14,14,19,34,19,15,22,18,20,23,20,18,21,14,21,20,25,31,31,30,31,24,26,20,25,25,22,23],
    'Song of Songs':[17,17,11,16,16,13,13,14],
    'Lamentations': [22,22,66,22,22],
    'Ecclesiastes': [18,26,22,16,20,12,29,17,18,20,10,14],
    'Ezra':         [11,70,13,24,17,22,28,36,15,44],
    'Daniel':       [21,49,30,37,31,28,28,27,27,21,45,13],
    '1 Chronicles': [54,55,24,43,26,81,40,40,44,14,47,40,14,17,29,43,27,17,19,8,30,19,32,31,31,32,34,21,30],
    '2 Chronicles': [17,18,17,22,14,42,22,18,31,19,23,16,22,15,19,14,19,34,11,37,20,12,21,27,28,23,9,27,36,27,21,33,25,33,27,23],
  };

  // ── Book/Chapter/Verse cascade (uses hardcoded DSS data, no corpus API) ─
  if (selBook) {
    Object.keys(_DSS_COVERAGE).forEach(function (b) {
      var opt = document.createElement('option');
      opt.value = b; opt.textContent = b;
      selBook.appendChild(opt);
    });
  }

  if (selBook) {
    selBook.addEventListener('change', function () {
      var book = this.value;
      _resetSelect(selChapter, 'Ch…');
      _resetSelect(selVerse, 'Vs…');
      if (!book) return;
      var chapters = _DSS_COVERAGE[book] || [];
      chapters.forEach(function (ch) {
        var opt = document.createElement('option');
        opt.value = ch; opt.textContent = ch;
        selChapter.appendChild(opt);
      });
      if (chapters.length) selChapter.disabled = false;
    });
  }

  if (selChapter) {
    selChapter.addEventListener('change', function () {
      var book = selBook ? selBook.value : '';
      var ch   = parseInt(this.value, 10);
      _resetSelect(selVerse, 'Vs…');
      if (!book || !ch) return;
      var counts = _VERSE_COUNTS[book] || [];
      var total  = counts[ch - 1] || 30;
      for (var v = 1; v <= total; v++) {
        var opt = document.createElement('option');
        opt.value = v; opt.textContent = v;
        selVerse.appendChild(opt);
      }
      selVerse.disabled = false;
    });
  }

  function _resetSelect(sel, placeholder) {
    if (!sel) return;
    sel.innerHTML = '<option value="">' + placeholder + '</option>';
    sel.disabled = true;
  }

  function _buildRefFromSelectors() {
    var book = selBook ? selBook.value : '';
    var ch   = selChapter ? selChapter.value : '';
    var vs   = selVerse ? selVerse.value : '';
    if (book && ch && vs) return book + ' ' + ch + ':' + vs;
    if (book && ch)       return book + ' ' + ch;
    return '';
  }

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
    var ref = (refInput ? refInput.value.trim() : '') || _buildRefFromSelectors();
    if (!ref) { showToast(window.t('err_enter_passage', 'Please enter or select a passage.')); return; }
    analyze(ref);
  });

  if (refInput) {
    refInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') btnAnalyze.click();
    });
  }

  // ── Core analyze ────────────────────────────────────────────────────────
  function analyze(ref) {
    if (!ref) return;
    _currentRef = ref;

    if (_es) { _es.close(); _es = null; }
    clearInterval(_timer);
    _finalHandled = false;

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

    history.replaceState(null, '', '/dss?ref=' + encodeURIComponent(ref));

    _es = new EventSource('/api/dss/stream?ref=' + encodeURIComponent(ref) + '&lang=' + (window.bibcritLang || 'en'));

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
          renderDSS(msg.data);
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
  function renderDSS(data) {
    _lastData = data;
    hide(loadState);

    show(heading);
    heading.innerHTML = '<span class="ph-ref">' + _esc(data.reference || _currentRef) + '</span>';

    // Manuscript cards — extant first, absent last
    if (msList) msList.innerHTML = '';
    var manuscripts = (data.dss_manuscripts || []).slice().sort(function (a, b) {
      var aExtant = (a.verse_present && a.alignment !== 'absent') ? 0 : 1;
      var bExtant = (b.verse_present && b.alignment !== 'absent') ? 0 : 1;
      return aExtant - bExtant;
    });

    manuscripts.forEach(function (ms, idx) {
      var card = _buildManuscriptCard(ms, idx);
      if (msList) msList.appendChild(card);
    });

    if (!manuscripts.length) {
      if (msList) msList.innerHTML =
        '<div class="bt-group-card" style="max-width:900px;margin:0 auto 1rem;text-align:center;padding:2rem 1.5rem">' +
          '<span class="material-symbols-outlined" style="font-size:2.5rem;color:var(--muted);display:block;margin-bottom:0.75rem">hide_source</span>' +
          '<p style="font-weight:600;margin:0 0 0.4rem;font-size:1rem">No DSS Witness Found</p>' +
          '<p style="color:var(--muted);margin:0;font-size:0.875rem">No Dead Sea Scrolls manuscript attests this passage. ' +
          'The passage may fall in a lacuna, or no scroll preserving this section has been identified.</p>' +
        '</div>';
    }

    // Synthesis
    var synth = data.synthesis_plain || data.synthesis || '';
    if (synth && synthSec && synthBody) {
      synthBody.innerHTML =
        '<div class="bt-group-card">' +
          '<p class="div-analysis">' + _esc(synth) + '</p>' +
          (data.synthesis && data.synthesis !== synth
            ? '<p class="div-meta" style="margin-top:8px;font-style:italic">' + _esc(data.synthesis) + '</p>'
            : '') +
          (data.textual_history_implication
            ? '<p style="margin-top:8px;font-size:0.875rem;color:var(--fg)">' + _esc(data.textual_history_implication) + '</p>'
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
        toolName: 'dss',
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
          fetch('/api/export/sbl?tool=dss&ref=' + encodeURIComponent(_currentRef))
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
          fetch('/api/export/bibtex?tool=dss&ref=' + encodeURIComponent(_currentRef))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              navigator.clipboard.writeText(d.bibtex || '').catch(function(){});
              showToast(window.t('toast_bibtex_copied_short', 'BibTeX copied!'));
            }).catch(function(){});
        });
      }
    }
  }

  function _buildManuscriptCard(ms, idx) {
    var card = document.createElement('div');
    card.className = 'dss-ms-card';
    card.style.maxWidth = '900px';
    card.style.margin = '0 auto 1rem';

    var alignment = ms.alignment || 'absent';
    var present   = ms.verse_present;
    var conf      = ms.alignment_confidence || 0;
    var pct       = Math.round(conf * 100);
    var confCls   = conf >= 0.75 ? 'badge-high' : conf >= 0.45 ? 'badge-medium' : 'badge-low';

    var header = document.createElement('div');
    header.className = 'dss-ms-header';
    header.setAttribute('role', 'button');
    header.setAttribute('aria-expanded', idx === 0 ? 'true' : 'false');
    header.innerHTML =
      '<span class="dss-ms-siglum">' + _esc(ms.siglum || '') + '</span>' +
      '<span class="dss-ms-fullname">' + _esc(ms.full_name || '') + '</span>' +
      _alignmentBadge(alignment) +
      (present && conf ? '<span class="conf-badge ' + confCls + '" style="margin-left:4px">' + pct + '%</span>' : '') +
      '<span class="dss-ms-toggle">' + (idx === 0 ? '▲' : '▼') + '</span>';

    var body = document.createElement('div');
    body.className = 'dss-ms-body' + (idx === 0 ? '' : ' collapsed');

    if (!present || alignment === 'absent') {
      body.innerHTML = '<p class="dss-absent-note">This passage is not extant in ' + _esc(ms.siglum || 'this manuscript') + '.</p>';
    } else {
      var inner = '';
      if (ms.dss_text) {
        inner += '<div class="dss-ms-text">' + _esc(ms.dss_text) + '</div>';
      }

      var divs = ms.divergences || [];
      if (divs.length) {
        inner +=
          '<table class="dss-div-table"><thead><tr>' +
          '<th>#</th><th>MT</th><th>LXX</th><th>DSS</th><th>Type</th><th>Implication</th>' +
          '</tr></thead><tbody>';
        divs.forEach(function (d) {
          inner += '<tr>' +
            '<td>' + _esc(String(d.word_position || '')) + '</td>' +
            '<td>' + _esc(d.mt_reading  || '—') + '</td>' +
            '<td>' + _esc(d.lxx_reading || '—') + '</td>' +
            '<td><strong>' + _esc(d.dss_reading || '—') + '</strong></td>' +
            '<td><span class="theo-type-badge">' + _esc(d.classification || '') + '</span></td>' +
            '<td>' + _esc(d.textual_implication || '') + '</td>' +
            '</tr>';
        });
        inner += '</tbody></table>';
      }

      if (ms.overall_note) {
        inner += '<p class="dss-overall-note">' + _esc(ms.overall_note) + '</p>';
      }

      body.innerHTML = inner;
    }

    header.addEventListener('click', function () {
      var isOpen = !body.classList.contains('collapsed');
      body.classList.toggle('collapsed', isOpen);
      header.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
      var toggle = header.querySelector('.dss-ms-toggle');
      if (toggle) toggle.textContent = isOpen ? '▼' : '▲';
    });

    card.appendChild(header);
    card.appendChild(body);
    return card;
  }

  function _alignmentBadge(alignment) {
    var labels = {
      sides_with_mt:  'Sides with MT',
      sides_with_lxx: 'Sides with LXX',
      independent:    'Independent',
      absent:         'Not extant',
    };
    var classes = {
      sides_with_mt:  'dss-align-mt',
      sides_with_lxx: 'dss-align-lxx',
      independent:    'dss-align-ind',
      absent:         'dss-align-abs',
    };
    var label = labels[alignment] || alignment;
    var cls   = classes[alignment] || 'dss-align-abs';
    return '<span class="dss-align-badge ' + cls + '">' + _esc(label) + '</span>';
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
  window.dss = { analyze: analyze };

})();
