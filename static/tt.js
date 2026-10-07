// static/tt.js — translation technique page. No model calls; fetches computed tables.
(function () {
  const gate = document.getElementById('tt-gate');
  const app = document.getElementById('tt-app');
  const I = window.TT_I18N || {};

  async function sha256(text) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }
  function open() { gate.hidden = true; app.hidden = false; loadMeta(); }
  try { if (sessionStorage.getItem('tt_ok') === '1') open(); } catch (e) {}
  document.getElementById('tt-gate-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const pw = document.getElementById('tt-gate-pw').value;
    const ok = (await sha256(pw)) === gate.dataset.hash;
    if (ok) { try { sessionStorage.setItem('tt_ok', '1'); } catch (e) {} open(); }
    else document.getElementById('tt-gate-msg').hidden = false;
  });

  const $ = id => document.getElementById(id);
  const lang = app.dataset.lang || 'en';
  function books() { return Array.from($('tt-books').selectedOptions).map(o => o.value).join(','); }
  function qs(extra) {
    const p = new URLSearchParams({ lex: $('tt-lex').value.trim(), books: books() });
    if ($('tt-facet').value) p.set('facet', $('tt-facet').value);
    if ($('tt-witness').value) p.set('witness', $('tt-witness').value);
    Object.entries(extra || {}).forEach(([k, v]) => p.set(k, v));
    return p.toString();
  }
  function fmtPct(x) { return (100 * x).toFixed(1) + '%'; }
  function tpl(s, vars) { return (s || '').replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? ''); }

  async function loadMeta() {
    const m = await (await fetch('/api/tt/meta')).json();
    const cov = Object.entries(m.coverage || {}).map(([b, c]) =>
      `${b}: ${Object.entries(c.by_source_tokens).map(([s, v]) => `${s} ${fmtPct(v)}`).join(', ')}`).join(' · ');
    $('tt-coverage').textContent = tpl(I.coverage, { coverage: cov });
    $('tt-manifest').textContent = tpl(I.manifest, { version: m.version, hash: m.manifest.hash || '', built: m.manifest.built_at || '', model_links: m.manifest.model_links || 0 });
    $('tt-eval').textContent = m.eval
      ? tpl(I.eval, { precision: fmtPct(m.eval.precision), recall: fmtPct(m.eval.recall), agreement: fmtPct(m.eval.agreement), n: m.eval.verses })
      : I.unevaluated;
  }

  let lexTimer = null;
  $('tt-lex').addEventListener('input', () => {
    clearTimeout(lexTimer);
    lexTimer = setTimeout(async () => {
      const q = $('tt-lex').value.trim();
      if (q.length < 1) return;
      const items = await (await fetch(`/api/tt/lexemes?q=${encodeURIComponent(q)}&books=${books()}`)).json();
      $('tt-lex-list').innerHTML = items.map(i => `<option value="${i.lex}">${i.word} · ${i.gloss} (${i.count})</option>`).join('');
    }, 150);
  });
  $('tt-lex').addEventListener('change', run);
  ['tt-books', 'tt-facet', 'tt-witness'].forEach(id => $(id).addEventListener('change', run));

  async function run() {
    const lex = $('tt-lex').value.trim();
    if (!lex) return;
    const r = await fetch('/api/tt/table?' + qs());
    if (!r.ok) return;
    const d = await r.json();
    renderDist(d); renderXtab(d); renderOcc(d);
    $('tt-export').href = '/api/tt/occurrences.csv?' + qs();
  }

  function renderDist(d) {
    const dist = d.distribution;
    $('tt-dist').hidden = false;
    $('tt-dist-lex').textContent = d.lex;
    const max = Math.max(1, ...dist.items.map(i => i.count));
    $('tt-bars').innerHTML = dist.items.map(i => `
      <div class="tt-bar-row">
        <span class="tt-bar-label" dir="rtl" lang="syr">${i.syr_lemma}</span>
        <span class="tt-bar" style="width:${(100 * i.count / max).toFixed(1)}%"></span>
        <span class="tt-bar-count">${i.count}${i.model_share ? ` <small>(${fmtPct(i.model_share)} model)</small>` : ''}</span>
      </div>`).join('');
    $('tt-model-share').textContent = tpl(I.model_share, { share: fmtPct(dist.model_share_total) });
    $('tt-null-count').textContent = tpl(I.null_count, { n: dist.null_count, total: dist.total });
    const wn = $('tt-witness-notes');
    wn.hidden = !(d.witness_notes && d.witness_notes.length);
    wn.textContent = (d.witness_notes || []).map(n => `${n.sigla} ${n.ref} #${n.position}: ${n.note} [${n.keyed_from}]`).join(' · ');
  }

  function renderXtab(d) {
    const x = d.crosstab;
    $('tt-xtab').hidden = !x;
    if (!x) return;
    $('tt-xtab-table').innerHTML = `<table class="tt-table"><thead><tr><th></th>${x.values.map(v => `<th>${v}</th>`).join('')}</tr></thead>
      <tbody>${x.lemmas.map((l, i) => `<tr><th dir="rtl" lang="syr">${l}</th>${x.matrix[i].map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    $('tt-xtab-stats').textContent = `χ² = ${x.stat}, df = ${x.dof}, p = ${x.p.toExponential(2)}, V = ${x.cramers_v}` + (x.unreliable ? ` — ${I.unreliable}` : '');
  }

  function renderOcc(d) {
    $('tt-occ').hidden = false;
    $('tt-occ-body').innerHTML = d.occurrences.map(o => `<tr>
      <td><a href="/translation-technique/verse/${encodeURIComponent(o.ref)}?lang=${lang}">${o.ref}</a></td>
      <td dir="rtl" lang="he">${o.heb_word}</td>
      <td dir="rtl" lang="syr">${o.syr_lemma ?? '—'}</td>
      <td>${o.prob}</td>
      <td>${o.source}${o.syr_source ? ' / ' + o.syr_source : ''}</td></tr>`).join('');
  }
})();
