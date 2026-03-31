/**
 * apparatus.js — BibCrit MT/LXX Divergence Analyzer UI
 *
 * Responsibilities:
 *   - Corpus browser: cascading book/chapter/verse selects via API
 *   - Fetch and render divergence analysis from /api/divergence
 *   - Highlight divergent words in MT and LXX columns
 *   - Click word → show divergence card in analysis panel
 *   - Export: SBL footnote + BibTeX via copy-to-clipboard
 *   - Budget bar: fetch + render from /api/budget
 */

(function () {
  'use strict';

  // ── State ────────────────────────────────────────────────────────────────
  var currentData = null;
  var currentRef  = '';

  // ── Color palettes ────────────────────────────────────────────────────────
  // Each translation_idiom gets a unique color; other types get a fixed type color
  var IDIOM_COLORS = [
    { border: '#c0522a', bg: '#fde8e0' },   // terracotta
    { border: '#2a7a5e', bg: '#d8f5ec' },   // teal
    { border: '#6b42b8', bg: '#ede4f8' },   // violet
    { border: '#a07000', bg: '#fff0c0' },   // amber
    { border: '#1e6fa8', bg: '#d8edf8' },   // sky blue
    { border: '#8a3060', bg: '#f8ddef' },   // rose
  ];
  var TYPE_COLORS = {
    'different_vorlage':    { border: '#3d6b45', bg: '#e6f4eb' },   // forest green
    'omission':             { border: '#7a4a20', bg: '#f5ece0' },   // sienna
    'addition':             { border: '#1a5c8c', bg: '#e4f0f8' },   // royal blue
    'scribal_error':        { border: '#8c6820', bg: '#fdf5dc' },   // ochre
    'theological_tendency': { border: '#8c2030', bg: '#f8e4e8' },   // crimson
    'grammatical_shift':    { border: '#5a6878', bg: '#edf0f2' },   // slate
  };

  // ── DOM refs ─────────────────────────────────────────────────────────────
  var selBook       = document.getElementById('sel-book');
  var selChapter    = document.getElementById('sel-chapter');
  var selVerse      = document.getElementById('sel-verse');
  var refInput      = document.getElementById('ref-input');
  var btnAnalyze    = document.getElementById('btn-analyze');
  var emptyState    = document.getElementById('empty-state');
  var loadingState  = document.getElementById('loading-state');
  var apparatusGrid = document.getElementById('apparatus-grid');
  var tabsArea        = document.getElementById('tabs-area');
  var tabsNav         = document.getElementById('tabs-nav');
  var tabsBody        = document.getElementById('tabs-body');
  var mtText          = document.getElementById('mt-text');
  var lxxText         = document.getElementById('lxx-text');
  var mtMeta          = document.getElementById('mt-meta');
  var exportRow       = document.getElementById('export-row');
  var passageHeading  = document.getElementById('passage-heading');

  // Guard: only run on the divergence page
  if (!selBook || !btnAnalyze) return;

  // ── Init ──────────────────────────────────────────────────────────────────
  fetchBooks();
  updateBudgetBar();

  // Featured reference links
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
    'Isaiah 7:14', 'Genesis 1:1', 'Psalm 22:1', 'Deuteronomy 32:8',
    'Exodus 3:14', 'Micah 5:2', 'Numbers 24:17', 'Amos 9:11',
    'Jeremiah 31:31', 'Isaiah 53:7', 'Zechariah 9:9', 'Isaiah 9:6',
    'Genesis 3:15', 'Psalm 2:7', 'Isaiah 11:1', 'Joel 3:1'
  ];
  var _lastRandom = '';
  var btnRandom = document.getElementById('btn-random');
  if (btnRandom) {
    btnRandom.addEventListener('click', function () {
      var pool = _randomPassages.filter(function (r) { return r !== _lastRandom; });
      var ref  = pool[Math.floor(Math.random() * pool.length)];
      _lastRandom = ref;
      analyze(ref);
    });
  }

  // ── Corpus browser ────────────────────────────────────────────────────────
  function fetchBooks() {
    fetch('/api/books?tradition=MT')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        (data.books || []).forEach(function (book) {
          var opt = document.createElement('option');
          opt.value = book;
          opt.textContent = book;
          selBook.appendChild(opt);
        });
      })
      .catch(function () {});
  }

  selBook.addEventListener('change', function () {
    var book = selBook.value;
    selChapter.innerHTML = '<option value="">Ch\u2026</option>';
    selChapter.disabled = !book;
    selVerse.innerHTML = '<option value="">Vs\u2026</option>';
    selVerse.disabled = true;
    if (!book) return;
    fetch('/api/chapters?book=' + encodeURIComponent(book) + '&tradition=MT')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        (data.chapters || []).forEach(function (ch) {
          var opt = document.createElement('option');
          opt.value = ch;
          opt.textContent = ch;
          selChapter.appendChild(opt);
        });
        selChapter.disabled = false;
      });
  });

  selChapter.addEventListener('change', function () {
    var book = selBook.value;
    var ch   = selChapter.value;
    selVerse.innerHTML = '<option value="">Vs\u2026</option>';
    selVerse.disabled = !ch;
    if (!ch) return;
    fetch('/api/verses?book=' + encodeURIComponent(book) + '&chapter=' + ch + '&tradition=MT')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        (data.verses || []).forEach(function (v) {
          var opt = document.createElement('option');
          opt.value = v;
          opt.textContent = v;
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

  // ── Analysis fetch + render ───────────────────────────────────────────────
  var _activeStream = null;
  var _timerInterval = null;
  var _elapsedSecs = 0;

  function analyze(ref) {
    if (!ref) return;
    currentRef = ref;
    refInput.value = ref;

    // Close any previous stream
    if (_activeStream) { _activeStream.close(); _activeStream = null; }
    clearInterval(_timerInterval);

    emptyState.style.display    = 'none';
    apparatusGrid.style.display = 'none';
    tabsArea.style.display      = 'none';
    exportRow.style.display     = 'none';
    if (passageHeading) passageHeading.style.display = 'none';
    loadingState.style.display  = 'flex';
    setLoadingStep('Preparing…');
    startTimer();

    var es = new EventSource('/api/divergence/stream?ref=' + encodeURIComponent(ref) + '&lang=' + (window.bibcritLang || 'en'));
    _activeStream = es;

    es.onmessage = function (e) {
      var msg = JSON.parse(e.data);

      if (msg.type === 'step') {
        setLoadingStep(msg.msg);
      } else if (msg.type === 'done') {
        es.close();
        _activeStream = null;
        stopTimer();
        loadingState.style.display = 'none';
        currentData = msg.data;
        renderApparatus(msg.data);
        if (passageHeading) passageHeading.style.display = 'block';
        apparatusGrid.style.display = 'grid';
        tabsArea.style.display      = 'block';
        exportRow.style.display     = 'flex';
        // Keep the URL bar in sync so the Share modal always reflects the current passage
        history.replaceState(null, '', '/divergence?ref=' + encodeURIComponent(ref));
        updateBudgetBar();

        // Inject Scholar Rating, Copy, Download into export-row (once only)
        if (window.ResultActions) {
          ResultActions.init({
            toolName: 'divergence',
            getReference: function() { return currentRef; },
            getResultData: function() { return currentData || {}; },
          });
        }
      } else if (msg.type === 'error') {
        es.close();
        _activeStream = null;
        stopTimer();
        loadingState.style.display = 'none';
        showError(msg.msg);
      }
    };

    es.onerror = function () {
      es.close();
      _activeStream = null;
      stopTimer();
      loadingState.style.display = 'none';
      showError(window.t('err_connection', 'Connection lost — please try again.'));
    };
  }

  function setLoadingStep(msg) {
    var stepEl = document.getElementById('loading-step');
    if (stepEl) stepEl.textContent = msg;
  }

  function startTimer() {
    _elapsedSecs = 0;
    var timerEl = document.getElementById('loading-timer');
    if (timerEl) timerEl.textContent = '';
    _timerInterval = setInterval(function () {
      _elapsedSecs++;
      if (timerEl) timerEl.textContent = _elapsedSecs + 's elapsed';
    }, 1000);
  }

  function stopTimer() {
    clearInterval(_timerInterval);
    _timerInterval = null;
  }

  function renderApparatus(data) {
    // Passage heading
    if (passageHeading) {
      var ref = data.reference || currentRef;
      passageHeading.innerHTML =
        '<span class="ph-ref">' + escapeHtml(ref) + '</span>';
    }

    // Sort: translation_idiom first, grammatical_shift last, others in middle
    data.divergences = sortDivergences(data.divergences || []);

    // One color map for everything: unique per idiom, fixed type color for others
    var colorMap = buildTabColorMap(data.divergences);

    var mtMap  = buildWordMap(data.divergences, 'mt_word');
    var lxxMap = buildWordMap(data.divergences, 'lxx_word');

    mtText.innerHTML  = renderWords(data.mt_words  || [], mtMap,  'mt',  colorMap);
    lxxText.innerHTML = renderWords(data.lxx_words || [], lxxMap, 'lxx', colorMap);

    var count = data.divergences.length;
    mtMeta.innerHTML = count
      ? '<span class="div-count">\u2726 ' + count + ' divergence' + (count === 1 ? '' : 's') + ' detected</span>'
      : '';

    buildTabs(data, colorMap);
  }

  function sortDivergences(divs) {
    var ORDER = {
      'translation_idiom':    0,
      'different_vorlage':    1,
      'omission':             2,
      'addition':             3,
      'scribal_error':        4,
      'theological_tendency': 5,
      'grammatical_shift':    6,
    };
    return divs.slice().sort(function (a, b) {
      var oa = ORDER[a.divergence_type] !== undefined ? ORDER[a.divergence_type] : 7;
      var ob = ORDER[b.divergence_type] !== undefined ? ORDER[b.divergence_type] : 7;
      return oa - ob;
    });
  }

  // One color map: unique per idiom instance, fixed type color for all other types
  function buildTabColorMap(divs) {
    var map = {};
    var idiomCount = 0;
    divs.forEach(function (div, i) {
      if (div.divergence_type === 'translation_idiom') {
        map[i] = IDIOM_COLORS[idiomCount % IDIOM_COLORS.length];
        idiomCount++;
      } else if (TYPE_COLORS[div.divergence_type]) {
        map[i] = TYPE_COLORS[div.divergence_type];
      }
    });
    return map;
  }

  // ── Tabs ──────────────────────────────────────────────────────────────────
  function buildTabs(data, colorMap) {
    tabsNav.innerHTML  = '';
    tabsBody.innerHTML = '';

    var divs = data.divergences || [];

    if (!divs.length) {
      var noDiv = document.createElement('div');
      noDiv.className = 'tab-panel active';
      noDiv.id = 'tab-panel-main';
      noDiv.innerHTML = '<p class="analysis-hint">No significant divergences detected.</p>';
      tabsBody.appendChild(noDiv);
      if (data.bibcrit_hypothesis) {
        appendHypothesisTab(data);
      }
      return;
    }

    // Create one tab + panel per divergence
    divs.forEach(function (div, i) {
      var panelId   = 'tab-panel-' + i;
      var typeShort = formatTypeShort(div.divergence_type);
      var color     = colorMap ? colorMap[i] : null;
      var isFirst   = (i === 0);

      // Tab button
      var btn = document.createElement('button');
      btn.className = 'tab-btn' + (isFirst ? ' active' : '');
      btn.role = 'tab';
      btn.dataset.panel = panelId;
      btn.setAttribute('aria-selected', isFirst ? 'true' : 'false');
      btn.innerHTML = '<span class="tab-num">' + (i + 1) + '</span>'
                    + '<span class="tab-type-label">' + escapeHtml(typeShort) + '</span>';

      // Store idiom color data on the button for activateTab to use
      if (color) {
        btn.dataset.idiomBorder = color.border;
        btn.dataset.idiomBg     = color.bg;
        applyTabColor(btn, color, isFirst);
      }

      btn.addEventListener('click', function () { activateTab(panelId); });
      tabsNav.appendChild(btn);

      // Panel
      var panel = document.createElement('div');
      panel.className = 'tab-panel' + (isFirst ? ' active' : '');
      panel.id = panelId;
      panel.innerHTML = buildDivergenceCardHtml(div, i, color);
      tabsBody.appendChild(panel);
    });

    // BibCrit Hypothesis tab
    if (data.bibcrit_hypothesis) {
      appendHypothesisTab(data);
    }
  }

  function appendHypothesisTab(data) {
    var panelId = 'tab-panel-hyp';
    var ref = data.reference || currentRef;
    var btn = document.createElement('button');
    btn.className = 'tab-btn tab-hypothesis';
    btn.role = 'tab';
    btn.dataset.panel = panelId;
    btn.setAttribute('aria-selected', 'false');
    btn.textContent = '\u2726 BibCrit Hypothesis';
    btn.addEventListener('click', function () {
      activateTab(panelId);
      _loadVoteCounts(ref);
    });
    tabsNav.appendChild(btn);

    var panel = document.createElement('div');
    panel.className = 'tab-panel';
    panel.id = panelId;
    panel.innerHTML = renderHypothesisCard(data);
    tabsBody.appendChild(panel);
  }

  function applyTabColor(btn, color, isActive) {
    if (!color) return;
    // Num badge always gets the idiom color
    var numEl = btn.querySelector('.tab-num');
    if (numEl) {
      numEl.style.background = color.border;
      numEl.style.color = 'white';
    }
    // Active state: colored border + tinted background
    if (isActive) {
      btn.style.borderColor = color.border;
      btn.style.background  = color.bg;
      btn.style.color       = color.border;
    } else {
      btn.style.borderColor = 'transparent';
      btn.style.background  = '';
      btn.style.color       = '';
    }
  }

  function activateTab(panelId) {
    tabsNav.querySelectorAll('.tab-btn').forEach(function (b) {
      var isActive = b.dataset.panel === panelId;
      b.classList.toggle('active', isActive);
      b.setAttribute('aria-selected', isActive ? 'true' : 'false');
      // Re-apply idiom color state if applicable
      if (b.dataset.idiomBorder) {
        applyTabColor(b, { border: b.dataset.idiomBorder, bg: b.dataset.idiomBg }, isActive);
      }
    });
    tabsBody.querySelectorAll('.tab-panel').forEach(function (p) {
      p.classList.toggle('active', p.id === panelId);
    });
  }

  function formatTypeShort(type) {
    // Abbreviate long type names for tab labels
    var map = {
      'theological_tendency': 'Theological',
      'scribal_error':        'Scribal Error',
      'different_vorlage':    'Vorlage',
      'translation_idiom':    'Idiom',
      'grammatical_shift':    'Grammar',
      'omission':             'Omission',
      'addition':             'Addition'
    };
    return map[type] || formatType(type);
  }

  function buildWordMap(divergences, field) {
    var map = {};
    divergences.forEach(function (div, i) {
      // Strip parenthetical gloss: "אֵלִי אֵלִי (My God...)" → "אֵלִי אֵלִי"
      var phrase = (div[field] || '').split('(')[0].trim();
      // Map every individual token so multi-word phrases highlight each word
      phrase.split(/\s+/).forEach(function (token) {
        if (token) map[token] = i;
      });
    });
    return map;
  }

  function renderWords(words, divMap, tradition, colorMap) {
    if (!words.length) {
      return '<em class="no-data">No ' + tradition.toUpperCase() + ' data loaded for this passage</em>';
    }
    return words.map(function (w) {
      var isDivergent = (w.word_text in divMap) || (w.lemma in divMap);
      var divIdx = (w.word_text in divMap) ? divMap[w.word_text]
                 : (w.lemma in divMap)     ? divMap[w.lemma]
                 : -1;
      var title = w.lemma + (w.morph ? ' \u00b7 ' + w.morph : '');
      if (isDivergent) {
        var color = (colorMap && divIdx >= 0) ? colorMap[divIdx] : null;
        var style = color
          ? ' style="background:' + color.bg + ';border-bottom:2px solid ' + color.border + '"'
          : '';
        return '<span class="word divergent divergent-' + tradition + '"'
          + ' data-div-idx="' + divIdx + '"'
          + style
          + ' title="' + escapeHtml(title) + '">'
          + escapeHtml(w.word_text) + '</span>';
      }
      return '<span class="word" title="' + escapeHtml(title) + '">'
        + escapeHtml(w.word_text) + '</span>';
    }).join(' ');
  }

  document.addEventListener('click', function (e) {
    var el = e.target.closest('.word.divergent');
    if (!el || !currentData) return;
    var idx = parseInt(el.dataset.divIdx, 10);
    if (!isNaN(idx) && currentData.divergences[idx]) {
      // Highlight the clicked word
      document.querySelectorAll('.word.divergent').forEach(function (w) {
        w.classList.remove('active-divergence');
      });
      document.querySelectorAll('.word.divergent[data-div-idx="' + idx + '"]').forEach(function (w) {
        w.classList.add('active-divergence');
      });
      // Switch to the corresponding tab
      activateTab('tab-panel-' + idx);
      // Scroll tabs area into view on mobile
      if (tabsArea) tabsArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });

  function buildDivergenceCardHtml(div, idx, color) {
    var tier      = confidenceTier(div.confidence);
    var tierClass = tier.toLowerCase();

    var borderStyle = color
      ? 'border-left:3px solid ' + color.border + ';background:' + color.bg + ';'
      : '';

    var hypsHtml = (div.hypotheses || []).map(function (h) {
      var hTier  = confidenceTier(h.confidence);
      var hClass = hTier.toLowerCase();
      return '<div class="hypothesis confidence-' + hClass + '">'
        + '<span class="confidence-badge confidence-' + hClass + '">' + hTier + ' ' + h.confidence.toFixed(2) + '</span>'
        + ' <span class="hyp-type">' + escapeHtml(formatType(h.type)) + '</span>'
        + '<p class="hyp-explanation">' + escapeHtml(h.explanation) + '</p>'
        + '</div>';
    }).join('');

    var citesHtml = (div.citations && div.citations.length)
      ? '<div class="div-citations">\uD83D\uDCDA ' + escapeHtml(div.citations.join(' \u00b7 ')) + '</div>'
      : '<div class="div-citations div-no-citations">No published sources identified for this divergence.</div>';

    return '<div class="divergence-card">'
      + '<div class="div-card-header">'
      +   '<span class="div-words">' + escapeHtml(div.mt_word) + ' \u2192 ' + escapeHtml(div.lxx_word) + '</span>'
      +   '<span class="confidence-badge confidence-' + tierClass + '">' + tier + ' ' + div.confidence.toFixed(2) + '</span>'
      + '</div>'
      + '<div class="div-analysis"' + (borderStyle ? ' style="' + borderStyle + '"' : '') + '>'
      +   escapeHtml(div.analysis_technical)
      + '</div>'
      + hypsHtml
      + citesHtml
      + '</div>';
  }

  function renderHypothesisCard(data) {
    var h = data && data.bibcrit_hypothesis;
    if (!h) return '';
    var tier      = confidenceTier(h.confidence || 0);
    var tierClass = tier.toLowerCase();
    var model     = data.model_version || 'claude sonnet 4.5';
    var modelDisplay = model.replace(/^claude-/, 'claude ').replace(/-(\d{8})$/, '').replace(/-/g, '.');
    var ref = data.reference || currentRef;

    return '<div class="bibcrit-hypothesis-card">'
      + '<div class="hyp-card-header">'
      +   '<span class="hyp-card-icon">\u2726</span>'
      +   '<span class="hyp-card-title">BibCrit Hypothesis</span>'
      +   '<span class="hyp-card-subtitle">' + escapeHtml(h.title || '') + '</span>'
      +   '<span class="confidence-badge confidence-' + tierClass + '">' + tier + ' ' + (h.confidence || 0).toFixed(2) + '</span>'
      + '</div>'
      + '<p class="hyp-card-plain">' + escapeHtml(h.plain || '') + '</p>'
      + '<p class="hyp-card-reasoning">' + escapeHtml(h.reasoning || '') + '</p>'
      + '<p class="hyp-card-generated">generated by ' + escapeHtml(modelDisplay) + '</p>'
      + '</div>';
  }

  // ── Vote handling ──────────────────────────────────────────────────────────
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.vote-btn');
    if (!btn) return;
    var row = document.getElementById('hyp-vote-row');
    if (!row) return;
    var ref = row.dataset.ref;
    var direction = btn.classList.contains('vote-up') ? 'up' : 'down';
    var voteKey = 'bibcrit_vote_' + ref;
    var prevVote = localStorage.getItem(voteKey);  // 'up', 'down', or null

    // Determine action: clicking same direction retracts, clicking opposite switches
    var action = 'cast';
    if (prevVote === direction) {
      action = 'retract';
    } else if (prevVote && prevVote !== direction) {
      // Retract previous first, then cast new — do two calls
      fetch('/api/hypothesis/vote?ref=' + encodeURIComponent(ref)
            + '&direction=' + prevVote + '&action=retract', { method: 'POST' });
    }

    fetch('/api/hypothesis/vote?ref=' + encodeURIComponent(ref)
          + '&direction=' + direction + '&action=' + action, { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) return;
        _applyVoteCounts(data.upvotes, data.downvotes);
        if (action === 'retract') {
          localStorage.removeItem(voteKey);
          _clearVoteHighlight();
        } else {
          localStorage.setItem(voteKey, direction);
          _highlightVote(direction);
        }
      });
  });

  function _loadVoteCounts(ref) {
    fetch('/api/hypothesis/votes?ref=' + encodeURIComponent(ref))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) return;
        _applyVoteCounts(data.upvotes, data.downvotes);
        // Restore previous vote highlight from localStorage
        var prevVote = localStorage.getItem('bibcrit_vote_' + ref);
        if (prevVote) _highlightVote(prevVote);
      })
      .catch(function () {
        var el = document.getElementById('upvote-count');
        if (el) el.textContent = '0';
      });
  }

  function _applyVoteCounts(upvotes, downvotes) {
    var el = document.getElementById('upvote-count');
    if (el) el.textContent = upvotes;
  }

  function _highlightVote(direction) {
    var upBtn   = document.getElementById('vote-up');
    var downBtn = document.getElementById('vote-down');
    if (!upBtn || !downBtn) return;
    upBtn.classList.toggle('vote-active', direction === 'up');
    downBtn.classList.toggle('vote-active', direction === 'down');
  }

  function _clearVoteHighlight() {
    var upBtn   = document.getElementById('vote-up');
    var downBtn = document.getElementById('vote-down');
    if (upBtn)   upBtn.classList.remove('vote-active');
    if (downBtn) downBtn.classList.remove('vote-active');
  }

  // ── Export ─────────────────────────────────────────────────────────────────
  document.getElementById('btn-sbl').addEventListener('click', function () {
    if (!currentRef) return;
    fetch('/api/divergence/export/sbl?ref=' + encodeURIComponent(currentRef))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { showToast('\u26a0 ' + data.error); return; }
        copyToClipboard((data.footnotes || []).join('\n\n'));
        showToast(window.t('toast_sbl_copied', 'SBL footnote copied to clipboard'));
      });
  });

  document.getElementById('btn-bibtex').addEventListener('click', function () {
    if (!currentRef) return;
    fetch('/api/divergence/export/bibtex?ref=' + encodeURIComponent(currentRef))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { showToast('\u26a0 ' + data.error); return; }
        copyToClipboard(data.bibtex || '');
        showToast(window.t('toast_bibtex_copied', 'BibTeX entries copied to clipboard'));
      });
  });

  document.getElementById('btn-share').addEventListener('click', function () {
    var url = window.location.href;  // URL is kept current via history.replaceState
    // Populate + open the global share modal (already defined in base.html + global.js)
    var shareUrlEl = document.getElementById('share-url');
    var shareQrEl  = document.getElementById('share-qr');
    var shareModal = document.getElementById('share-modal');
    if (!shareModal) return;
    if (shareUrlEl) shareUrlEl.value = url;
    // Regenerate QR for this specific passage URL
    if (shareQrEl) {
      shareQrEl.innerHTML = '';
      if (typeof QRCode !== 'undefined') {
        var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        new QRCode(shareQrEl, {
          text: url,
          width: 200,
          height: 200,
          colorDark:  isDark ? '#e2e4dc' : '#1a1a1a',
          colorLight: isDark ? '#1a1d18' : '#ffffff',
          correctLevel: QRCode.CorrectLevel.M
        });
      }
    }
    shareModal.classList.add('active');
  });

  // ── Budget bar ─────────────────────────────────────────────────────────────
  function updateBudgetBar() {
    fetch('/api/budget')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var spendEl  = document.getElementById('budget-spend');
        var capEl    = document.getElementById('budget-cap');
        var barEl    = document.getElementById('budget-bar');
        var pctEl    = document.getElementById('budget-pct');
        var donateEl = document.getElementById('budget-donate-btn');

        if (!barEl) return;

        var pct = data.pct || 0;
        barEl.style.width = Math.min(100, pct) + '%';
        barEl.className   = 'budget-fill'
          + (pct >= 100 ? ' critical' : pct >= 80 ? ' warning' : '');

        if (spendEl) spendEl.textContent = '$' + (data.spend_usd || 0).toFixed(2);
        if (capEl)   capEl.textContent   = '$' + (data.cap_usd  || 10).toFixed(2);
        if (pctEl)   pctEl.textContent   = pct + '%';

        if (donateEl && pct >= 80) donateEl.style.display = 'inline-block';

        if (pct >= 100) {
          var overlay = document.getElementById('donation-modal-overlay');
          if (overlay) overlay.classList.add('active');
        }
      })
      .catch(function () {});
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function confidenceTier(score) {
    if (score >= 0.75) return 'HIGH';
    if (score >= 0.45) return 'MEDIUM';
    return 'LOW';
  }

  function formatType(type) {
    return (type || '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showError(msg) {
    emptyState.style.display = 'block';
    emptyState.innerHTML = '<div class="error-msg"><p>\u26a0\ufe0f ' + escapeHtml(msg) + '</p>'
      + '<button onclick="location.reload()">Try again</button></div>';
  }

  function showToast(msg) {
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.style.display = 'block';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () { toast.style.display = 'none'; }, 3000);
  }

  function copyToClipboard(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(function () { legacyCopy(text); });
    } else {
      legacyCopy(text);
    }
  }

  function legacyCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
  }

  // Expose analyze() for auto-trigger from template
  window.apparatus = { analyze: analyze };

})();
