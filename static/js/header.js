/**
 * Sticky header state.
 *
 * The header is `position: sticky` in CSS; this file only toggles the
 * compact `.is-scrolled` state. An IntersectionObserver on a 1x10px
 * sentinel at the top of the document is used instead of a scroll
 * listener, so the browser does the intersection work off the main
 * thread. A rAF-throttled scroll fallback covers older engines.
 *
 * The threshold is 10px: enough to ignore sub-pixel rubber-banding on
 * iOS while still reacting before the first fold scrolls away.
 */
(function () {
  'use strict';

  var THRESHOLD = 10;
  var header = document.querySelector('[data-hm-header]') || document.querySelector('.hm-header');
  var sentinel = document.querySelector('[data-header-sentinel]');

  if (!header) return;

  function apply(scrolled) {
    if (header.classList.contains('is-scrolled') === scrolled) return;
    header.classList.toggle('is-scrolled', scrolled);
  }

  if (sentinel && 'IntersectionObserver' in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        apply(!entries[0].isIntersecting);
      },
      { rootMargin: '-' + THRESHOLD + 'px 0px 0px 0px', threshold: 0 }
    );
    observer.observe(sentinel);
    return;
  }

  // Fallback: single rAF-guarded listener, passive.
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      apply(window.pageYOffset > THRESHOLD);
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
