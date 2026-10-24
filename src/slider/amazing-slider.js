/**
 * Amazing offers slider + countdown — Swiper 11, tree-shaken ESM.
 *
 * The countdown is driven by a deadline timestamp rendered by the server
 * (AmazingOffersSettings.deadline) so every visitor sees the same end time.
 * The timer uses a single rAF loop that throttles to 1 update/second and
 * hides itself entirely when the deadline has passed.
 *
 * Bundled by `npm run build:amazing` into static/build/amazing-slider.js.
 */
import Swiper from 'swiper';
import { Navigation, Keyboard, A11y } from 'swiper/modules';
import 'swiper/css';

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)');

const PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

function toPersian(value) {
  return String(value).replace(/\d/g, (d) => PERSIAN_DIGITS[Number(d)]);
}

function padTwo(value) {
  return String(value).padStart(2, '0');
}

function initTimer(root) {
  const deadlineAttr = root.dataset.amazingDeadline;
  if (!deadlineAttr) return;

  const deadline = Date.parse(deadlineAttr);
  if (Number.isNaN(deadline)) return;

  const digits = root.querySelector('[data-amazing-digits]');
  const ended = root.querySelector('[data-amazing-ended]');
  const hoursEl = root.querySelector('[data-amazing-hours]');
  const minutesEl = root.querySelector('[data-amazing-minutes]');
  const secondsEl = root.querySelector('[data-amazing-seconds]');

  let lastTick = -1;

  function render(totalSeconds) {
    if (totalSeconds <= 0) {
      if (digits) digits.hidden = true;
      if (ended) ended.hidden = false;
      root.setAttribute('aria-live', 'off');
      return false;
    }

    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hoursEl) hoursEl.textContent = toPersian(padTwo(Math.min(hours, 99)));
    if (minutesEl) minutesEl.textContent = toPersian(padTwo(minutes));
    if (secondsEl) secondsEl.textContent = toPersian(padTwo(seconds));
    return true;
  }

  function frame() {
    const remaining = Math.floor((deadline - Date.now()) / 1000);
    if (remaining !== lastTick) {
      lastTick = remaining;
      const alive = render(remaining);
      if (!alive) return; // deadline passed: stop the loop
    }
    requestAnimationFrame(frame);
  }

  // Run once immediately so the timer never flashes 00:00:00.
  const remaining = Math.floor((deadline - Date.now()) / 1000);
  if (remaining <= 0) {
    render(0);
    return;
  }
  render(remaining);
  requestAnimationFrame(frame);
}

function initSlider(root) {
  const slides = root.querySelectorAll('.swiper-slide');
  const controls = root.querySelector('[data-amazing-controls]');
  const nextEl = root.querySelector('[data-amazing-next]');
  const prevEl = root.querySelector('[data-amazing-prev]');

  if (slides.length < 2) {
    if (controls) controls.hidden = true;
    return null;
  }

  const swiper = new Swiper(root, {
    modules: [Navigation, Keyboard, A11y],
    slidesPerView: 'auto',
    spaceBetween: 14,
    speed: REDUCED_MOTION.matches ? 0 : 520,
    rewind: true,
    watchOverflow: true,
    keyboard: { enabled: true, onlyInViewport: true },
    a11y: {
      enabled: true,
      containerRoleDescriptionMessage: 'اسلایدر شگفت‌انگیز',
      itemRoleDescriptionMessage: 'محصول شگفت‌انگیز',
      prevSlideMessage: 'محصول قبلی',
      nextSlideMessage: 'محصول بعدی',
    },
    navigation: { nextEl, prevEl, disabledClass: 'is-disabled' },
  });

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

document.querySelectorAll('[data-amazing-timer]').forEach(initTimer);
document.querySelectorAll('[data-amazing-slider]').forEach((root) => {
  if (root.dataset.amazingReady === 'true') return;
  const instance = initSlider(root);
  if (instance) root.dataset.amazingReady = 'true';
});
