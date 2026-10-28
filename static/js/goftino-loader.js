/* Optional Goftino live-chat widget. No widget or external request without an ID. */
(function () {
  'use strict';
  var source = document.currentScript;
  var id = source && source.getAttribute('data-goftino-id');
  if (!id || !/^[a-zA-Z0-9_-]{6,64}$/.test(id)) return;
  function load() {
    if (document.querySelector('script[data-hm-goftino-loaded]')) return;
    var script = document.createElement('script');
    script.src = 'https://www.goftino.com/widget/' + encodeURIComponent(id);
    script.async = true;
    script.setAttribute('data-hm-goftino-loaded', 'true');
    document.head.appendChild(script);
  }
  if (document.readyState === 'complete') load();
  else window.addEventListener('load', load, { once: true });
}());
