/**
 * Main products slider — Swiper 11, tree-shaken ESM.
 *
 * Mirrors the hero-slider architecture: Swiper owns gestures, translate and
 * loop logic. Cards keep a fixed width so `slidesPerView: "auto"` preserves
 * card proportions at every breakpoint (4 / 3 / 1) without JS measurement.
 *
 * Bundled by `npm run build:products` into static/build/product-slider.js.
 */
import Swiper from 'swiper';
import { Navigation, Pagination, Keyboard, A11y } from 'swiper/modules';
import 'swiper/css';

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)');

function initProductSlider(root) {
  const slides = root.querySelectorAll('.swiper-slide');
  const controls = root.querySelector('[data-product-controls]');
  const nextEl = root.querySelector('[data-product-next]');
  const prevEl = root.querySelector('[data-product-prev]');
  const dotsEl = root.querySelector('[data-product-dots]');

  // Fewer slides than a single viewport needs no controls and no engine.
  if (slides.length < 2) {
    if (controls) controls.hidden = true;
    return null;
  }

  const swiper = new Swiper(root, {
    modules: [Navigation, Pagination, Keyboard, A11y],
    slidesPerView: 'auto',
    spaceBetween: 18,
    speed: REDUCED_MOTION.matches ? 0 : 520,
    rewind: true,
    watchOverflow: true,
    keyboard: { enabled: true, onlyInViewport: true },
    a11y: {
      enabled: true,
      containerRoleDescriptionMessage: 'اسلایدر محصولات',
      itemRoleDescriptionMessage: 'محصول',
      prevSlideMessage: 'محصول قبلی',
      nextSlideMessage: 'محصول بعدی',
      paginationBulletMessage: 'رفتن به محصول {{index}}',
    },
    navigation: { nextEl, prevEl, disabledClass: 'is-disabled' },
    pagination: {
      el: dotsEl,
      clickable: true,
      bulletElement: 'button',
      bulletClass: 'hm-product-slider__dot',
      bulletActiveClass: 'is-active',
    },
  });

  // The slider may live in a container whose width settles late (fonts,
  // responsive images). Re-measure instead of assuming init width is final.
  if ('ResizeObserver' in window) {
    let frame = 0;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => swiper.update());
    });
    observer.observe(root);
  }

  return swiper;
}

const roots = document.querySelectorAll('[data-product-slider]');
roots.forEach((root) => {
  if (root.dataset.productReady === 'true') return;
  const instance = initProductSlider(root);
  if (instance) root.dataset.productReady = 'true';
});
