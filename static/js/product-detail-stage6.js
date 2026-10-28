/* Task 6: activate an existing product tab when a link outside the tablist
   targets it. No prices, cart state or product data are changed. */
(function () {
  'use strict';
  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('.hm-product-detail-page [data-tabs-goto]');
    if (!trigger) return;
    var target = trigger.getAttribute('data-tabs-goto');
    var group = document.querySelector('.hm-product-detail-page [data-product-tabs]');
    if (!target || !group) return;
    var tab = Array.from(group.querySelectorAll('[data-tabs-tab]')).find(function (item) {
      return item.getAttribute('data-tabs-target') === target;
    });
    var panel = document.getElementById(target);
    if (!tab || !panel || !group.contains(panel)) return;
    event.preventDefault();
    tab.click();
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    panel.scrollIntoView({behavior: reduce ? 'auto' : 'smooth', block: 'start'});
    try { panel.focus({preventScroll: true}); } catch (_) { panel.focus(); }
  });
})();
