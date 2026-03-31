/* BibCrit — result-actions: Scholar Rating + Copy + Download injected into export-row */
(function(global) {
  'use strict';

  function init(options) {
    /*
      options = {
        toolName: 'theological',
        getReference: function() { return _currentRef; },
        getResultData: function() { return _lastData || {}; },
        getSvgEl: function() { return null; },  // optional, for genealogy
      }
      Injects Scholar Rating, Copy, Download into #export-row (prepended before existing buttons).
    */
    var exportRow = document.getElementById('export-row');
    if (!exportRow || exportRow._raInitialized) return;
    exportRow._raInitialized = true;

    // ── Scholar Rating ─────────────────────────────────────────────
    var ratingWrap = document.createElement('span');
    ratingWrap.className = 'ra-rating-wrap';

    var ratingLabel = document.createElement('span');
    ratingLabel.className = 'vote-label';
    ratingLabel.textContent = window.t('ra_scholar_rating', 'Scholar rating:');

    var upBtn = document.createElement('button');
    upBtn.className = 'vote-btn vote-up ra-vote-btn';
    upBtn.title = window.t('ra_upvote_title', 'Upvote');
    upBtn.innerHTML = '▲ <span class="vote-count">0</span>';

    var downBtn = document.createElement('button');
    downBtn.className = 'vote-btn vote-down ra-vote-btn';
    downBtn.title = window.t('ra_downvote_title', 'Downvote');
    downBtn.innerHTML = '▼';

    var raSep = document.createElement('span');
    raSep.className = 'btn-export-sep';

    ratingWrap.appendChild(ratingLabel);
    ratingWrap.appendChild(upBtn);
    ratingWrap.appendChild(downBtn);

    // ── Copy ───────────────────────────────────────────────────────
    var copyBtn = document.createElement('button');
    copyBtn.className = 'btn-export';
    copyBtn.title = window.t('ra_copy_title', 'Copy analysis to clipboard');
    copyBtn.innerHTML = window.t('ra_copy_btn', '📋 Copy');

    // ── Download ───────────────────────────────────────────────────
    var dlBtn = document.createElement('button');
    dlBtn.className = 'btn-export';
    dlBtn.title = window.t('ra_download_title', 'Download analysis');
    dlBtn.innerHTML = window.t('ra_download_btn', '⬇ Download');

    var dlSep = document.createElement('span');
    dlSep.className = 'btn-export-sep';

    // Prepend: [rating] [sep] [Copy] [Download] [sep] [existing buttons...]
    exportRow.insertBefore(dlSep, exportRow.firstChild);
    exportRow.insertBefore(dlBtn, dlSep);
    exportRow.insertBefore(copyBtn, dlBtn);
    exportRow.insertBefore(raSep, copyBtn);
    exportRow.insertBefore(ratingWrap, raSep);

    // ── Vote state ─────────────────────────────────────────────────
    var voteKey = 'bibcrit-vote-' + options.toolName + '-' + (options.getReference ? options.getReference() : '');
    var savedVote = localStorage.getItem(voteKey);
    var voteCount = 0;

    function updateVoteUI() {
      var countEl = upBtn.querySelector('.vote-count');
      if (countEl) countEl.textContent = voteCount > 0 ? voteCount : '0';
      upBtn.classList.toggle('vote-active', savedVote === 'up');
      downBtn.classList.toggle('vote-active', savedVote === 'down');
    }

    // Fetch current vote count from server
    var ref = options.getReference ? options.getReference() : '';
    fetch('/api/votes?tool=' + encodeURIComponent(options.toolName) + '&ref=' + encodeURIComponent(ref))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        voteCount = (d.upvotes || 0) - (d.downvotes || 0);
        updateVoteUI();
      })
      .catch(function() { updateVoteUI(); });

    upBtn.addEventListener('click', function() {
      var isActive = savedVote === 'up';
      savedVote = isActive ? null : 'up';
      voteCount += isActive ? -1 : 1;
      if (!isActive && downBtn.classList.contains('vote-active')) voteCount += 1;
      localStorage.setItem(voteKey, savedVote || '');
      updateVoteUI();
      fetch('/api/vote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference: ref, tool: options.toolName, value: isActive ? 0 : 1 }),
      }).catch(function(){});
    });

    downBtn.addEventListener('click', function() {
      var isActive = savedVote === 'down';
      savedVote = isActive ? null : 'down';
      if (!isActive && upBtn.classList.contains('vote-active')) voteCount -= 1;
      localStorage.setItem(voteKey, savedVote || '');
      updateVoteUI();
      fetch('/api/vote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference: ref, tool: options.toolName, value: isActive ? 0 : -1 }),
      }).catch(function(){});
    });

    // ── Copy ───────────────────────────────────────────────────────
    copyBtn.addEventListener('click', function() {
      var data = options.getResultData ? options.getResultData() : {};
      var text = global.ResultActions._toText(data, ref, options.toolName);
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() { _flash(copyBtn, '✓ Copied!'); });
      } else {
        var ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        _flash(copyBtn, '✓ Copied!');
      }
    });

    // ── Download ───────────────────────────────────────────────────
    dlBtn.addEventListener('click', function() {
      var data = options.getResultData ? options.getResultData() : {};
      var safeRef = ref.replace(/[^a-z0-9]/gi, '_');
      var text = global.ResultActions._toText(data, ref, options.toolName);
      _dlBlob(text, 'text/plain', 'bibcrit_' + options.toolName + '_' + safeRef + '.txt');
      // SVG download — any tool that provides getSvgEl gets a .svg file too
      var svgEl = options.getSvgEl ? options.getSvgEl() : null;
      if (svgEl) {
        var svgData = '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(svgEl);
        _dlBlob(svgData, 'image/svg+xml', 'bibcrit_' + options.toolName + '_' + safeRef + '.svg');
      }
    });
  }

  function _flash(btn, label) {
    var orig = btn.innerHTML;
    btn.innerHTML = label;
    setTimeout(function() { btn.innerHTML = orig; }, 1500);
  }

  function _dlBlob(content, mime, filename) {
    var blob = new Blob([content], { type: mime });
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }

  function _resultToText(data, ref, tool) {
    var hr = '─'.repeat(60);
    var lines = [
      'BibCrit — ' + _toolLabel(tool) + ' Analysis',
      'Reference: ' + ref,
      'URL: ' + window.location.href,
      hr,
      '',
    ];

    if (tool === 'divergence') {
      if (data.summary_plain) lines.push('SUMMARY', data.summary_plain, '');
      if (data.summary)       lines.push('TECHNICAL SUMMARY', data.summary, '');
      var divs = data.divergences || [];
      if (divs.length) {
        lines.push('DIVERGENCES (' + divs.length + ')', '');
        divs.forEach(function(d, i) {
          lines.push(
            (i + 1) + '. MT: ' + (d.mt_word || '—') + '  →  LXX: ' + (d.lxx_word || '—') +
            '  [' + (d.divergence_type || '') + '  conf: ' + Math.round((d.confidence||0)*100) + '%]'
          );
          if (d.analysis_plain)    lines.push('   ' + d.analysis_plain);
          if (d.analysis_technical) lines.push('   Technical: ' + d.analysis_technical);
          if (d.dss_witness)       lines.push('   DSS witness: ' + d.dss_witness);
          var hyps = d.hypotheses || [];
          if (hyps.length) {
            lines.push('   Hypotheses:');
            hyps.forEach(function(h) {
              lines.push('     [' + Math.round((h.confidence||0)*100) + '%] ' + (h.type||'') + ' — ' + (h.explanation||''));
            });
          }
          var cits = d.citations || [];
          if (cits.length) lines.push('   Citations: ' + cits.join('; '));
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else if (tool === 'backtranslation') {
      if (data.summary_plain) lines.push('SUMMARY', data.summary_plain, '');
      if (data.summary)       lines.push('TECHNICAL SUMMARY', data.summary, '');
      var words = data.reconstructed_words || [];
      if (words.length) {
        lines.push('RECONSTRUCTED VORLAGE', '');
        words.forEach(function(w) {
          lines.push(
            (w.position || '') + '. LXX: ' + (w.lxx_word || '—') +
            '  →  Vorlage: ' + (w.vorlage_word || '—') +
            '  MT: ' + (w.mt_equivalent || '—') +
            (w.status ? '  [' + w.status + ']' : '') +
            (w.confidence ? '  conf: ' + Math.round(w.confidence*100) + '%' : '')
          );
          if (w.reasoning) lines.push('   ' + w.reasoning);
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else if (tool === 'scribal') {
      if (data.translator_name) lines.push('Translator: ' + data.translator_name, '');
      if (data.overall_plain)   lines.push('OVERALL ASSESSMENT', data.overall_plain, '');
      // Radar scores
      var profile = data.translator_profile || {};
      var profileKeys = ['literalness','anthropomorphism_reduction','messianic_heightening','harmonization','paraphrase_rate'];
      var profileLabels = ['Literalness','Anthropomorphism Reduction','Messianic Heightening','Harmonization','Paraphrase Rate'];
      var hasProfile = profileKeys.some(function(k) { return profile[k] !== undefined; });
      if (hasProfile) {
        lines.push('DIMENSION SCORES');
        profileKeys.forEach(function(k, i) {
          if (profile[k] !== undefined) {
            lines.push('  ' + profileLabels[i] + ': ' + Math.round(profile[k]*100) + '%');
          }
        });
        lines.push('');
      }
      // Full dimension analysis
      var dims = data.dimensions || [];
      if (dims.length) {
        lines.push('DIMENSION ANALYSIS', '');
        dims.forEach(function(d) {
          var label = (d.dimension || '').replace(/_/g,' ').replace(/\b\w/g, function(c){ return c.toUpperCase(); });
          lines.push(label + ': ' + (d.score !== undefined ? Math.round(d.score*100) + '%' : ''));
          if (d.summary_plain) lines.push('   ' + d.summary_plain);
          if (d.summary)       lines.push('   Technical: ' + d.summary);
          var examples = d.examples || [];
          if (examples.length) {
            lines.push('   Examples:');
            examples.forEach(function(ex) {
              lines.push(
                '     ' + (ex.reference||'') + '  MT: ' + (ex.mt_text||'—') +
                '  LXX: ' + (ex.lxx_text||'—')
              );
              if (ex.note) lines.push('     → ' + ex.note);
            });
          }
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else if (tool === 'numerical') {
      if (data.overall_plain) lines.push('SUMMARY', data.overall_plain, '');
      var sa = data.systematic_analysis || {};
      if (sa.pattern_plain) lines.push('PATTERN', sa.pattern_plain, '');
      if (sa.pattern)       lines.push('TECHNICAL PATTERN', sa.pattern, '');
      var figs = data.figures || [];
      if (figs.length) {
        lines.push('FIGURES (' + figs.length + ')', '');
        figs.forEach(function(f) {
          lines.push(
            (f.name || '') + ':  MT=' + (f.mt_value !== undefined ? f.mt_value : '—') +
            '  LXX=' + (f.lxx_value !== undefined ? f.lxx_value : '—') +
            (f.sp_value !== undefined && f.sp_value !== null ? '  SP=' + f.sp_value : '') +
            (f.divergence_type ? '  [' + f.divergence_type + ']' : '')
          );
          if (f.plain_note) lines.push('   ' + f.plain_note);
        });
        lines.push('');
      }
      var theories = data.theories || [];
      if (theories.length) {
        lines.push('COMPETING THEORIES', '');
        theories.forEach(function(t, i) {
          lines.push(
            (i + 1) + '. ' + (t.name || '') +
            '  score=' + (t.score !== undefined ? t.score : '—') +
            '  conf=' + Math.round((t.confidence||0)*100) + '%'
          );
          if (t.summary_plain) lines.push('   ' + t.summary_plain);
          if (t.summary)       lines.push('   Technical: ' + t.summary);
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else if (tool === 'dss') {
      if (data.synthesis_plain) lines.push('SYNTHESIS', data.synthesis_plain, '');
      if (data.synthesis)       lines.push('TECHNICAL SYNTHESIS', data.synthesis, '');
      var mss = data.dss_manuscripts || [];
      if (mss.length) {
        lines.push('MANUSCRIPTS (' + mss.length + ')', '');
        mss.forEach(function(ms) {
          lines.push(
            (ms.siglum || '') + ' — ' + (ms.full_name || '') +
            '  [' + (ms.alignment || '') + ']' +
            (ms.alignment_confidence ? '  ' + Math.round(ms.alignment_confidence*100) + '%' : '')
          );
          if (ms.verse_present && ms.dss_text) lines.push('   Text: ' + ms.dss_text);
          if (ms.overall_note) lines.push('   ' + ms.overall_note);
          var dssDiv = ms.divergences || [];
          dssDiv.forEach(function(d) {
            lines.push(
              '   • MT: ' + (d.mt_reading||'—') + '  LXX: ' + (d.lxx_reading||'—') +
              '  DSS: ' + (d.dss_reading||'—') + '  [' + (d.classification||'') + ']'
            );
            if (d.textual_implication) lines.push('     ' + d.textual_implication);
          });
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else if (tool === 'theological') {
      if (data.summary_plain)    lines.push('SUMMARY', data.summary_plain, '');
      if (data.summary)          lines.push('TECHNICAL SUMMARY', data.summary, '');
      if (data.dominant_strategy) lines.push('Dominant strategy: ' + data.dominant_strategy, '');
      if (data.overall_plain)    lines.push('Overall: ' + data.overall_plain, '');
      var revs = data.revisions || [];
      if (revs.length) {
        lines.push('THEOLOGICAL REVISIONS (' + revs.length + ')', '');
        revs.forEach(function(r, i) {
          lines.push(
            (i + 1) + '. [' + (r.revision_type || r.category || '') + ']' +
            (r.tradition ? '  ' + r.tradition : '') +
            '  conf=' + Math.round((r.confidence||0)*100) + '%'
          );
          if (r.reference || r.passage) lines.push('   Passage: ' + (r.reference || r.passage));
          if (r.mt_reading)     lines.push('   MT reading: ' + r.mt_reading);
          if (r.revised_reading) lines.push('   Revised: ' + r.revised_reading);
          var plain = r.evidence_plain || r.plain_description || r.plain || '';
          if (plain) lines.push('   ' + plain);
          if (r.evidence) lines.push('   Technical: ' + r.evidence);
          var scits = r.scholarly_citations || [];
          if (scits.length) lines.push('   Citations: ' + scits.join('; '));
          if (r.counter_arguments) lines.push('   Counter-argument: ' + r.counter_arguments);
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else if (tool === 'patristic') {
      if (data.period_summary)              lines.push('PERIOD SUMMARY', data.period_summary, '');
      if (data.transmission_synthesis_plain) lines.push('SYNTHESIS', data.transmission_synthesis_plain, '');
      if (data.transmission_synthesis)      lines.push('TECHNICAL SYNTHESIS', data.transmission_synthesis, '');
      // Text form distribution
      var tfd = data.text_form_distribution || {};
      var tfdKeys = Object.keys(tfd);
      if (tfdKeys.length) {
        lines.push('TEXT FORM DISTRIBUTION');
        tfdKeys.forEach(function(k) { lines.push('  ' + k + ': ' + tfd[k]); });
        lines.push('');
      }
      var cits = data.citations || [];
      if (cits.length) {
        lines.push('PATRISTIC CITATIONS (' + cits.length + ')', '');
        cits.forEach(function(c, i) {
          lines.push(
            (i + 1) + '. ' + (c.father || '') +
            (c.dates_ce || c.dates ? ' (' + (c.dates_ce || c.dates) + ')' : '') +
            (c.region ? '  ' + c.region : '') +
            '  — ' + (c.work || '') +
            (c.chapter_section ? ' ' + c.chapter_section : '') +
            '  [' + (c.text_form || '') + ']' +
            (c.text_form_confidence ? '  ' + Math.round(c.text_form_confidence*100) + '%' : '')
          );
          if (c.cited_text)           lines.push('   "' + c.cited_text + '"');
          if (c.text_form_note)       lines.push('   Text form: ' + c.text_form_note);
          if (c.theological_use)      lines.push('   Theological use: ' + c.theological_use);
          if (c.transmission_implication) lines.push('   Transmission: ' + c.transmission_implication);
          lines.push('');
        });
      }
      // Notable variants
      var nvars = data.notable_variants || [];
      if (nvars.length) {
        lines.push('NOTABLE VARIANTS', '');
        nvars.forEach(function(v, i) {
          lines.push((i+1) + '. "' + (v.reading||'') + '"  [' + (v.text_form_alignment||'') + ']');
          if (v.fathers_using_it) lines.push('   Attested in: ' + (v.fathers_using_it||[]).join(', '));
          if (v.significance)     lines.push('   ' + v.significance);
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else if (tool === 'genealogy') {
      if (data.period_range)         lines.push('Period: ' + data.period_range, '');
      if (data.archetype_description) lines.push('ARCHETYPE', data.archetype_description, '');
      if (data.transmission_plain)   lines.push('TRANSMISSION HISTORY', data.transmission_plain, '');
      if (data.transmission_narrative) lines.push('TECHNICAL NARRATIVE', data.transmission_narrative, '');
      var nodes = data.stemma_nodes || [];
      if (nodes.length) {
        lines.push('STEMMA NODES (' + nodes.length + ')', '');
        nodes.forEach(function(n) {
          lines.push(
            '• ' + (n.label || n.id) +
            (n.full_name ? ' (' + n.full_name + ')' : '') +
            (n.date ? '  [' + n.date + ']' : '') +
            (n.type ? '  type:' + n.type : '') +
            (n.tradition ? '  tradition:' + n.tradition : '') +
            (n.language ? '  lang:' + n.language : '')
          );
          if (n.description) lines.push('  ' + n.description);
        });
        lines.push('');
      }
      var edges = data.stemma_edges || [];
      if (edges.length) {
        lines.push('STEMMA EDGES');
        edges.forEach(function(e) {
          lines.push('  ' + (e.from||'') + ' → ' + (e.to||''));
        });
        lines.push('');
      }
      var kdivs = data.key_divergences || [];
      if (kdivs.length) {
        lines.push('KEY DIVERGENCES', '');
        kdivs.forEach(function(d, i) {
          lines.push((i + 1) + '. ' + (d.title || '') + (d.passage ? '  (' + d.passage + ')' : ''));
          if (d.witnesses && d.witnesses.length) lines.push('   Witnesses: ' + d.witnesses.join(', '));
          if (d.plain)    lines.push('   ' + d.plain);
          if (d.technical) lines.push('   Technical: ' + d.technical);
          lines.push('');
        });
      }
      _appendAssessment(lines, data);
    }

    else {
      // Generic fallback
      ['summary_plain','overall_plain','transmission_plain','synthesis_plain',
       'archetype_description','period_summary'].forEach(function(k) {
        if (data[k]) lines.push(data[k], '');
      });
      _appendAssessment(lines, data);
    }

    lines.push(hr);
    lines.push('Generated by BibCrit · bibcrit.app · powered by Claude');
    lines.push('Citation: Fresco Benaim, J. (2026). BibCrit. ORCID:0009-0000-2026-0836');
    return lines.join('\n');
  }

  function _appendAssessment(lines, data) {
    var ass = data.bibcrit_assessment || {};
    if (ass.title || ass.plain) {
      lines.push('BIBCRIT ASSESSMENT');
      if (ass.title) lines.push(ass.title);
      if (ass.plain) lines.push(ass.plain);
      if (ass.confidence) lines.push('Confidence: ' + Math.round(ass.confidence * 100) + '%');
      lines.push('');
    }
  }

  function _toolLabel(tool) {
    var labels = {
      divergence:      'MT/LXX Divergence',
      backtranslation: 'Back-Translation',
      scribal:         'Scribal Tendency',
      numerical:       'Numerical Discrepancy',
      dss:             'DSS Bridge',
      theological:     'Theological Revision',
      patristic:       'Patristic Citation',
      genealogy:       'Manuscript Genealogy',
    };
    return labels[tool] || tool;
  }

  global.ResultActions = global.ResultActions || {};
  global.ResultActions.init = init;
  global.ResultActions._dlBlob = _dlBlob;
  global.ResultActions._toText = _resultToText;

})(window);
