/* BibCrit — Targum Comparator */

(function () {
  'use strict';

  // Targum covers Torah + Prophets (OT Canon subset)
  var _TARGUM_BOOKS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36, 'Deuteronomy': 34,
    'Joshua': 24, 'Judges': 21, '1 Samuel': 31, '2 Samuel': 24,
    '1 Kings': 22, '2 Kings': 25, 'Isaiah': 66, 'Jeremiah': 52,
    'Ezekiel': 48, 'Hosea': 14, 'Joel': 3, 'Amos': 9, 'Obadiah': 1,
    'Jonah': 4, 'Micah': 7, 'Nahum': 3, 'Habakkuk': 3,
    'Zephaniah': 3, 'Haggai': 2, 'Zechariah': 14, 'Malachi': 4,
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
  var results    = document.getElementById('targum-results');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  var _timer = null;
  var _currentRef = '';
  var _finalHandled   = false;
  var _partialData    = {};
  var _sectionReceived = false;

  // Populate book dropdown
  if (selBook) {
    Object.keys(_TARGUM_BOOKS).forEach(function (b) {
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
      var numCh = _TARGUM_BOOKS[book] || 0;
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
      var b = selBook ? selBook.value : '';
      var c = selChapter ? selChapter.value : '';
      var v = this.value;
      if (b && c && v) refInput.value = b + ' ' + c + ':' + v;
    });
  }

  // Featured passage clicks
  document.querySelectorAll('.featured-ref').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.dataset.ref;
      if (ref) { refInput.value = ref; analyze(ref); }
    });
  });

  btnAnalyze.addEventListener('click', function () {
    var ref = (refInput ? refInput.value : '').trim();
    if (!ref) {
      showToast(window.t ? window.t('err_enter_passage', 'Please enter a passage') : 'Please enter a passage');
      return;
    }
    analyze(ref);
  });

  if (refInput) {
    refInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') btnAnalyze.click();
    });
  }

  function showToast(msg, dur) {
    if (!toast) return;
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(function () { toast.style.display = 'none'; }, dur || 3000);
  }

  function setLoading(on) {
    if (on && emptyState) emptyState.style.display = 'none'; // only hide; renderResult shows results explicitly
    if (loadState)  loadState.style.display  = on ? 'block' : 'none';
    if (results)    results.style.display    = on ? 'none' : 'block';
    if (on && _timer) clearInterval(_timer);
    if (on && loadTimer) {
      var secs = 0;
      loadTimer.textContent = '';
      _timer = setInterval(function () {
        secs++;
        loadTimer.textContent = secs + 's';
      }, 1000);
    } else if (loadTimer) {
      loadTimer.textContent = '';
    }
  }

  function showSection(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = '';
  }

  function setText(id, html) {
    var el = document.getElementById(id);
    if (el) {
      el.innerHTML = html;
      var sec = el.closest('.num-section');
      if (sec) sec.style.display = '';
    }
  }

  function renderResult(data) {
    if (loadTimer) loadTimer.textContent = '';
    if (_timer) { clearInterval(_timer); _timer = null; }

    setLoading(false);
    if (heading) {
      heading.textContent = data.reference || _currentRef;
      heading.style.display = '';
    }

    // Three-column text
    var colMt   = document.getElementById('col-mt-text');
    var colTarg = document.getElementById('col-targ-text');
    var colLxx  = document.getElementById('col-lxx-text');
    var msBadge = document.getElementById('manuscript-badge');
    var textCols = document.getElementById('text-columns');
    if (colMt)   colMt.textContent   = data.mt_text   || '';
    if (colTarg) colTarg.textContent = data.targ_text  || '';
    if (colLxx)  colLxx.textContent  = data.lxx_text   || '';
    if (msBadge) msBadge.textContent = data.manuscript || 'Targum';
    if (textCols && (data.mt_text || data.targ_text)) textCols.style.display = '';

    // Synthesis
    if (data.synthesis) {
      setText('synthesis-body', esc(data.synthesis));
      showSection('synthesis-section');
    }

    // Rendering fidelity
    if (data.rendering_fidelity && data.rendering_fidelity.word_analysis) {
      var rows = (data.rendering_fidelity.word_analysis || []).map(function (w) {
        return '<tr><td>' + esc(w.mt_word || '') + '</td>' +
               '<td>' + esc(w.targ_word || '') + '</td>' +
               '<td><span class="var-type-chip">' + esc(w.type || '') + '</span></td>' +
               '<td>' + esc(w.note || '') + '</td></tr>';
      }).join('');
      setText('fidelity-body',
        '<p style="margin-bottom:.5rem">Overall: <strong>' + esc(data.rendering_fidelity.overall || '') + '</strong></p>' +
        (rows ? '<div style="overflow-x:auto"><table class="var-table" style="min-width:520px"><thead><tr><th>MT</th><th>Targum</th><th>Type</th><th>Note</th></tr></thead><tbody>' + rows + '</tbody></table></div>' : ''));
      showSection('fidelity-section');
    }

    // Theological modifications
    if (data.theological_modifications && data.theological_modifications.length) {
      var html = data.theological_modifications.map(function (m) {
        return '<div class="variant-card">' +
          '<div class="vc-type">' + esc(m.type || '') + '</div>' +
          '<div class="vc-pair"><span class="vc-label">MT:</span> ' + esc(m.mt_reading || '') + '</div>' +
          '<div class="vc-pair"><span class="vc-label">Targum:</span> ' + esc(m.targ_reading || '') + '</div>' +
          '<p class="vc-note">' + esc(m.explanation || '') + '</p></div>';
      }).join('');
      setText('theological-body', html);
      showSection('theological-section');
    }

    // Targumic expansions
    if (data.targumic_expansions && data.targumic_expansions.length) {
      var html2 = data.targumic_expansions.map(function (ex) {
        return '<div class="variant-card">' +
          '<div class="vc-location">' + esc(ex.location || '') + '</div>' +
          '<p class="vc-expansion">' + esc(ex.expansion_text || '') + '</p>' +
          (ex.midrashic_parallel ? '<p class="vc-parallel">Midrashic parallel: ' + esc(ex.midrashic_parallel) + '</p>' : '') +
          '<p class="vc-note">' + esc(ex.significance || '') + '</p></div>';
      }).join('');
      setText('expansions-body', html2);
      showSection('expansions-section');
    }

    // Messianic reinterpretation
    if (data.messianic_reinterpretation && data.messianic_reinterpretation.present) {
      var insts = (data.messianic_reinterpretation.instances || []).map(function (i) {
        return '<div class="variant-card">' +
          '<div class="vc-pair"><span class="vc-label">MT:</span> ' + esc(i.mt_reading || '') + '</div>' +
          '<div class="vc-pair"><span class="vc-label">Targum:</span> ' + esc(i.targ_reading || '') + '</div>' +
          '<p class="vc-note">' + esc(i.scholarly_note || '') + '</p></div>';
      }).join('');
      setText('messianic-body', insts || '<p>Messianic reinterpretation present — see synthesis.</p>');
      showSection('messianic-section');
    }

    // LXX alignment
    if (data.lxx_alignment && data.lxx_alignment.areas_of_agreement) {
      setText('lxx-align-body',
        '<p>' + esc(data.lxx_alignment.areas_of_agreement) + '</p>' +
        (data.lxx_alignment.significance ? '<p class="vc-note">' + esc(data.lxx_alignment.significance) + '</p>' : ''));
      showSection('lxx-align-section');
    }

    // BibCrit assessment
    if (data.assessment) {
      var a = data.assessment;
      var aHtml = '';
      if (a.title)      aHtml += '<h3 class="bc-title">' + esc(a.title) + '</h3>';
      if (a.plain)      aHtml += '<p class="bc-plain">' + esc(a.plain) + '</p>';
      if (a.reasoning)  aHtml += '<p>' + esc(a.reasoning) + '</p>';
      if (a.next_steps) aHtml += '<p><strong>Next steps:</strong> ' + esc(a.next_steps) + '</p>';
      if (typeof a.confidence === 'number') {
        aHtml += '<div class="confidence-bar"><div class="confidence-fill" style="width:' +
                 (a.confidence * 100).toFixed(0) + '%"></div></div>';
      }
      var bibSec  = document.getElementById('bibcrit-assessment');
      var bibBody = document.getElementById('bibcrit-body');
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
      btnSbl.onclick = function () {
        navigator.clipboard.writeText(data.citations.sbl);
        showToast(window.t ? window.t('toast_sbl_copied', 'SBL footnote copied!') : 'Copied!');
      };
    }
    if (btnBibtex && data.citations && data.citations.bibtex) {
      btnBibtex.onclick = function () {
        navigator.clipboard.writeText(data.citations.bibtex);
        showToast(window.t ? window.t('toast_bibtex_copied', 'BibTeX copied!') : 'Copied!');
      };
    }
    if (btnShare) {
      btnShare.onclick = function () {
        var url = window.location.origin + '/targum?ref=' + encodeURIComponent(_currentRef);
        navigator.clipboard.writeText(url);
        showToast(window.t ? window.t('toast_link_copied', 'Link copied!') : 'Link copied!');
      };
    }
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Skeleton helpers ──────────────────────────────────────────────────────
  function _skelRows(n, widths) {
    var html = '';
    var pcts = widths || [100, 88, 72, 58, 45];
    for (var i = 0; i < n; i++) {
      html += '<div class="dss-skel-row" style="height:12px;width:' + (pcts[i] || 55) + '%"></div>';
    }
    return html;
  }

  function _renderSkeleton() {
    var textCols = document.getElementById('text-columns');
    if (textCols) textCols.style.display = '';
    var colMt   = document.getElementById('col-mt-text');
    var colTarg = document.getElementById('col-targ-text');
    var colLxx  = document.getElementById('col-lxx-text');
    if (colMt)   colMt.innerHTML   = _skelRows(4, [90, 75, 60, 80]);
    if (colTarg) colTarg.innerHTML = _skelRows(4, [85, 70, 55, 75]);
    if (colLxx)  colLxx.innerHTML  = _skelRows(4, [80, 65, 50, 70]);
    var synthSec  = document.getElementById('synthesis-section');
    var synthBody = document.getElementById('synthesis-body');
    if (synthSec && synthBody) {
      synthBody.innerHTML = _skelRows(3, [100, 85, 70]);
      synthSec.style.display = '';
    }
  }

  // ── Progressive section rendering ─────────────────────────────────────────
  function _renderSection(key, data) {
    _partialData[key] = data;
    _sectionReceived  = true;

    if (emptyState) emptyState.style.display = 'none';

    // _corpus: MT, Targum, and LXX texts from corpus — replace skeleton columns
    // with real text immediately, before Claude analysis begins.
    if (key === '_corpus') {
      var colMt   = document.getElementById('col-mt-text');
      var colTarg = document.getElementById('col-targ-text');
      var colLxx  = document.getElementById('col-lxx-text');
      var msBadge = document.getElementById('manuscript-badge');
      var textCols = document.getElementById('text-columns');
      if (colMt)   colMt.textContent   = data.mt_text   || '';
      if (colTarg) colTarg.textContent = data.targ_text  || '';
      if (colLxx)  colLxx.textContent  = data.lxx_text   || '';
      if (msBadge) msBadge.textContent = data.manuscript || 'Targum';
      if (textCols && (data.mt_text || data.targ_text)) textCols.style.display = '';
      return;
    }

    if (key === 'synthesis') {
      setText('synthesis-body', '<p>' + esc(String(data || '')) + '</p>');
      showSection('synthesis-section');
      var synthSecEl = document.getElementById('synthesis-section');
      if (synthSecEl) staggerReveal(synthSecEl, 0);
    }

    if (key === 'key_divergences' || key === 'rendering_fidelity') {
      var fid = _partialData.rendering_fidelity;
      if (fid && fid.word_analysis) {
        var rows = (fid.word_analysis || []).map(function (w) {
          return '<tr><td>' + esc(w.mt_word || '') + '</td>' +
                 '<td>' + esc(w.targ_word || '') + '</td>' +
                 '<td><span class="var-type-chip">' + esc(w.type || '') + '</span></td>' +
                 '<td>' + esc(w.note || '') + '</td></tr>';
        }).join('');
        setText('fidelity-body',
          '<p style="margin-bottom:.5rem">Overall: <strong>' + esc(fid.overall || '') + '</strong></p>' +
          (rows ? '<div style="overflow-x:auto"><table class="var-table" style="min-width:520px"><thead><tr><th>MT</th><th>Targum</th><th>Type</th><th>Note</th></tr></thead><tbody>' + rows + '</tbody></table></div>' : ''));
        showSection('fidelity-section');
        var fidSec = document.getElementById('fidelity-section');
        if (fidSec) staggerReveal(fidSec, 0);
      }
    }

    if (key === 'theological_modifications') {
      var mods = Array.isArray(data) ? data : (data || []);
      if (mods.length) {
        var html = mods.map(function (m) {
          return '<div class="variant-card">' +
            '<div class="vc-type">' + esc(m.type || '') + '</div>' +
            '<div class="vc-pair"><span class="vc-label">MT:</span> ' + esc(m.mt_reading || '') + '</div>' +
            '<div class="vc-pair"><span class="vc-label">Targum:</span> ' + esc(m.targ_reading || '') + '</div>' +
            '<p class="vc-note">' + esc(m.explanation || '') + '</p></div>';
        }).join('');
        setText('theological-body', html);
        showSection('theological-section');
        var theoSec = document.getElementById('theological-section');
        if (theoSec) staggerReveal(theoSec, 0);
      }
    }

    if (key === 'targumic_expansions' || key === 'expansions') {
      var exps = Array.isArray(data) ? data : (data || []);
      if (exps.length) {
        var html2 = exps.map(function (ex) {
          return '<div class="variant-card">' +
            '<div class="vc-location">' + esc(ex.location || '') + '</div>' +
            '<p class="vc-expansion">' + esc(ex.expansion_text || '') + '</p>' +
            (ex.midrashic_parallel ? '<p class="vc-parallel">Midrashic parallel: ' + esc(ex.midrashic_parallel) + '</p>' : '') +
            '<p class="vc-note">' + esc(ex.significance || '') + '</p></div>';
        }).join('');
        setText('expansions-body', html2);
        showSection('expansions-section');
        var expSec = document.getElementById('expansions-section');
        if (expSec) staggerReveal(expSec, 0);
      }
    }

    if (key === 'messianic_reinterpretation' || key === 'messianic') {
      if (data && data.present) {
        var insts = (data.instances || []).map(function (i) {
          return '<div class="variant-card">' +
            '<div class="vc-pair"><span class="vc-label">MT:</span> ' + esc(i.mt_reading || '') + '</div>' +
            '<div class="vc-pair"><span class="vc-label">Targum:</span> ' + esc(i.targ_reading || '') + '</div>' +
            '<p class="vc-note">' + esc(i.scholarly_note || '') + '</p></div>';
        }).join('');
        setText('messianic-body', insts || '<p>Messianic reinterpretation present \u2014 see synthesis.</p>');
        showSection('messianic-section');
        var mesSec = document.getElementById('messianic-section');
        if (mesSec) staggerReveal(mesSec, 0);
      }
    }

    if (key === 'lxx_alignment') {
      if (data && data.areas_of_agreement) {
        setText('lxx-align-body',
          '<p>' + esc(data.areas_of_agreement) + '</p>' +
          (data.significance ? '<p class="vc-note">' + esc(data.significance) + '</p>' : ''));
        showSection('lxx-align-section');
        var lxxSec = document.getElementById('lxx-align-section');
        if (lxxSec) staggerReveal(lxxSec, 0);
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

  function analyze(ref) {
    _currentRef      = ref;
    _finalHandled    = false;
    _partialData     = {};
    _sectionReceived = false;
    // Show compact spinner + heading + skeleton immediately
    if (emptyState) emptyState.style.display = 'none';
    if (results)    results.style.display    = 'block';
    if (loadState) {
      loadState.classList.add('is-compact');
      loadState.style.display = 'block';
    }
    if (loadStep) loadStep.textContent = window.t ? window.t('step_generating', 'Analyzing \u2014 this may take 40\u201360 seconds\u2026') : 'Analyzing \u2014 this may take 40\u201360 seconds\u2026';
    if (_timer) clearInterval(_timer);
    if (loadTimer) {
      var secs = 0; loadTimer.textContent = '';
      _timer = setInterval(function () { secs++; loadTimer.textContent = secs + 's'; }, 1000);
    }
    if (heading) { heading.textContent = ref; heading.style.display = ''; }
    _renderSkeleton();

    var lang = new URLSearchParams(window.location.search).get('lang') || 'en';
    var url  = '/api/targum/stream?ref=' + encodeURIComponent(ref) + '&lang=' + lang;
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
          es.close();
          _hideCompactSpinner();
          showToast(msg.msg || 'Error', 5000);
        }
      } catch (_) {}
    };

    es.onerror = function () {
      if (_finalHandled) return;
      es.close();
      _hideCompactSpinner();
      showToast(window.t ? window.t('err_connection', 'Connection error') : 'Connection error', 5000);
    };
  }

  window.targum = { analyze: analyze };
}());
