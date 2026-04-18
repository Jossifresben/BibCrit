/* Aramaic Root Atlas — Global JS */

(function() {
    'use strict';

    var html = document.documentElement;
    var urlParams = new URLSearchParams(window.location.search);

    // --- Dark Mode ---
    var themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        var themeIcon = themeBtn.querySelector('.material-symbols-outlined');

        function applyTheme(theme) {
            html.setAttribute('data-theme', theme);
            if (themeIcon) themeIcon.textContent = theme === 'dark' ? 'bedtime' : 'sunny';
        }

        var savedTheme = localStorage.getItem('bibcrit-theme');
        if (savedTheme) applyTheme(savedTheme);

        themeBtn.addEventListener('click', function() {
            var current = html.getAttribute('data-theme') || 'light';
            var next = current === 'dark' ? 'light' : 'dark';
            localStorage.setItem('bibcrit-theme', next);
            applyTheme(next);
        });
    }

    // --- Scholar / Student Mode Toggle ---
    var modeBtn = document.getElementById('mode-toggle');
    if (modeBtn) {
        var modeIconScholar = modeBtn.querySelector('.mode-icon-scholar');
        var modeIconStudent = modeBtn.querySelector('.mode-icon-student');

        function applyMode(mode) {
            var isStudent = mode === 'student';
            document.body.classList.toggle('mode-student', isStudent);
            modeBtn.classList.toggle('mode-active', isStudent);
            if (modeIconScholar) modeIconScholar.style.display = isStudent ? 'none' : 'block';
            if (modeIconStudent) modeIconStudent.style.display = isStudent ? 'block' : 'none';
        }

        var savedMode = localStorage.getItem('bibcrit-mode') || 'scholar';
        applyMode(savedMode);

        modeBtn.addEventListener('click', function () {
            var next = document.body.classList.contains('mode-student') ? 'scholar' : 'student';
            localStorage.setItem('bibcrit-mode', next);
            applyMode(next);
        });
    }

    // Expose current lang globally so tool JS files can pass it to API stream calls
    window.bibcritLang = urlParams.get('lang') || localStorage.getItem('bibcrit-lang') || 'en';

    // --- Lang Preference ---
    var currentLang = urlParams.get('lang');
    if (currentLang) {
        // Persist chosen lang
        localStorage.setItem('bibcrit-lang', currentLang);
    } else {
        var storedLang = localStorage.getItem('bibcrit-lang');
        if (storedLang && storedLang !== 'en') {
            urlParams.set('lang', storedLang);
            window.location.replace(window.location.pathname + '?' + urlParams.toString() + window.location.hash);
            return;
        }
    }

    // Update lang code label to match active lang
    var langCodeEl = document.getElementById('lang-current-code');
    if (langCodeEl) {
        var activeLang = urlParams.get('lang') || localStorage.getItem('bibcrit-lang') || 'en';
        langCodeEl.textContent = activeLang.toUpperCase();
    }

    // --- Stored Preferences Redirect ---
    var needsRedirect = false;
    if (!urlParams.has('script')) {
        var storedScript = localStorage.getItem('script');
        if (storedScript && storedScript !== 'latin') {
            urlParams.set('script', storedScript);
            needsRedirect = true;
        }
    }
    if (!urlParams.has('trans')) {
        var storedTrans = localStorage.getItem('trans');
        if (storedTrans) {
            urlParams.set('trans', storedTrans);
            needsRedirect = true;
        }
    }
    if (needsRedirect) {
        var newUrl = window.location.pathname + '?' + urlParams.toString() + window.location.hash;
        window.location.replace(newUrl);
        return;
    }

    // --- Syriac Font Variant ---
    var storedFont = localStorage.getItem('syriac-font') || 'estrangela';
    if (storedFont !== 'estrangela') {
        html.setAttribute('data-syriac-font', storedFont);
    }
    document.querySelectorAll('.syriac-font-option').forEach(function(btn) {
        if (btn.getAttribute('data-syriac-font') === storedFont) {
            btn.classList.add('active');
        }
        btn.addEventListener('click', function() {
            var val = this.getAttribute('data-syriac-font');
            localStorage.setItem('syriac-font', val);
            if (val === 'estrangela') {
                html.removeAttribute('data-syriac-font');
            } else {
                html.setAttribute('data-syriac-font', val);
            }
            document.querySelectorAll('.syriac-font-option').forEach(function(b) {
                b.classList.remove('active');
            });
            this.classList.add('active');
        });
    });

    // --- Hamburger Menu ---
    var hamburger = document.getElementById('nav-hamburger');
    var navLinks = document.getElementById('nav-links');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', function(e) {
            e.stopPropagation();
            var isOpen = navLinks.classList.toggle('open');
            hamburger.setAttribute('aria-expanded', isOpen);
            hamburger.querySelector('.material-symbols-outlined').textContent = isOpen ? 'close' : 'menu';
        });
    }

    // --- Helper: close all dropdowns ---
    function closeAllDropdowns() {
        var sd = document.getElementById('settings-dropdown');
        var ld = document.getElementById('lang-dropdown');
        if (sd) sd.classList.remove('open');
        if (ld) ld.classList.remove('open');
        document.querySelectorAll('.nav-dropdown').forEach(function(d) { d.classList.remove('open'); });
    }

    // --- Nav dropdowns (Explore / Research) ---
    document.querySelectorAll('.nav-drop-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var dropdown = btn.closest('.nav-dropdown');
            var wasOpen = dropdown.classList.contains('open');
            closeAllDropdowns();
            if (!wasOpen) {
                dropdown.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
            } else {
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    });
    document.querySelectorAll('.nav-drop-menu').forEach(function(menu) {
        menu.addEventListener('click', function(e) { e.stopPropagation(); });
    });

    // --- Language Dropdown ---
    var langToggle = document.getElementById('lang-toggle');
    var langDropdown = document.getElementById('lang-dropdown');
    if (langToggle && langDropdown) {
        langToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            var wasOpen = langDropdown.classList.contains('open');
            closeAllDropdowns();
            if (!wasOpen) langDropdown.classList.add('open');
        });

        langDropdown.querySelectorAll('.lang-option').forEach(function(opt) {
            opt.addEventListener('click', function() {
                var langVal = this.getAttribute('data-lang');
                if (langVal) {
                    var url = new URL(window.location.href);
                    url.searchParams.set('lang', langVal);
                    window.location.href = url.toString();
                }
            });
        });
    }

    // --- Settings Dropdown ---
    var settingsToggle = document.getElementById('settings-toggle');
    var settingsDropdown = document.getElementById('settings-dropdown');
    if (settingsToggle && settingsDropdown) {
        settingsToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            var wasOpen = settingsDropdown.classList.contains('open');
            closeAllDropdowns();
            if (!wasOpen) settingsDropdown.classList.add('open');
        });

        settingsDropdown.querySelectorAll('.settings-option').forEach(function(opt) {
            opt.addEventListener('click', function() {
                var scriptVal = this.getAttribute('data-script');
                var transVal = this.getAttribute('data-trans');
                if (scriptVal) {
                    localStorage.setItem('script', scriptVal);
                    var url = new URL(window.location.href);
                    url.searchParams.set('script', scriptVal);
                    window.location.href = url.toString();
                } else if (transVal) {
                    localStorage.setItem('trans', transVal);
                    var url = new URL(window.location.href);
                    url.searchParams.set('trans', transVal);
                    window.location.href = url.toString();
                }
            });
        });
    }

    // Close dropdowns and hamburger on outside click
    document.addEventListener('click', function() {
        closeAllDropdowns();
        if (navLinks) {
            navLinks.classList.remove('open');
            if (hamburger) {
                hamburger.setAttribute('aria-expanded', 'false');
                hamburger.querySelector('.material-symbols-outlined').textContent = 'menu';
            }
        }
    });
    if (settingsDropdown) settingsDropdown.addEventListener('click', function(e) { e.stopPropagation(); });
    if (langDropdown) langDropdown.addEventListener('click', function(e) { e.stopPropagation(); });

    // --- Share / QR Modal ---
    var shareBtn = document.getElementById('share-toggle');
    var shareModal = document.getElementById('share-modal');
    if (shareBtn && shareModal) {
        var shareUrl = document.getElementById('share-url');
        var copyBtn = document.getElementById('share-copy-btn');
        var qrEl = document.getElementById('share-qr');
        var closeBtn = document.getElementById('share-close');
        var qrGenerated = false;

        shareBtn.addEventListener('click', function() {
            var url = window.location.href;
            if (shareUrl) shareUrl.value = url;
            if (!qrGenerated && qrEl && typeof QRCode !== 'undefined') {
                var isDark = html.getAttribute('data-theme') === 'dark';
                new QRCode(qrEl, {
                    text: url,
                    width: 200,
                    height: 200,
                    colorDark: isDark ? '#e2e4dc' : '#1a1a1a',
                    colorLight: isDark ? '#1a1d18' : '#ffffff',
                    correctLevel: QRCode.CorrectLevel.M
                });
                qrGenerated = true;
            }
            shareModal.classList.add('active');
        });

        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                shareModal.classList.remove('active');
            });
        }

        shareModal.addEventListener('click', function(e) {
            if (e.target === shareModal) shareModal.classList.remove('active');
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && shareModal.classList.contains('active')) {
                shareModal.classList.remove('active');
            }
        });

        if (copyBtn && shareUrl) {
            copyBtn.addEventListener('click', function() {
                shareUrl.select();
                navigator.clipboard.writeText(shareUrl.value).then(function() {
                    copyBtn.querySelector('.material-symbols-outlined').textContent = 'check';
                    setTimeout(function() {
                        copyBtn.querySelector('.material-symbols-outlined').textContent = 'content_copy';
                    }, 1500);
                });
            });
        }
    }
})();

