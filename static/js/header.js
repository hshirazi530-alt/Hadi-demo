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

// Category links can overflow on narrow screens. Bring the focused link into
// view without scrolling the page away from the header.
(function () {
  'use strict';
  var list = document.querySelector('.hm-cats__list');
  if (!list) return;
  list.addEventListener('focusin', function (event) {
    var link = event.target.closest('.hm-cats__link');
    if (link && list.contains(link)) {
      link.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'auto' });
    }
  });
})();

// Two-column category navigation. Details/summary provides the basic click
// and keyboard interaction even without this enhancement.
(function () {
  'use strict';
  var menu = document.querySelector('[data-category-menu]');
  if (!menu) return;
  var trigger = menu.querySelector('summary');
  var links = Array.prototype.slice.call(menu.querySelectorAll('[data-category-target]'));
  var panels = Array.prototype.slice.call(menu.querySelectorAll('.hm-category-flyout__panel'));
  var openedByHover = false;
  var pinnedOpen = false;
  var pointerInside = false;

  function syncExpanded() {
    trigger.setAttribute('aria-expanded', menu.open ? 'true' : 'false');
  }
  menu.addEventListener('toggle', syncExpanded);
  syncExpanded();

  function activate(link) {
    var target = document.getElementById(link.getAttribute('data-category-target'));
    if (!target || !menu.contains(target)) return;
    links.forEach(function (item) { item.classList.toggle('is-current', item === link); });
    panels.forEach(function (panel) { panel.hidden = panel !== target; });
  }

  function closeMenu() {
    menu.open = false;
    openedByHover = false;
    pinnedOpen = false;
  }

  menu.addEventListener('pointerenter', function (event) {
    if (event.pointerType !== 'mouse') return;
    pointerInside = true;
    if (!menu.open) {
      openedByHover = true;
      menu.open = true;
    }
  });
  menu.addEventListener('pointerleave', function (event) {
    if (event.pointerType !== 'mouse') return;
    pointerInside = false;
    if (openedByHover && !pinnedOpen && !menu.contains(document.activeElement)) closeMenu();
  });
  trigger.addEventListener('click', function (event) {
    if (menu.open && openedByHover && !pinnedOpen) {
      // A click on a hover-open menu pins it instead of immediately closing it.
      event.preventDefault();
      pinnedOpen = true;
      openedByHover = false;
    } else {
      pinnedOpen = !menu.open;
      openedByHover = false;
    }
  });
  menu.addEventListener('pointerover', function (event) {
    if (event.pointerType !== 'mouse') return;
    var active = document.activeElement;
    if (active && active.closest && active.closest('.hm-category-flyout__panel')) return;
    var link = event.target.closest('[data-category-target]');
    if (link && menu.contains(link)) activate(link);
  });
  menu.addEventListener('focusin', function (event) {
    var link = event.target.closest('[data-category-target]');
    if (link && menu.contains(link)) activate(link);
  });
  menu.addEventListener('focusout', function (event) {
    if (!menu.contains(event.relatedTarget) && !pointerInside) closeMenu();
  });
  document.addEventListener('pointerdown', function (event) {
    if (menu.open && !menu.contains(event.target)) closeMenu();
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape' || !menu.open) return;
    closeMenu();
    trigger.focus({ preventScroll: true });
    event.preventDefault();
    event.stopPropagation();
  });
})();
