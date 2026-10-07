// static/tt.js — translation technique page. No model calls; fetches computed tables.
(function () {
  const app = document.getElementById('tt-app');
  const I = window.TT_I18N || {};
  const $ = id => document.getElementById(id);

  document.addEventListener('DOMContentLoaded', () => { loadMeta(); if ($('tt-lex').value.trim()) setTimeout(() => schedule(), 0); });

  const how = $('tt-how');
  try { if (localStorage.getItem('tt_how') === 'closed') how.open = false; } catch (e) {}
  how.addEventListener('toggle', () => { try { localStorage.setItem('tt_how', how.open ? 'open' : 'closed'); } catch (e) {} });
  $('tt-copy').addEventListener('click', async () => {
    const url = location.href, b = $('tt-copy');
    let ok = false;
    try { await navigator.clipboard.writeText(url); ok = true; }
    catch (e) {
      const ta = document.createElement('input'); ta.value = url; ta.readOnly = true;
      ta.style.cssText = 'position:fixed;left:-9999px;opacity:0';
      document.body.appendChild(ta); ta.select();
      try { ok = document.execCommand('copy'); } catch (e2) { console.warn('tt: copy failed', e2); }
      ta.remove();
    }
    if (ok) { b.textContent = I.copied; setTimeout(() => { b.textContent = I.copy_link; }, 1500); }
  });
  const lang = app.dataset.lang || 'en';
  const OCC_LIMIT = 200;
  function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function fmtPct(x) { return (100 * x).toFixed(1) + '%'; }
  function tpl(s, vars) { return (s || '').replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? ''); }
  function bookName(b) { return String(b).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + ' -> ' + r.status);
    return r.json();
  }

  // ── books chips ──
  const chipBooks = () => Array.from(document.querySelectorAll('#tt-books [data-book]'));
  function books() { return chipBooks().filter(c => c.classList.contains('active')).map(c => c.dataset.book).join(','); }
  function syncAllChip() {
    const all = document.querySelector('#tt-books [data-all]');
    const on = chipBooks().every(c => c.classList.contains('active'));
    all.classList.toggle('active', on); all.setAttribute('aria-pressed', on);
  }
  function setChip(c, on) { c.classList.toggle('active', on); c.setAttribute('aria-pressed', on); }
  $('tt-books').addEventListener('click', (ev) => {
    const c = ev.target.closest('button'); if (!c) return;
    if (c.dataset.all) { const on = !c.classList.contains('active'); chipBooks().forEach(b => setChip(b, on)); }
    else setChip(c, !c.classList.contains('active'));
    syncAllChip();
    known = new Set();
    schedule();
  });
  syncAllChip();

  function qs(lex, extra) {
    const p = new URLSearchParams({ lex, books: books() });
    if ($('tt-facet').value) p.set('facet', $('tt-facet').value);
    if ($('tt-witness').value) p.set('witness', $('tt-witness').value);
    Object.entries(extra || {}).forEach(([k, v]) => p.set(k, v));
    return p.toString();
  }

  // ── meta / methodology ──
  async function loadMeta() {
    try {
      const m = await getJSON('/api/tt/meta');
      const sel = new Set(m.books || []);
      const cov = Object.entries(m.coverage || {}).filter(([b]) => sel.has(b)).map(([b, c]) =>
        `${bookName(b)}: ${Object.entries(c.by_source_tokens).map(([s, v]) => `${s} ${fmtPct(v)}`).join(', ')}`).join(' · ');
      $('tt-coverage').textContent = tpl(I.coverage, { coverage: cov });
      const mf = m.manifest || {};
      $('tt-manifest').innerHTML = esc(tpl(I.manifest, { version: m.version, hash: '\u0001', built: mf.built_at || '', model_links: mf.model_links || 0, model: mf.model_id || '—' }))
        .replace('\u0001', `<code>${esc(mf.hash || '')}</code>`);
      $('tt-eval').textContent = m.eval
        ? tpl(I.eval, { precision: fmtPct(m.eval.precision), recall: fmtPct(m.eval.recall), agreement: fmtPct(m.eval.agreement), n: m.eval.verses })
        : I.unevaluated;
    } catch (e) { console.warn('tt: meta failed', e); }
  }

  // ── lexeme input ──
  let known = new Set();       // lex values from the last suggestion fetch
  let sugTimer = null, runTimer = null, seq = 0, sugSeq = 0;
  const lexInfo = new Map();   // lex -> {word, gloss}
  const isLex = v => known.has(v) || /[\[\/]$/.test(v);

  async function fetchSuggestions() {
    const q = $('tt-lex').value.trim();
    if (!q) { known = new Set(); $('tt-lex-list').innerHTML = ''; return; }
    const my = ++sugSeq;
    try {
      const items = await getJSON(`/api/tt/lexemes?q=${encodeURIComponent(q)}&books=${encodeURIComponent(books())}`);
      if (my !== sugSeq) return;
      known = new Set(items.map(i => i.lex));
      items.forEach(i => lexInfo.set(i.lex, { word: i.word, gloss: i.gloss }));
      $('tt-lex-list').innerHTML = items.map(i => `<option value="${esc(i.lex)}">${esc(i.word)} · ${esc(i.gloss)} (${esc(i.count)})</option>`).join('');
    } catch (e) { console.warn('tt: suggestions failed', e); }
  }
  function schedule() { clearTimeout(runTimer); runTimer = setTimeout(run, 120); }

  $('tt-lex').addEventListener('input', () => {
    clearTimeout(sugTimer);
    const v = $('tt-lex').value.trim();
    if (!v) { clearTimeout(runTimer); seq++; reset(); known = new Set(); $('tt-lex-list').innerHTML = ''; return; }
    if (known.has(v)) schedule();            // datalist selection
    sugTimer = setTimeout(fetchSuggestions, 150);
  });
  $('tt-lex').addEventListener('keydown', (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); schedule(); } });
  $('tt-lex').addEventListener('change', schedule);
  ['tt-facet', 'tt-witness'].forEach(id => $(id).addEventListener('change', schedule));
  document.querySelectorAll('.featured-ref[data-lex]').forEach(a => a.addEventListener('click', (ev) => {
    ev.preventDefault(); $('tt-lex').value = a.dataset.lex; schedule();
  }));

  async function resolve(value) {
    try {
      const items = await getJSON(`/api/tt/lexemes?q=${encodeURIComponent(value)}&books=${encodeURIComponent(books())}`);
      if (!items.length) return null;
      known = new Set(items.map(i => i.lex));
      items.forEach(i => lexInfo.set(i.lex, { word: i.word, gloss: i.gloss }));
      return items[0].lex;
    } catch (e) { console.warn('tt: resolve failed', e); return null; }
  }

  function showMsg(on) { $('tt-msg').textContent = I.no_match || ''; $('tt-msg').hidden = !on; }
  function clearUrlLex() {
    try { const u = new URLSearchParams(location.search); u.delete('lex'); const q = u.toString(); history.replaceState(null, '', q ? '?' + q : location.pathname); } catch (e) {}
  }
  function reset() {
    clearUrlLex();
    ['tt-dist', 'tt-xtab', 'tt-occ'].forEach(id => { $(id).hidden = true; });
    showMsg(false);
    $('tt-empty').hidden = false;
  }
  function noMatch() {
    clearUrlLex();
    ['tt-dist', 'tt-xtab', 'tt-occ'].forEach(id => { $(id).hidden = true; });
    $('tt-empty').hidden = true;
    showMsg(true);
  }

  async function run() {
    const raw = $('tt-lex').value.trim();
    const my = ++seq;
    if (!raw || !books()) { reset(); return; }
    let lex = raw;
    if (!isLex(raw)) {
      lex = await resolve(raw);
      if (my !== seq) return;
      if (!lex) { noMatch(); return; }
      $('tt-lex').value = lex;
    }
    let d;
    try {
      const r = await fetch('/api/tt/table?' + qs(lex, { lang }));
      if (my !== seq) return;
      if (!r.ok) { noMatch(); return; }
      d = await r.json();
    } catch (e) { console.warn('tt: table failed', e); if (my === seq) noMatch(); return; }
    if (my !== seq) return;
    if (!d.occurrences || !d.occurrences.length) { noMatch(); return; }
    showMsg(false); $('tt-empty').hidden = true;
    renderDist(d, my); renderXtab(d); renderOcc(d);
    $('tt-export').href = '/api/tt/occurrences.csv?' + qs(lex);
    try { history.replaceState(null, '', '?' + qs(lex, { lang })); } catch (e) {}
  }

  async function titleFor(lex, my) {
    let info = lexInfo.get(lex);
    if (!info) {
      try {
        const items = await getJSON(`/api/tt/lexemes?q=${encodeURIComponent(lex)}`);
        const hit = items.find(i => i.lex === lex) || items[0];
        if (hit) { info = { word: hit.word, gloss: hit.gloss }; lexInfo.set(lex, info); }
      } catch (e) { console.warn('tt: lexeme info failed', e); }
    }
    if (my !== seq) return;
    $('tt-dist-lex').innerHTML = `<span class="tt-lex-word" lang="he" dir="rtl">${esc(info ? info.word : '')}</span> `
      + `<span class="tt-lex-id">${esc(lex)}</span>` + (info && info.gloss ? ` <span class="tt-lex-gloss">${esc(info.gloss)}</span>` : '');
  }

  function renderDist(d, my) {
    const dist = d.distribution;
    $('tt-dist').hidden = false;
    $('tt-dist-lex').innerHTML = `<span class="tt-lex-id">${esc(d.lex)}</span>`;
    titleFor(d.lex, my);
    const max = Math.max(1, ...dist.items.map(i => i.count));
    $('tt-bars').innerHTML = dist.items.map(i => `
      <div class="tt-bar-row">
        <span class="tt-bar-label tt-syriac" dir="rtl" lang="syr">${esc(i.syr_lemma)}</span>
        <span class="tt-bar-track"><span class="tt-bar" style="width:${(100 * i.count / max).toFixed(1)}%"></span></span>
        <span class="tt-bar-count">${esc(i.count)}${i.model_share ? ` <span class="confidence-badge confidence-medium">${esc(Math.round(100 * i.model_share))}% ${esc(I.model)}</span>` : ''}</span>
      </div>`).join('');
    $('tt-model-share').textContent = tpl(I.model_share, { share: fmtPct(dist.model_share_total) });
    $('tt-null-count').textContent = tpl(I.null_count, { n: dist.null_count, total: dist.total });
    const wn = $('tt-witness-notes');
    wn.hidden = !(d.witness_notes && d.witness_notes.length);
    const fl = d.findings || [];
    $('tt-findings').hidden = !fl.length;
    $('tt-findings-list').innerHTML = fl.map(f => `<li>${esc(f)}</li>`).join('');
    wn.textContent = (d.witness_notes || []).map(n => `${n.sigla} ${n.ref} #${n.position}: ${n.note} [${n.keyed_from}]`).join(' · ');
  }

  function renderXtab(d) {
    const x = d.crosstab;
    $('tt-xtab').hidden = !x;
    if (!x) return;
    const fo = $('tt-facet').selectedOptions[0];
    $('tt-xtab-facet').textContent = fo ? fo.textContent : '';
    const rowTot = x.matrix.map(r => r.reduce((a, b) => a + b, 0));
    const colTot = x.values.map((_, j) => x.matrix.reduce((a, r) => a + r[j], 0));
    const grand = rowTot.reduce((a, b) => a + b, 0);
    $('tt-xtab-table').innerHTML = `<table class="tt-table tt-zebra"><thead><tr><th></th>${x.values.map(v => { const lb = (x.value_labels || {})[v]; return `<th class="tt-num"${lb ? ` title="${esc(lb)}"` : ''}>${esc(v)}${lb && lb !== v ? `<br><small class="tt-vlabel">${esc(lb)}</small>` : ''}</th>`; }).join('')}<th class="tt-num">Σ</th></tr></thead>
      <tbody>${x.lemmas.map((l, i) => `<tr><th class="tt-syriac" dir="rtl" lang="syr">${esc(l)}</th>${x.matrix[i].map(c => `<td class="tt-num">${esc(c)}</td>`).join('')}<td class="tt-num tt-total">${rowTot[i]}</td></tr>`).join('')}
      <tr class="tt-total-row"><th>Σ</th>${colTot.map(c => `<td class="tt-num tt-total">${c}</td>`).join('')}<td class="tt-num tt-total">${grand}</td></tr></tbody></table>`;
    const el = $('tt-xtab-stats');
    if (x.unreliable) { el.textContent = I.unreliable; return; }
    const v = Number(x.cramers_v);
    const gloss = v < 0.1 ? I.assoc_negligible : v < 0.3 ? I.assoc_weak : v < 0.5 ? I.assoc_moderate : I.assoc_strong;
    const pt = x.p_text || (x.p < 0.001 ? '< 0.001' : x.p.toFixed(3));
    const p = pt.startsWith('<') ? pt : '= ' + pt;
    el.textContent = `χ² = ${x.stat}, df = ${x.dof}, p ${p} · Cramér's V = ${v.toFixed(2)} (${gloss})`;
  }

  function probClass(p) { return p >= 0.8 ? 'confidence-high' : p >= 0.5 ? 'confidence-medium' : 'confidence-low'; }
  function occRow(o) {
    const p = Number(o.prob);
    return `<tr>
      <td><a href="/translation-technique/verse/${encodeURIComponent(o.ref)}?lang=${encodeURIComponent(lang)}">${esc(o.ref)}</a></td>
      <td class="tt-hebrew" dir="rtl" lang="he">${esc(o.heb_word)}</td>
      <td class="tt-syriac" dir="rtl" lang="syr">${esc(o.syr_lemma ?? '—')}</td>
      <td>${o.prob == null ? '—' : `<span class="confidence-badge ${probClass(p)}">${esc(o.prob)}</span>`}</td>
      <td>${o.source ? `<span class="tradition-badge tt-src">${esc(o.source)}</span>` : ''}${o.syr_source ? ` <span class="tradition-badge tt-src tt-src-lemma">${esc(o.syr_source)}</span>` : ''}</td></tr>`;
  }
  let occAll = [], sortKey = 'ref', sortDir = 1, showAll = false;
  const sortVal = {
    ref: o => o._i,
    syr: o => o.syr_lemma ?? '',
    prob: o => (o.prob == null ? -1 : Number(o.prob)),
    src: o => `${o.source || ''}/${o.syr_source || ''}`,
  };
  function paintOcc() {
    const f = sortVal[sortKey];
    const rows = occAll.slice().sort((x, y) => {
      const a = f(x), b = f(y);
      const c = typeof a === 'number' ? a - b : String(a).localeCompare(String(b));
      return (c || x._i - y._i) * sortDir;
    });
    $('tt-occ-body').innerHTML = (showAll ? rows : rows.slice(0, OCC_LIMIT)).map(occRow).join('');
    document.querySelectorAll('#tt-occ th[data-sort]').forEach(th => {
      const on = th.dataset.sort === sortKey;
      th.setAttribute('aria-sort', on ? (sortDir > 0 ? 'ascending' : 'descending') : 'none');
      th.querySelector('.tt-arrow').textContent = on ? (sortDir > 0 ? ' ▲' : ' ▼') : '';
    });
    const btn = $('tt-show-all');
    btn.hidden = showAll || occAll.length <= OCC_LIMIT;
    btn.textContent = tpl(I.show_all, { n: occAll.length });
  }
  function sortBy(th) {
    const k = th.dataset.sort;
    if (k === sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = 1; }
    paintOcc();
  }
  document.querySelectorAll('#tt-occ th[data-sort]').forEach(th => {
    th.addEventListener('click', () => sortBy(th));
    th.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); sortBy(th); } });
  });
  $('tt-show-all').addEventListener('click', () => { showAll = true; paintOcc(); });
  function renderOcc(d) {
    $('tt-occ').hidden = false;
    occAll = d.occurrences.map((o, i) => Object.assign({ _i: i }, o));   // _i keeps the canonical (server) order
    showAll = false;
    $('tt-occ-count').textContent = `(${occAll.length})`;
    paintOcc();
  }
})();
