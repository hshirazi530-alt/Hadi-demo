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

/* --------------------------------------------------------------------------
   Background motion slides (the IPL care slide).
   Plays only while the slide is active and the tab is visible, so the
   animation costs nothing when the visitor is looking elsewhere. With
   prefers-reduced-motion the poster frame stays and the video never loads.
   -------------------------------------------------------------------------- */
(function () {
  'use strict';
  var slides = document.querySelectorAll('[data-hero-animated-slide]');
  if (!slides.length) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  slides.forEach(function (slide) {
    var video = slide.querySelector('[data-hero-motion]');
    if (!video) return;

    var loaded = false;   // guard: load() must run once, or it aborts the download
    var enableMotion = false; // becomes true only once the slide has been seen

    function ensureLoaded() {
      if (loaded || reduceMotion.matches) return;
      loaded = true;
      video.preload = 'auto';
      video.load();
    }

    function play() {
      if (!enableMotion || reduceMotion.matches || document.hidden) return;
      var result = video.play();
      if (result && result.catch) result.catch(function () {});
    }

    function sync() {
      var active = slide.classList.contains('swiper-slide-active') && !document.hidden;
      if (active) {
        // Only the first activation pays the network cost; afterwards the
        // buffer is reused, so looping back is instant.
        enableMotion = true;
        ensureLoaded();
        play();
      } else if (enableMotion) {
        video.pause();
      }
    }

    if (reduceMotion.addEventListener) reduceMotion.addEventListener('change', sync);
    new MutationObserver(sync).observe(slide, {attributes: true, attributeFilter: ['class']});
    document.addEventListener('visibilitychange', sync);
    sync();
  });
}());