// --- Shared bookmark utilities ---
function getBookmarks() {
    try { return JSON.parse(localStorage.getItem('atlas_bookmarks') || '{"verses":[],"roots":[]}'); }
    catch(e) { return {verses:[], roots:[]}; }
}
function saveBookmarks(bm) { localStorage.setItem('atlas_bookmarks', JSON.stringify(bm)); }

// --- Shared annotation utilities ---
function getAnnotations() {
    try { return JSON.parse(localStorage.getItem('atlas_annotations') || '{"verses":{},"roots":{}}'); }
    catch(e) { return {verses:{}, roots:{}}; }
}
function saveAnnotations(ann) { localStorage.setItem('atlas_annotations', JSON.stringify(ann)); }
function setAnnotation(type, key, text, tags) {
    var ann = getAnnotations();
    var now = new Date().toISOString().slice(0,10);
    if (!ann[type]) ann[type] = {};
    var existing = ann[type][key];
    ann[type][key] = { text: text, tags: tags || [], created: existing ? existing.created : now, updated: now };
    saveAnnotations(ann);
}
function deleteAnnotation(type, key) {
    var ann = getAnnotations();
    if (ann[type]) delete ann[type][key];
    saveAnnotations(ann);
}

// --- Budget bar (shared across all analysis pages) ---
function updateBudgetBar() {
    fetch('/api/budget')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var spendEl  = document.getElementById('budget-spend');
            var capEl    = document.getElementById('budget-cap');
            var barEl    = document.getElementById('budget-bar');
            var pctEl    = document.getElementById('budget-pct');
            var donateEl = document.getElementById('budget-donate-btn');
            if (spendEl) spendEl.textContent = '$' + (data.spend_usd || 0).toFixed(2);
            if (capEl)   capEl.textContent   = '$' + (data.cap_usd   || 5).toFixed(2);
            if (barEl)   barEl.style.width   = Math.min(data.pct || 0, 100) + '%';
            if (pctEl)   pctEl.textContent   = (data.pct || 0).toFixed(1) + '%';
            if (donateEl) donateEl.style.display = (data.pct >= 80) ? 'inline-block' : 'none';
        })
        .catch(function() {});
}

