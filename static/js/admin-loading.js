(function () {
  'use strict';

  var loader = document.getElementById('hjm-admin-loader');
  if (!loader) return;

  var hidden = false;
  var hideTimer;

  function showLoader() {
    window.clearTimeout(hideTimer);
    hidden = false;
    loader.hidden = false;
    loader.classList.remove('is-hidden');
    loader.removeAttribute('aria-hidden');
  }

  function hideLoader() {
    if (hidden) return;

    hidden = true;
    window.clearTimeout(loadFallbackTimer);
    loader.classList.add('is-hidden');
    loader.setAttribute('aria-hidden', 'true');
    hideTimer = window.setTimeout(function () {
      loader.hidden = true;
    }, 260);
  }

  function onPageLoaded() {
    window.setTimeout(hideLoader, 220);
  }

  if (document.readyState === 'complete') onPageLoaded();
  else window.addEventListener('load', onPageLoaded, { once: true });

  var loadFallbackTimer = window.setTimeout(hideLoader, 15000);

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.matches('[data-no-admin-loader], [data-ajax], [data-ajax-submit]')) return;
    if (form.target && form.target !== '_self') return;
    if (form.method.toLowerCase() === 'dialog') return;

    window.setTimeout(function () {
      if (!event.defaultPrevented) showLoader();
    }, 0);
  }, true);

  document.addEventListener('click', function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    var link = event.target.closest('a[href]');
    if (!link || link.hasAttribute('download')) return;
    if (link.target && link.target !== '_self') return;
    if (link.closest('[data-toggle], [data-widget], .dropdown-toggle')) return;

    var destination = new URL(link.href, window.location.href);
    if (destination.origin !== window.location.origin || !destination.pathname.startsWith('/admin/')) return;
    if (destination.pathname === window.location.pathname && destination.search === window.location.search) return;

    window.setTimeout(function () {
      if (!event.defaultPrevented) showLoader();
    }, 0);
  }, true);

  window.addEventListener('pageshow', function (event) {
    if (event.persisted) hideLoader();
  });
})();
