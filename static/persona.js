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
    scholar: { divergence: 1, backtranslation: 2, dss: 3, genealogy: 4, scribal: 5, numerical: 6, theological: 7, patristic: 8 },
    phd:     { divergence: 1, backtranslation: 2, dss: 3, theological: 4, scribal: 5, numerical: 6, patristic: 7, genealogy: 8 },
    student: { divergence: 1, backtranslation: 2, dss: 3, scribal: 4, numerical: 5, theological: 6, patristic: 7, genealogy: 8 },
  };

  // Which tool cards get the accent highlight per persona
  const HIGHLIGHT = {
    scholar: ['divergence', 'backtranslation', 'dss', 'genealogy'],
    phd:     ['divergence', 'backtranslation', 'dss', 'theological'],
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
    showEl(toolGrid);
    showEl(discovery);

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

    showEl(selector);
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
    showEl(defaultHero);
    showEl(toolGrid);
    showEl(discovery);

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

    if (persona && PERSONAS[persona]) {
      pill.style.background = PERSONAS[persona].color;
      if (label) label.textContent = PERSONAS[persona].label + ' \u25be';
      pill.style.display = 'flex';
    } else {
      pill.style.display = 'none';
    }

    // Update active state in dropdown
    document.querySelectorAll('[data-switch-persona]').forEach(function (item) {
      item.classList.toggle('active', item.dataset.switchPersona === persona);
    });
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    var persona = getPersona();
    var isHome  = !!document.getElementById('persona-selector');

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
    }
  });

}());
