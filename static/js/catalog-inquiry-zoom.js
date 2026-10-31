(function () {
  'use strict';
  function ready() {
    var surface = document.querySelector('[data-inquiry-zoom]');
    var dialog = document.querySelector('[data-image-zoom-dialog]');
    if (!surface || !dialog) return;
    var image = surface.querySelector('img');
    var button = surface.querySelector('[data-inquiry-zoom-button]');
    if (!image || !button) return;
    function open() {
      var target = dialog.querySelector('[data-image-zoom-view]');
      var caption = dialog.querySelector('[data-image-zoom-caption]');
      target.src = image.currentSrc || image.src; target.alt = image.alt;
      caption.textContent = image.alt;
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else window.open(target.src, '_blank', 'noopener,noreferrer');
    }
    button.addEventListener('click', open);
    image.addEventListener('click', open);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
})();
