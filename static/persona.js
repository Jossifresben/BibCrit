/**
 * BibCrit Persona UX
 * Manages Scholar / PhD / Student persona selection, localStorage persistence,
 * home-page hero swap, tool-card reordering + highlight, and nav pill.
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'bibcrit_persona';

  const PERSONAS = {
    scholar: { label: 'Scholar', color: '#2563eb' },
    phd:     { label: 'PhD',     color: '#6b5cdb' },
    student: { label: 'Student', color: '#059669' },
  };

  // CSS order value per tool per persona (lower = appears first in grid)
  const ORDER = {
    scholar: { divergence: 1, backtranslation: 2, dss: 3, genealogy: 4, scribal: 5, numerical: 6, theological: 7, patristic: 8, chiasm: 9, source: 10 },
    phd:     { divergence: 1, backtranslation: 2, dss: 3, theological: 4, scribal: 5, numerical: 6, patristic: 7, genealogy: 8, chiasm: 9, source: 10 },
    student: { divergence: 1, backtranslation: 2, dss: 3, scribal: 4, numerical: 5, theological: 6, patristic: 7, genealogy: 8, chiasm: 9, source: 10 },
  };

  // Which tool cards get the accent highlight per persona
  const HIGHLIGHT = {
    scholar: ['divergence', 'backtranslation', 'dss', 'genealogy', 'chiasm', 'source'],
    phd:     ['divergence', 'backtranslation', 'dss', 'theological', 'source'],
    student: ['divergence', 'backtranslation', 'dss'],
  };

  // ── Storage helpers ─────────────────────────────────────────────────────────
  function getPersona()    { try { return localStorage.getItem(STORAGE_KEY); } catch(e) { return null; } }
  function setPersona(p)   { try { localStorage.setItem(STORAGE_KEY, p); } catch(e) {} }
  function clearPersona()  { try { localStorage.removeItem(STORAGE_KEY); } catch(e) {} }

  // ── Home-page helpers ───────────────────────────────────────────────────────
  function showEl(el)  { if (el) el.style.display = ''; }
  function hideEl(el)  { if (el) el.style.display = 'none'; }

  function applyPersona(persona) {
    document.body.dataset.persona = persona;

    const selector   = document.getElementById('persona-selector');
    const defaultHero = document.getElementById('home-hero-default');
    const toolGrid   = document.getElementById('home-tools');
    const discovery  = document.querySelector('.home-discovery');

    hideEl(selector);
    hideEl(defaultHero);
    if (toolGrid)  toolGrid.style.display  = 'grid';
    if (discovery) discovery.style.display = 'block';

    // Persona heroes
    document.querySelectorAll('.persona-hero').forEach(function (h) {
      h.style.display = h.dataset.persona === persona ? 'block' : 'none';
    });

    // Reorder tool cards
    var order = ORDER[persona] || {};
    document.querySelectorAll('[data-tool]').forEach(function (card) {
      var o = order[card.dataset.tool];
      if (o) card.style.order = o;
    });

    // Highlight featured cards
    var highlighted = HIGHLIGHT[persona] || [];
    document.querySelectorAll('[data-tool]').forEach(function (card) {
      var isHL = highlighted.indexOf(card.dataset.tool) !== -1;
      card.classList.toggle('persona-highlight', isHL);
      if (isHL) card.dataset.personaAccent = persona;
      else delete card.dataset.personaAccent;
    });

    updateNavPill(persona);
  }

  function showSelector() {
    document.body.removeAttribute('data-persona');

    var selector  = document.getElementById('persona-selector');
    var defaultHero = document.getElementById('home-hero-default');
    var toolGrid  = document.getElementById('home-tools');
    var discovery = document.querySelector('.home-discovery');

    if (selector) selector.style.display = 'block';
    hideEl(defaultHero);
    hideEl(toolGrid);
    hideEl(discovery);

    document.querySelectorAll('.persona-hero').forEach(function (h) {
      h.style.display = 'none';
    });

    updateNavPill(null);
  }

  function showAll() {
    document.body.removeAttribute('data-persona');
    clearPersona();

    var selector  = document.getElementById('persona-selector');
    var defaultHero = document.getElementById('home-hero-default');
    var toolGrid  = document.getElementById('home-tools');
    var discovery = document.querySelector('.home-discovery');

    hideEl(selector);
    if (defaultHero) defaultHero.style.display = 'block';
    if (toolGrid)    toolGrid.style.display     = 'grid';
    if (discovery)   discovery.style.display    = 'block';

    document.querySelectorAll('.persona-hero').forEach(function (h) {
      h.style.display = 'none';
    });

    // Reset card order + highlights
    document.querySelectorAll('[data-tool]').forEach(function (card) {
      card.style.order = '';
      card.classList.remove('persona-highlight');
      delete card.dataset.personaAccent;
    });

    updateNavPill(null);
  }

  // ── Nav pill ────────────────────────────────────────────────────────────────
  function updateNavPill(persona) {
    var pill  = document.getElementById('persona-pill');
    var label = document.getElementById('persona-pill-label');
    if (!pill) return;

    var isHome = !!document.getElementById('persona-selector');

    if (persona && PERSONAS[persona]) {
      pill.style.background = PERSONAS[persona].color;
      if (label) label.textContent = PERSONAS[persona].label + ' \u25be';
      pill.style.display = 'flex';
    } else if (isHome) {
      // On home page with no persona: show a neutral "Choose view" pill
      pill.style.background = 'var(--muted, #6b7280)';
      if (label) label.textContent = 'Choose view \u25be';
      pill.style.display = 'flex';
    } else {
      pill.style.display = 'none';
    }

    // Update active state in dropdown
    document.querySelectorAll('[data-switch-persona]').forEach(function (item) {
      item.classList.toggle('active', item.dataset.switchPersona === persona);
    });
  }

  // ── Tool page subtitle ───────────────────────────────────────────────────
  /**
   * Swap the #tool-subtitle paragraph text based on the active persona.
   * The element must already exist in the template with default (no-persona) text.
   * @param {string} toolName  - e.g. 'divergence' (reserved for future use)
   * @param {{scholar:string, phd:string, student:string}} texts
   */
  function setToolSubtitle(toolName, texts) {
    var persona = getPersona();
    if (!persona) return;
    var el = document.getElementById('tool-subtitle');
    if (!el) return;
    if (texts[persona]) el.textContent = texts[persona];
  }

  // ── Public API ───────────────────────────────────────────────────────────
  window.BibCritPersona = { setToolSubtitle: setToolSubtitle };

  // ── Init ────────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    var persona = getPersona();
    var isHome  = !!document.getElementById('persona-selector');

    // Apply data-persona to body on every page (drives CSS subtitle colors)
    if (persona) document.body.dataset.persona = persona;
    else delete document.body.dataset.persona;

    // Nav pill on every page
    updateNavPill(persona);

    // Home-page logic
    if (isHome) {
      // Remove the anti-flash class now that JS is running
      document.documentElement.classList.remove('persona-first-visit');

      if (persona) {
        applyPersona(persona);
      } else {
        showSelector();
      }
    }

    // ── Selector card clicks ─────────────────────────────────────────────────
    document.querySelectorAll('[data-select-persona]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var p = this.dataset.selectPersona;
        setPersona(p);
        applyPersona(p);
      });
    });

    // ── Skip link ────────────────────────────────────────────────────────────
    var skipLink = document.getElementById('persona-skip');
    if (skipLink) {
      skipLink.addEventListener('click', function (e) {
        e.preventDefault();
        showAll();
      });
    }

    // ── Nav pill toggle ──────────────────────────────────────────────────────
    var pill     = document.getElementById('persona-pill');
    var dropdown = document.getElementById('persona-pill-dropdown');
    if (pill && dropdown) {
      pill.addEventListener('click', function (e) {
        e.stopPropagation();
        dropdown.classList.toggle('open');
      });
      document.addEventListener('click', function () {
        dropdown.classList.remove('open');
      });
      dropdown.addEventListener('click', function (e) {
        e.stopPropagation();
      });

      document.querySelectorAll('[data-switch-persona]').forEach(function (item) {
        item.addEventListener('click', function () {
          var p = this.dataset.switchPersona;
          if (p === 'all') {
            clearPersona();
          } else {
            setPersona(p);
          }
          window.location.reload();
        });
      });

      // "Change view" — navigate home and show selector
      var changeBtn = document.getElementById('ppd-change-view');
      if (changeBtn) {
        changeBtn.addEventListener('click', function () {
          dropdown.classList.remove('open');
          var isHome = !!document.getElementById('persona-selector');
          if (isHome) {
            // Already on home page — clear persona and show selector inline
            clearPersona();
            showSelector();
            updateNavPill(null);
          } else {
            // Navigate to home, selector will auto-show (no persona in storage)
            clearPersona();
            window.location.href = '/';
          }
        });
      }
    }
  });

}());