document.addEventListener('DOMContentLoaded', function() {
    updateBudgetBar();
});

// ── Passage length guard ───────────────────────────────────────────────────
/**
 * Rough upper-bound estimate of verses in a biblical reference string.
 * Handles: "Genesis 6:1-9:17" (cross-chapter), "Genesis 6-9" (chapter range),
 *          "Amos 5:1-17" (same-chapter verse range), single verse/chapter.
 */
window.BibCrit_estimateVerseCount = function(ref) {
  if (!ref) return 0;
  // NOTE: same-chapter verse range MUST be checked first to avoid
  // "5:1-17" being misread as chapter range "1→17".
  // Same-chapter verse range: ":1-17"
  var vr = ref.match(/:\s*(\d+)\s*[-\u2013\u2014]\s*(\d+)\s*$/);
  if (vr) return parseInt(vr[2]) - parseInt(vr[1]) + 1;
  // Cross-chapter range: "6:1 - 9:17"
  var cc = ref.match(/(\d+)\s*:\s*\d+\s*[-\u2013\u2014]\s*(\d+)\s*:/);
  if (cc) return (parseInt(cc[2]) - parseInt(cc[1]) + 1) * 30;
  // Chapter range without colons: "6 - 9"
  var cr = ref.match(/\b(\d+)\s*[-\u2013\u2014]\s*(\d+)\b(?!\s*:)/);
  if (cr) {
    var d = parseInt(cr[2]) - parseInt(cr[1]);
    if (d > 0 && d < 50) return (d + 1) * 30;
  }
  return 20; // single verse or chapter — safe
};

/**
 * Show a toast-style error if a reference exceeds TOOL_MAX_VERSES.
 * Returns true if the reference is too long (caller should abort), false if ok.
 */
window.BibCrit_checkPassageLength = function(ref) {
  var max = window.TOOL_MAX_VERSES;
  if (!max) return false; // no limit set for this tool
  var est = window.BibCrit_estimateVerseCount(ref);
  if (est <= max) return false;
  // Show inline error using the toast system (defined in result-actions.js)
  var msg = (window.BIBCRIT_I18N && window.BIBCRIT_I18N['err_passage_too_long'])
    ? window.BIBCRIT_I18N['err_passage_too_long'].replace('{max}', max)
    : 'Passage too long. Please keep to ' + max + ' verses or fewer.';
  if (window.showToast) {
    window.showToast(msg, 'error');
  } else {
    // Fallback: inline error below the analyze button
    var btn = document.getElementById('btn-analyze');
    if (btn) {
      var err = document.getElementById('_passage-len-err');
      if (!err) {
        err = document.createElement('p');
        err.id = '_passage-len-err';
        err.style.cssText = 'color:#c0392b;font-size:.85rem;margin:.4rem 0 0;';
        btn.parentNode.insertBefore(err, btn.nextSibling);
      }
      err.textContent = msg;
      setTimeout(function() { if (err.parentNode) err.textContent = ''; }, 6000);
    }
  }
  return true;
};
