/**
 * backtranslation.js — BibCrit LXX Back-Translation Workbench
 *
 * Responsibilities:
 *   - Corpus browser: cascading book/chapter/verse selects (LXX tradition)
 *   - Fetch and render Vorlage reconstruction from /api/backtranslation/stream
 *   - Render three-column grid: LXX | Vorlage (color-coded) | MT
 *   - Click word → show word analysis tab
 *   - Export: SBL footnote + BibTeX via copy-to-clipboard
 */

(function () {
  'use strict';

  // ── State ─────────────────────────────────────────────────────────────────
  var currentData = null;
  var currentRef  = '';

  // ── Status color map ──────────────────────────────────────────────────────
  var STATUS = {
    'agrees_mt':  { cls: 'bt-agrees-mt',  label: 'Agrees MT',   border: '#28a745' },
    'agrees_dss': { cls: 'bt-agrees-dss', label: 'Agrees DSS',  border: '#3a6bc4' },
    'unattested': { cls: 'bt-unattested', label: 'Unattested',  border: '#dc3545' },
    'idiom_only': { cls: 'bt-idiom-only', label: 'Greek Idiom', border: '#6c757d' },
  };

  // ── DOM refs ──────────────────────────────────────────────────────────────
  var selBook       = document.getElementById('sel-book');
  var selChapter    = document.getElementById('sel-chapter');
  var selVerse      = document.getElementById('sel-verse');
  var refInput      = document.getElementById('ref-input');
  var btnAnalyze    = document.getElementById('btn-analyze');
  var emptyState    = document.getElementById('empty-state');
  var loadingState  = document.getElementById('loading-state');
  var vorlageGrid   = document.getElementById('vorlage-grid');
  var tabsArea      = document.getElementById('tabs-area');
  var tabsNav       = document.getElementById('tabs-nav');
  var tabsBody      = document.getElementById('tabs-body');
  var lxxText       = document.getElementById('lxx-text');
  var vorlageText   = document.getElementById('vorlage-text');
  var mtText        = document.getElementById('mt-text');
  var exportRow     = document.getElementById('export-row');
  var passageHeading = document.getElementById('passage-heading');

  if (!selBook || !btnAnalyze) return;  // guard: only run on backtranslation page

  // ── Info banner (dismissable, remembered via localStorage) ───────────────
  var infoBanner = document.getElementById('bt-info-banner');
  var infoClose  = document.getElementById('bt-info-close');
  if (infoBanner) {
    if (localStorage.getItem('bt-info-dismissed') === '1') {
      infoBanner.style.display = 'none';
    }
    if (infoClose) {
      infoClose.addEventListener('click', function () {
        infoBanner.style.maxHeight = infoBanner.scrollHeight + 'px';
        infoBanner.style.overflow  = 'hidden';
        infoBanner.style.transition = 'max-height 0.3s ease, opacity 0.3s ease, padding 0.3s ease';
        requestAnimationFrame(function () {
          infoBanner.style.maxHeight = '0';
          infoBanner.style.opacity   = '0';
          infoBanner.style.padding   = '0';
        });
        setTimeout(function () { infoBanner.style.display = 'none'; }, 320);
        localStorage.setItem('bt-info-dismissed', '1');
      });
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  fetchBooks();

  document.querySelectorAll('.featured-ref').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      refInput.value = el.dataset.ref;
      analyze(el.dataset.ref);
    });
  });

  btnAnalyze.addEventListener('click', function () { analyze(refInput.value.trim()); });
  refInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') analyze(refInput.value.trim());
  });

  var _randomPassages = [
    'Exodus 3:14', 'Micah 5:2', 'Numbers 24:17', 'Amos 9:11',
    'Jeremiah 31:31', 'Isaiah 53:7', 'Zechariah 9:9', 'Isaiah 9:6',
    'Genesis 3:15', 'Psalm 2:7', 'Isaiah 11:1', 'Joel 3:1',
  ];
  document.getElementById('btn-random').addEventListener('click', function () {
    var ref = _randomPassages[Math.floor(Math.random() * _randomPassages.length)];
    refInput.value = ref;
    analyze(ref);
  });

  // ── Corpus browser ────────────────────────────────────────────────────────
  function fetchBooks() {
    fetch('/api/books?tradition=LXX')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.books || []).forEach(function (b) {
          var o = document.createElement('option');
          o.value = o.textContent = b;
          selBook.appendChild(o);
        });
      });
  }

  selBook.addEventListener('change', function () {
    selChapter.innerHTML = '<option value="">Ch…</option>';
    selVerse.innerHTML   = '<option value="">Vs…</option>';
    selChapter.disabled  = true;
    selVerse.disabled    = true;
    if (!selBook.value) return;
    fetch('/api/chapters?book=' + encodeURIComponent(selBook.value) + '&tradition=LXX')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.chapters || []).forEach(function (c) {
          var o = document.createElement('option');
          o.value = o.textContent = c;
          selChapter.appendChild(o);
        });
        selChapter.disabled = false;
      });
  });

  selChapter.addEventListener('change', function () {
    selVerse.innerHTML  = '<option value="">Vs…</option>';
    selVerse.disabled   = true;
    if (!selChapter.value) return;
    fetch('/api/verses?book=' + encodeURIComponent(selBook.value) +
          '&chapter=' + selChapter.value + '&tradition=LXX')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.verses || []).forEach(function (v) {
          var o = document.createElement('option');
          o.value = o.textContent = v;
          selVerse.appendChild(o);
        });
        selVerse.disabled = false;
      });
  });

  selVerse.addEventListener('change', function () {
    if (!selVerse.value) return;
    var ref = selBook.value + ' ' + selChapter.value + ':' + selVerse.value;
    refInput.value = ref;
    analyze(ref);
  });

  // ── Analysis (SSE) ────────────────────────────────────────────────────────
  function analyze(ref) {
    if (!ref) return;
    currentRef = ref;

    // Show loading, hide others
    emptyState.style.display    = 'none';
    vorlageGrid.style.display   = 'none';
    tabsArea.style.display      = 'none';
    passageHeading.style.display = 'none';
    loadingState.style.display  = 'flex';

    var stepEl  = document.getElementById('loading-step');
    var timerEl = document.getElementById('loading-timer');
    stepEl.textContent  = 'Preparing…';
    timerEl.textContent = '';

    var startTime = Date.now();
    var timerInterval = setInterval(function () {
      var s = Math.floor((Date.now() - startTime) / 1000);
      timerEl.textContent = s + 's';
    }, 1000);

    var es = new EventSource('/api/backtranslation/stream?ref=' + encodeURIComponent(ref) + '&lang=' + (window.bibcritLang || 'en'));

    es.onmessage = function (e) {
      var msg = JSON.parse(e.data);

      if (msg.type === 'step') {
        stepEl.textContent = msg.msg;

      } else if (msg.type === 'error') {
        clearInterval(timerInterval);
        es.close();
        loadingState.style.display = 'none';
        emptyState.style.display   = 'block';
        emptyState.querySelector('h2').textContent = '⚠ ' + msg.msg;

      } else if (msg.type === 'done') {
        clearInterval(timerInterval);
        es.close();
        loadingState.style.display = 'none';
        currentData = msg.data;
        history.replaceState(null, '', '/backtranslation?ref=' + encodeURIComponent(ref));
        if (typeof updateBudgetBar === 'function') updateBudgetBar();
        renderWorkbench(msg.data);
      }
    };

    es.onerror = function () {
      clearInterval(timerInterval);
      es.close();
      loadingState.style.display = 'none';
      emptyState.style.display   = 'block';
    };
  }

  // ── Render ────────────────────────────────────────────────────────────────
  function renderWorkbench(data) {
    // Passage heading
    passageHeading.innerHTML =
      '<span class="ph-ref">' + _esc(data.reference) + '</span>' +
      '<span class="ph-tool">Back-Translation Workbench</span>';
    passageHeading.style.display = 'flex';

    // Render columns
    renderLxx(data.lxx_words || [], data.reconstructed_words || []);
    renderVorlage(data.reconstructed_words || []);
    renderMt(data.mt_words || []);

    // Show legend
    var legend = document.getElementById('bt-legend');
    if (legend) legend.style.display = 'flex';

    vorlageGrid.style.display = 'grid';

    // Build tabs
    buildTabs(data);

    tabsArea.style.display  = 'block';
    exportRow.style.display = 'flex';

    // Inject Scholar Rating, Copy, Download into export-row (once only)
    if (window.ResultActions) {
      ResultActions.init({
        toolName: 'backtranslation',
        getReference: function() { return currentRef; },
        getResultData: function() { return currentData || {}; },
      });
    }
  }

  // ── Column renderers ──────────────────────────────────────────────────────
  function renderLxx(lxxWords, reconstructed) {
    lxxText.innerHTML = '';
    // Build a quick lookup: lxx_word phrase → position index
    var phraseMap = {};
    reconstructed.forEach(function (rw, i) {
      (rw.lxx_word || '').split(/\s+/).forEach(function (tok) {
        if (tok) phraseMap[tok.toLowerCase()] = i;
      });
    });

    lxxWords.forEach(function (w) {
      var span = document.createElement('span');
      span.className   = 'word';
      span.textContent = w.word_text + ' ';
      var idx = phraseMap[(w.word_text || '').toLowerCase()];
      if (idx !== undefined) {
        span.dataset.btIdx = idx;
        span.classList.add('divergent-lxx');
        span.addEventListener('click', function () {
          var groupId = _wordGroupMap[idx];
          if (groupId) activateTab(groupId, 'bt-card-' + idx);
        });
      }
      lxxText.appendChild(span);
    });
  }

  function renderVorlage(reconstructed) {
    vorlageText.innerHTML = '';
    reconstructed.forEach(function (rw, i) {
      var span = document.createElement('span');
      var st   = STATUS[rw.status] || STATUS['idiom_only'];
      span.className   = 'word bt-word ' + st.cls;
      span.textContent = (rw.vorlage_word || '—') + ' ';
      span.dataset.btIdx = i;
      span.addEventListener('click', function () {
        var groupId = _wordGroupMap[i];
        if (groupId) activateTab(groupId, 'bt-card-' + i);
      });
      vorlageText.appendChild(span);
    });
  }

  function renderMt(mtWords) {
    mtText.innerHTML = '';
    mtWords.forEach(function (w) {
      var span = document.createElement('span');
      span.className   = 'word';
      span.textContent = w.word_text + ' ';
      mtText.appendChild(span);
    });
  }

  // ── Tabs (grouped by status) ──────────────────────────────────────────────
  // Tab order: Agrees MT → Agrees DSS → Unattested → Greek Idiom → Assessment
  var GROUP_ORDER = ['agrees_mt', 'agrees_dss', 'unattested', 'idiom_only'];

  // Maps word position → group tab ID (used by word-click handlers)
  var _wordGroupMap = {};
  var _sortAsc      = false;   // default: highest confidence first
  var _lastData     = null;

  function buildTabs(data) {
    _lastData          = data;
    tabsNav.innerHTML  = '';
    tabsBody.innerHTML = '';
    _wordGroupMap      = {};

    var reconstructed = data.reconstructed_words || [];

    // Group words by status
    var groups = {};
    GROUP_ORDER.forEach(function (s) { groups[s] = []; });
    reconstructed.forEach(function (rw, i) {
      var s = rw.status || 'idiom_only';
      if (!groups[s]) groups[s] = [];
      groups[s].push({ rw: rw, idx: i });
      _wordGroupMap[i] = 'bt-group-' + s;
    });

    var firstPanelId = null;

    GROUP_ORDER.forEach(function (status) {
      var items = groups[status] || [];
      if (!items.length) return;

      // Sort by confidence
      items.sort(function (a, b) {
        return _sortAsc
          ? (a.rw.confidence || 0) - (b.rw.confidence || 0)
          : (b.rw.confidence || 0) - (a.rw.confidence || 0);
      });

      var st      = STATUS[status] || STATUS['idiom_only'];
      var panelId = 'bt-group-' + status;
      if (!firstPanelId) firstPanelId = panelId;

      // Tab button with count badge
      var btn = document.createElement('button');
      btn.className     = 'tab-btn';
      btn.role          = 'tab';
      btn.dataset.panel = panelId;
      btn.innerHTML =
        '<span class="tab-num" style="background:' + st.border + ';color:#fff;">' +
          items.length +
        '</span> ' + st.label;
      btn.addEventListener('click', function () { activateTab(panelId); });
      tabsNav.appendChild(btn);

      // Panel: stacked cards sorted by confidence
      var panel = document.createElement('div');
      panel.id        = panelId;
      panel.className = 'tab-panel';

      items.forEach(function (item) {
        var cardWrap = document.createElement('div');
        cardWrap.id        = 'bt-card-' + item.idx;
        cardWrap.className = 'bt-group-card';
        cardWrap.innerHTML = buildWordPanelHtml(item.rw, item.idx, st);
        panel.appendChild(cardWrap);
      });

      tabsBody.appendChild(panel);
    });

    // Sort toggle button (appended after group tabs, before Assessment)
    var sortBtn = document.createElement('button');
    sortBtn.className = 'tab-btn bt-sort-btn';
    sortBtn.id        = 'bt-sort-toggle';
    sortBtn.title     = 'Sort by confidence';
    sortBtn.innerHTML = _sortAsc ? '↑ Confidence' : '↓ Confidence';
    sortBtn.addEventListener('click', function () {
      _sortAsc = !_sortAsc;
      var activePanel = tabsBody.querySelector('.tab-panel.active');
      var activePanelId = activePanel ? activePanel.id : null;
      buildTabs(_lastData);
      if (activePanelId) activateTab(activePanelId);
    });
    tabsNav.appendChild(sortBtn);

    // BibCrit Assessment tab
    if (data.bibcrit_assessment) {
      var assessPanelId = 'bt-panel-assessment';
      var assessBtn = document.createElement('button');
      assessBtn.className     = 'tab-btn tab-hypothesis';
      assessBtn.role          = 'tab';
      assessBtn.dataset.panel = assessPanelId;
      assessBtn.innerHTML     =
        '<span class="tab-num" style="background:#5f2c7c;color:#fff;">✦</span> BibCrit Assessment';
      assessBtn.addEventListener('click', function () { activateTab(assessPanelId); });
      tabsNav.appendChild(assessBtn);

      var assessPanel = document.createElement('div');
      assessPanel.id        = assessPanelId;
      assessPanel.className = 'tab-panel';
      assessPanel.innerHTML = buildAssessmentHtml(data);
      tabsBody.appendChild(assessPanel);
    }

    if (firstPanelId) activateTab(firstPanelId);
  }

  function activateTab(panelId, scrollToCardId) {
    tabsNav.querySelectorAll('.tab-btn').forEach(function (b) {
      b.classList.remove('active');
    });
    tabsBody.querySelectorAll('.tab-panel').forEach(function (p) {
      p.classList.remove('active');
    });

    var activeBtn   = tabsNav.querySelector('[data-panel="' + panelId + '"]');
    var activePanel = document.getElementById(panelId);
    if (activeBtn)   activeBtn.classList.add('active');
    if (activePanel) activePanel.classList.add('active');

    // Scroll to specific card within the panel (from word-click)
    if (scrollToCardId) {
      var card = document.getElementById(scrollToCardId);
      if (card) {
        setTimeout(function () {
          card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          card.classList.add('bt-card-highlight');
          setTimeout(function () { card.classList.remove('bt-card-highlight'); }, 1200);
        }, 50);
      }
    }
  }

  function buildWordPanelHtml(rw, idx, st) {
    var conf     = rw.confidence || 0;
    var confTier = conf >= 0.75 ? 'high' : conf >= 0.45 ? 'medium' : 'low';
    var confLabel = conf >= 0.75 ? 'HIGH' : conf >= 0.45 ? 'MEDIUM' : 'LOW';

    var alts = '';
    (rw.alternatives || []).forEach(function (alt) {
      alts += '<li><span class="hebrew-text">' + _esc(alt.reading) + '</span>' +
              ' <span class="conf-small">(' + Math.round(alt.confidence * 100) + '%)</span>' +
              ' — ' + _esc(alt.note) + '</li>';
    });

    return '<div class="div-card" style="border-left:4px solid ' + st.border + ';">' +
      '<div class="div-card-head">' +
        '<span class="div-words">' +
          '<span class="div-lxx">' + _esc(rw.lxx_word || '') + '</span>' +
          ' <span class="div-arrow">→</span> ' +
          '<span class="div-mt hebrew-text">' + _esc(rw.vorlage_word || '—') + '</span>' +
        '</span>' +
        '<span class="div-badges">' +
          '<span class="confidence-badge confidence-' + confTier + '">' + confLabel + ' ' + Math.round(conf * 100) + '%</span>' +
        '</span>' +
      '</div>' +
      (rw.mt_equivalent ? '<p class="div-meta">MT equivalent: <span class="hebrew-text">' + _esc(rw.mt_equivalent) + '</span></p>' : '') +
      (rw.dss_witness   ? '<p class="div-meta">DSS: ' + _esc(rw.dss_witness) + '</p>' : '') +
      '<div class="div-analysis">' +
        '<p>' + _esc(rw.reasoning || '') + '</p>' +
      '</div>' +
      (alts ? '<div class="div-alternatives"><strong>Alternative readings:</strong><ul>' + alts + '</ul></div>' : '') +
    '</div>';
  }

  function buildAssessmentHtml(data) {
    var a    = data.bibcrit_assessment || {};
    var conf = a.confidence || 0;
    var confTier  = conf >= 0.75 ? 'high' : conf >= 0.45 ? 'medium' : 'low';
    var confLabel = conf >= 0.75 ? 'HIGH' : conf >= 0.45 ? 'MEDIUM' : 'LOW';

    return '<div class="hyp-card">' +
      '<div class="hyp-card-header">' +
        '<span class="hyp-card-title">✦ BibCrit Assessment</span>' +
        '<span class="hyp-card-subtitle">' + _esc(a.title || '') + '</span>' +
        '<span class="confidence-badge confidence-' + confTier + '">' + confLabel + '</span>' +
      '</div>' +
      '<p class="hyp-card-plain">' + _esc(a.plain || '') + '</p>' +
      '<p class="hyp-card-reasoning">' + _esc(a.reasoning || '') + '</p>' +
      (data.summary_technical ? '<p class="hyp-card-reasoning" style="margin-top:8px;">' + _esc(data.summary_technical) + '</p>' : '') +
      '<p class="hyp-card-generated">generated by ' + _esc(data.model_version || 'BibCrit') + '</p>' +
    '</div>';
  }

  // ── Export ────────────────────────────────────────────────────────────────
  document.getElementById('btn-sbl').addEventListener('click', function () {
    if (!currentData) return;
    var lines = (currentData.reconstructed_words || []).map(function (rw) {
      var st = STATUS[rw.status] || STATUS['idiom_only'];
      return 'In ' + currentRef + ', LXX ' + (rw.lxx_word || '') +
             ' reflects probable Vorlage ' + (rw.vorlage_word || '—') +
             ' (' + st.label + '). ' + (rw.reasoning || '');
    });
    copyToClipboard(lines.join('\n\n'));
    showToast(window.t('toast_sbl_copied', 'SBL footnote copied to clipboard'));
  });

  document.getElementById('btn-bibtex').addEventListener('click', function () {
    if (!currentData) return;
    var key   = currentRef.replace(/\s+/g, '').replace(':', '_');
    var note  = (currentData.reconstructed_words || []).map(function (rw) {
      return (rw.lxx_word || '') + ' → ' + (rw.vorlage_word || '—') +
             ' (' + (rw.status || '') + ')';
    }).join('; ');
    var bib = '@misc{BibCrit_BT_' + key + ',\n' +
              '  title   = {Vorlage Reconstruction: ' + currentRef + '},\n' +
              '  note    = {' + note + '},\n' +
              '  howpublished = {\\url{https://bibcrit.org/backtranslation?ref=' +
              encodeURIComponent(currentRef) + '}},\n' +
              '}';
    copyToClipboard(bib);
    showToast(window.t('toast_bibtex_copied', 'BibTeX copied to clipboard'));
  });

  document.getElementById('btn-share').addEventListener('click', function () {
    var url = window.location.href;
    var shareUrlEl = document.getElementById('share-url');
    var shareQrEl  = document.getElementById('share-qr');
    var shareModal = document.getElementById('share-modal');
    if (!shareModal) return;
    if (shareUrlEl) shareUrlEl.value = url;
    if (shareQrEl) {
      shareQrEl.innerHTML = '';
      if (typeof QRCode !== 'undefined') {
        var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        new QRCode(shareQrEl, {
          text:            url,
          width:           160,
          height:          160,
          colorDark:       isDark ? '#e8e6de' : '#1a1a1a',
          colorLight:      isDark ? '#1a1a1a' : '#ffffff',
          correctLevel:    QRCode.CorrectLevel.M,
        });
      }
    }
    shareModal.style.display = 'flex';
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  function copyToClipboard(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
    } else {
      var ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  }

  function showToast(msg) {
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent    = msg;
    toast.style.display  = 'block';
    toast.style.opacity  = '1';
    setTimeout(function () { toast.style.display = 'none'; }, 2500);
  }

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Public API ────────────────────────────────────────────────────────────
  window.backtranslation = { analyze: analyze };

})();
