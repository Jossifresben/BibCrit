/* Aramaic Root Atlas — Guided Tour (Driver.js v1) */
(function () {
    'use strict';

    var I18N      = window.TOUR_I18N  || {};
    var IS_RTL    = window.TOUR_IS_RTL || false;
    var STORAGE   = 'atlas_tour_seen';
    var isHome    = window.location.pathname === '/';

    function t(key) { return I18N[key] || ''; }

    /* ---- Build step list ----------------------------------------- */
    function buildSteps() {
        var steps = [];

        // Step 1: Welcome — brand logo (always present)
        steps.push({
            element: '.nav-brand',
            popover: {
                title: t('welcome_title'),
                description: t('welcome_body'),
                side: 'bottom', align: 'start'
            }
        });

        // Step 2: Browse link
        steps.push({
            element: '#nav-browse',
            popover: {
                title: t('nav_browse_title'),
                description: t('nav_browse_body'),
                side: 'bottom', align: 'start'
            }
        });

        // Step 3: Explore dropdown
        steps.push({
            element: '#nav-explore-btn',
            popover: {
                title: t('nav_explore_title'),
                description: t('nav_explore_body'),
                side: 'bottom', align: 'start'
            }
        });

        // Step 4: Research dropdown
        steps.push({
            element: '#nav-research-btn',
            popover: {
                title: t('nav_research_title'),
                description: t('nav_research_body'),
                side: 'bottom', align: 'start'
            }
        });

        // Steps 5-9 only on homepage (elements won't exist elsewhere)
        if (isHome) {
            steps.push({
                element: '#tab-root',
                popover: {
                    title: t('search_title'),
                    description: t('search_body'),
                    side: 'bottom', align: 'start'
                }
            });
            steps.push({
                element: '#tab-cognate',
                popover: {
                    title: t('cognate_title'),
                    description: t('cognate_body'),
                    side: 'bottom', align: 'start'
                }
            });
            steps.push({
                element: '#tab-meaning',
                popover: {
                    title: t('meaning_title'),
                    description: t('meaning_body'),
                    side: 'bottom', align: 'start'
                }
            });
            steps.push({
                element: '#tab-text',
                popover: {
                    title: t('text_title'),
                    description: t('text_body'),
                    side: 'bottom', align: 'start'
                }
            });
            steps.push({
                element: '.browse-btn',
                popover: {
                    title: t('reader_title'),
                    description: t('reader_body'),
                    side: 'top', align: 'center'
                }
            });
        }

        // Step 10: Settings (always present)
        steps.push({
            element: '#settings-toggle',
            popover: {
                title: t('settings_title'),
                description: t('settings_body'),
                side: IS_RTL ? 'left' : 'left', align: 'start'
            }
        });

        // Step 11: Language selector (always present)
        steps.push({
            element: '#lang-toggle',
            popover: {
                title: t('lang_title'),
                description: t('lang_body'),
                side: 'left', align: 'start'
            }
        });

        // Step 12: Bookmarks
        steps.push({
            element: '#nav-bookmarks',
            popover: {
                title: t('bookmarks_title'),
                description: t('bookmarks_body'),
                side: 'left', align: 'start'
            }
        });

        // Step 13: Share / QR
        steps.push({
            element: '#share-toggle',
            popover: {
                title: t('share_title'),
                description: t('share_body'),
                side: 'left', align: 'start'
            }
        });

        // Step 14: The tour button itself — wrap-up
        steps.push({
            element: '#tour-nav-btn',
            popover: {
                title: t('end_title'),
                description: t('end_body'),
                side: 'left', align: 'end'
            }
        });

        return steps;
    }

    /* ---- Launch tour --------------------------------------------- */
    function startTour() {
        // Driver.js v1 IIFE bundles as window.driver.js.driver
        // (the ".js" suffix in the filename becomes a property key on window.driver)
        var driverFn = (window.driver && window.driver.js && typeof window.driver.js.driver === 'function')
            ? window.driver.js.driver
            : typeof window.driver === 'function'
                ? window.driver
                : null;

        if (!driverFn) {
            console.warn('Aramaic Root Atlas: Driver.js not loaded — tour unavailable.');
            return;
        }

        var driverObj = driverFn({
            showProgress:  true,
            animate:       true,
            allowClose:    true,
            overlayColor:  'rgba(0,0,0,0.6)',
            nextBtnText:   t('next')   || 'Next',
            prevBtnText:   IS_RTL ? '→' : '←',
            doneBtnText:   t('finish') || 'Done',
            popoverClass:  'atlas-tour-popover' + (IS_RTL ? ' atlas-tour-rtl' : ''),
            steps: buildSteps(),
            onDestroyStarted: function () {
                localStorage.setItem(STORAGE, '1');
                hideTourBtn();
                driverObj.destroy();
            }
        });

        driverObj.drive();
    }

    /* ---- Hide/show the homepage "Guided Tour" button -------------- */
    function hideTourBtn() {
        var btn = document.querySelector('#tour-start-container .tour-start-btn');
        if (btn) btn.style.display = 'none';

        var hint = document.getElementById('tour-restart-hint');
        if (hint) {
            hint.style.display = 'block';
            hint.style.opacity = '1';
            setTimeout(function () {
                hint.style.opacity = '0';
                setTimeout(function () { hint.style.display = 'none'; }, 650);
            }, 4000);
        }
    }

    function syncTourBtn() {
        if (!localStorage.getItem(STORAGE)) return;
        var btn = document.querySelector('#tour-start-container .tour-start-btn');
        if (btn) btn.style.display = 'none';
    }

    /* ---- Called by the homepage button ----------------------------- */
    window.startTourFromBtn = function () {
        startTour();
    };

    /* ---- Expose globally so onclick="startTour()" works ----------- */
    window.startTour = startTour;

    /* ---- Tour nav-button click (always force-restart) ------------- */
    document.addEventListener('DOMContentLoaded', function () {
        syncTourBtn();   // hide if already seen

        var btn = document.getElementById('tour-nav-btn');
        if (btn) {
            btn.addEventListener('click', function () {
                localStorage.removeItem(STORAGE);
                startTour();
            });
        }
    });

    /* Auto-start removed — user clicks the Guided Tour button explicitly. */

    /* ---- ?tour=1 deep-link support -------------------------------- */
    if (new URLSearchParams(window.location.search).get('tour') === '1') {
        window.addEventListener('load', function () {
            setTimeout(startTour, 400);
        });
    }

})();
