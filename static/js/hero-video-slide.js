(function () {
  'use strict';
  var slide = document.querySelector('[data-hero-video-slide]');
  if (!slide) return;
  var video = slide.querySelector('[data-hero-video]');
  var playButton = slide.querySelector('[data-video-play]');
  var soundButton = slide.querySelector('[data-video-sound]');
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var userPaused = false;
  function updateControls() {
    playButton.textContent = video.paused ? 'پخش ویدئو' : 'توقف ویدئو';
    playButton.setAttribute('aria-label', playButton.textContent);
    soundButton.textContent = video.muted ? 'فعال‌کردن صدا' : 'بی‌صدا کردن';
    soundButton.setAttribute('aria-label', soundButton.textContent);
    soundButton.setAttribute('aria-pressed', String(!video.muted));
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
  soundButton.addEventListener('click', function (event) {
    event.stopPropagation();
    video.muted = !video.muted;
    if (!video.muted && video.paused) { userPaused = false; tryPlay(); }
    updateControls();
  });
  video.addEventListener('play', updateControls);
  video.addEventListener('pause', updateControls);
  video.addEventListener('volumechange', updateControls);
  new MutationObserver(syncSlide).observe(slide, {attributes:true, attributeFilter:['class']});
  document.addEventListener('visibilitychange', syncSlide);
  syncSlide();
}());
