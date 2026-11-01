(function () {
  'use strict';
  document.querySelectorAll('[data-hero-video-slide]').forEach(function (slide) {
  var video = slide.querySelector('[data-hero-video]');
  var playButton = slide.querySelector('[data-video-play]');
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var userPaused = false;
  function updateControls() {
    playButton.textContent = video.paused ? 'پخش ویدئو' : 'توقف ویدئو';
    playButton.setAttribute('aria-label', playButton.textContent);
  }
  function tryPlay() {
    var result = video.play();
    if (result && result.catch) result.catch(function () { updateControls(); });
  }
  function syncSlide() {
    var active = slide.classList.contains('swiper-slide-active') && !document.hidden;
    if (!active) {
      video.pause(); video.muted = true; userPaused = false;
    } else if (!reduceMotion.matches && !userPaused && video.paused) {
      video.muted = true; tryPlay();
    }
    updateControls();
  }
  playButton.addEventListener('click', function (event) {
    event.stopPropagation();
    if (video.paused) { userPaused = false; tryPlay(); }
    else { userPaused = true; video.pause(); }
    updateControls();
  });
  video.addEventListener('play', updateControls);
  video.addEventListener('pause', updateControls);
  new MutationObserver(syncSlide).observe(slide, {attributes:true, attributeFilter:['class']});
  document.addEventListener('visibilitychange', syncSlide);
  syncSlide();
  });
}());
