/**
 * Hero slider — Swiper 11, tree-shaken ESM.
 *
 * Swiper owns gestures, translate and loop logic; GSAP is used only for
 * content-level choreography on slide change (never for slide movement).
 * Bundled by `npm run build:slider` into static/js/hero-slider.js (+ .css).
 */
import Swiper from 'swiper';
import { Navigation, Pagination, Keyboard, A11y, Autoplay } from 'swiper/modules';
import { gsap } from 'gsap';
import 'swiper/css';

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)');

function animateSlide(swiper) {
  if (REDUCED_MOTION.matches) return;

  const slide = swiper.slides[swiper.activeIndex];
  if (!slide) return;

  const content = slide.querySelectorAll('.hm-hero__content > *');
  const visual = slide.querySelector('.hm-hero__media img');

  if (visual) {
    visual.style.willChange = 'transform';
  }

  const tl = gsap.timeline({
    defaults: { ease: 'power2.out' },
    onComplete: () => {
      if (visual) visual.style.willChange = 'auto';
    },
  });

  if (content.length) {
    tl.fromTo(
      content,
      { y: 16, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.45, stagger: 0.05 }
    );
  }
  if (visual) {
    tl.fromTo(visual, { scale: 1.03 }, { scale: 1, duration: 0.7 }, 0);
  }
}

function syncAutoplayButton(button, playing) {
  if (!button) return;
  button.setAttribute('aria-pressed', String(!playing));
  button.setAttribute('aria-label', playing ? 'توقف پخش خودکار' : 'ادامهٔ پخش خودکار');
  const icon = button.querySelector('[data-hero-autoplay-icon]');
  const label = button.querySelector('[data-hero-autoplay-label]');
  if (icon) icon.textContent = playing ? 'Ⅱ' : '▶';
  if (label) label.textContent = playing ? 'توقف' : 'ادامه';
}

function initHero(root) {
  const slides = root.querySelectorAll('.swiper-slide');
  const controls = root.querySelector('[data-hero-controls]');
  const nextEl = root.querySelector('[data-hero-next]');
  const prevEl = root.querySelector('[data-hero-prev]');
  const dotsEl = root.querySelector('[data-hero-dots]');
  const autoplayBtn = root.querySelector('[data-hero-autoplay]');

  // A single slide needs no controls and no engine.
  if (slides.length < 2) {
    if (controls) controls.hidden = true;
    return null;
  }

  const swiper = new Swiper(root, {
    modules: [Navigation, Pagination, Keyboard, A11y, Autoplay],
    slidesPerView: 1,
    speed: REDUCED_MOTION.matches ? 0 : 620,
    rewind: true,
    watchOverflow: true,
    keyboard: { enabled: true, onlyInViewport: true },
    a11y: {
      enabled: true,
      containerRoleDescriptionMessage: 'اسلایدر',
      itemRoleDescriptionMessage: 'اسلاید',
      prevSlideMessage: 'اسلاید قبلی',
      nextSlideMessage: 'اسلاید بعدی',
      paginationBulletMessage: 'رفتن به اسلاید {{index}}',
    },
    autoplay: REDUCED_MOTION.matches
      ? false
      : { delay: 5200, disableOnInteraction: false, pauseOnMouseEnter: true },
    navigation: { nextEl, prevEl, disabledClass: 'is-disabled' },
    pagination: {
      el: dotsEl,
      clickable: true,
      bulletElement: 'button',
      bulletClass: 'hm-hero__dot',
      bulletActiveClass: 'is-active',
    },
    on: {
      init(instance) {
        animateSlide(instance);
        syncAutoplayButton(autoplayBtn, !!(instance.autoplay && instance.autoplay.running));
      },
      slideChangeTransitionStart(instance) {
        animateSlide(instance);
      },
    },
  });

  if (autoplayBtn) {
    autoplayBtn.addEventListener('click', () => {
      if (swiper.autoplay.running) {
        swiper.autoplay.stop();
        syncAutoplayButton(autoplayBtn, false);
      } else {
        swiper.autoplay.start();
        syncAutoplayButton(autoplayBtn, true);
      }
    });
  }

  // The slider may live in a container whose width settles late (fonts,
  // responsive images, tab panels). Re-measure instead of assuming init
  // width is final.
  if ('ResizeObserver' in window) {
    let frame = 0;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => swiper.update());
    });
    observer.observe(root);
  }

  // Returning to a backgrounded tab leaves autoplay paused in some
  // browsers; a single update keeps geometry correct without restarting.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) swiper.update();
  });

  return swiper;
}

const roots = document.querySelectorAll('[data-hero-slider]');
roots.forEach((root) => {
  if (root.dataset.heroReady === 'true') return;
  const instance = initHero(root);
  if (instance) root.dataset.heroReady = 'true';
});
