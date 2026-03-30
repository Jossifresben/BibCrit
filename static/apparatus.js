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

  // ── DOM refs ─────────────────────────────────────────────────────────────
  var selBook       = document.getElementById('sel-book');
  var selChapter    = document.getElementById('sel-chapter');
  var selVerse      = document.getElementById('sel-verse');
  var refInput      = document.getElementById('ref-input');
  var btnAnalyze    = document.getElementById('btn-analyze');
  var emptyState    = document.getElementById('empty-state');
  var loadingState  = document.getElementById('loading-state');
  var apparatusGrid = document.getElementById('apparatus-grid');
  var mtText        = document.getElementById('mt-text');
  var lxxText       = document.getElementById('lxx-text');
  var mtMeta        = document.getElementById('mt-meta');
  var analysisPanel = document.getElementById('analysis-panel');
  var exportRow     = document.getElementById('export-row');

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
  function analyze(ref) {
    if (!ref) return;
    currentRef = ref;
    refInput.value = ref;

    emptyState.style.display    = 'none';
    apparatusGrid.style.display = 'none';
    loadingState.style.display  = 'flex';

    fetch('/api/divergence?ref=' + encodeURIComponent(ref))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        loadingState.style.display = 'none';
        if (data.error) {
          showError(data.error);
          return;
        }
        currentData = data;
        renderApparatus(data);
        apparatusGrid.style.display = 'grid';
        exportRow.style.display     = 'flex';
        updateBudgetBar();
      })
      .catch(function () {
        loadingState.style.display = 'none';
        showError('Network error — please try again.');
      });
  }

  function renderApparatus(data) {
    var mtMap  = buildWordMap(data.divergences || [], 'mt_word');
    var lxxMap = buildWordMap(data.divergences || [], 'lxx_word');

    mtText.innerHTML  = renderWords(data.mt_words  || [], mtMap,  'mt');
    lxxText.innerHTML = renderWords(data.lxx_words || [], lxxMap, 'lxx');

    var count = (data.divergences || []).length;
    mtMeta.innerHTML = count
      ? '<span class="div-count">\u2726 ' + count + ' divergence' + (count === 1 ? '' : 's') + ' detected</span>'
      : '';

    if (data.divergences && data.divergences.length > 0) {
      showDivergenceCard(data.divergences[0], 0);
    } else {
      analysisPanel.innerHTML = '<p class="analysis-hint">No significant divergences detected.</p>';
    }
  }

  function buildWordMap(divergences, field) {
    var map = {};
    divergences.forEach(function (div, i) {
      var word = (div[field] || '').split('(')[0].trim();
      if (word) map[word] = i;
    });
    return map;
  }

  function renderWords(words, divMap, tradition) {
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
        return '<span class="word divergent divergent-' + tradition
          + '" data-div-idx="' + divIdx
          + '" title="' + escapeHtml(title) + '">'
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
      showDivergenceCard(currentData.divergences[idx], idx);
    }
  });

  function showDivergenceCard(div, idx) {
    var tier      = confidenceTier(div.confidence);
    var tierClass = tier.toLowerCase();

    document.querySelectorAll('.word.divergent').forEach(function (el) {
      el.classList.remove('active-divergence');
    });
    document.querySelectorAll('.word.divergent[data-div-idx="' + idx + '"]').forEach(function (el) {
      el.classList.add('active-divergence');
    });

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
      : '';

    analysisPanel.innerHTML =
      '<div class="divergence-card">'
      + '<div class="div-card-header">'
      +   '<span class="div-words">' + escapeHtml(div.mt_word) + ' \u2192 ' + escapeHtml(div.lxx_word) + '</span>'
      +   '<span class="confidence-badge confidence-' + tierClass + '">' + tier + ' ' + div.confidence.toFixed(2) + '</span>'
      + '</div>'
      + '<div class="div-analysis">' + escapeHtml(div.analysis_technical) + '</div>'
      + hypsHtml
      + citesHtml
      + '</div>';
  }

  // ── Export ─────────────────────────────────────────────────────────────────
  document.getElementById('btn-sbl').addEventListener('click', function () {
    if (!currentRef) return;
    fetch('/api/divergence/export/sbl?ref=' + encodeURIComponent(currentRef))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { showToast('\u26a0 ' + data.error); return; }
        copyToClipboard((data.footnotes || []).join('\n\n'));
        showToast('SBL footnote copied to clipboard');
      });
  });

  document.getElementById('btn-bibtex').addEventListener('click', function () {
    if (!currentRef) return;
    fetch('/api/divergence/export/bibtex?ref=' + encodeURIComponent(currentRef))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { showToast('\u26a0 ' + data.error); return; }
        copyToClipboard(data.bibtex || '');
        showToast('BibTeX entries copied to clipboard');
      });
  });

  document.getElementById('btn-share').addEventListener('click', function () {
    var url = window.location.origin + '/divergence?ref=' + encodeURIComponent(currentRef);
    copyToClipboard(url);
    showToast('Link copied to clipboard');
  });

  document.getElementById('btn-save').addEventListener('click', function () {
    if (!currentRef) return;
    var bookmarks = JSON.parse(localStorage.getItem('bibcrit_bookmarks') || '[]');
    if (!bookmarks.includes(currentRef)) {
      bookmarks.push(currentRef);
      localStorage.setItem('bibcrit_bookmarks', JSON.stringify(bookmarks));
    }
    showToast('Saved to bookmarks');
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
        if (capEl)   capEl.textContent   = '$' + (data.cap_usd  || 5).toFixed(2);
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
