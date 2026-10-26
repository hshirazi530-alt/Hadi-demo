/* Digital Goods slider — homepage
 * Swiper instance + subtle GSAP entrance animation, mirroring the hero
 * slider behaviour (autoplay, dots, arrows, pause toggle, a11y).
 */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

  function animate(slider) {
    if (reduced.matches) return;
    var slide = slider.slides[slider.activeIndex];
    if (!slide) return;
    var items = slide.querySelectorAll(".hm-digital-slide__content > *");
    var media = slide.querySelector(".hm-digital-slide__media-frame img");
    if (!items.length && !media) return;

    var set = function (el, props) {
      for (var k in props) el.style[k] = props[k];
    };

    items.forEach(function (el) {
      set(el, { transform: "translateY(14px)", opacity: "0", willChange: "transform, opacity" });
    });
    if (media) set(media, { transform: "scale(1.04)", willChange: "transform" });

    requestAnimationFrame(function () {
      items.forEach(function (el, i) {
        el.style.transition = "transform 0.5s cubic-bezier(0.22, 1, 0.36, 1) " + (i * 55) + "ms, opacity 0.5s ease " + (i * 55) + "ms";
        set(el, { transform: "translateY(0)", opacity: "1" });
      });
      if (media) {
        media.style.transition = "transform 0.7s cubic-bezier(0.22, 1, 0.36, 1)";
        set(media, { transform: "scale(1)" });
      }

      setTimeout(function () {
        items.forEach(function (el) { el.style.willChange = "auto"; });
        if (media) media.style.willChange = "auto";
      }, 900);
    });
  }

  function syncToggle(btn, running) {
    if (!btn) return;
    btn.setAttribute("aria-pressed", String(!running));
    btn.setAttribute("aria-label", running ? "توقف پخش خودکار" : "ادامهٔ پخش خودکار");
    var icon = btn.querySelector("[data-digital-autoplay-icon]");
    var label = btn.querySelector("[data-digital-autoplay-label]");
    if (icon) icon.textContent = running ? "Ⅱ" : "▶";
    if (label) label.textContent = running ? "توقف" : "ادامه";
  }

  function init(container) {
    if (container.dataset.digitalReady === "true") return;
    var slides = container.querySelectorAll(".swiper-slide");
    var controls = container.querySelector("[data-digital-controls]");
    var prev = container.querySelector("[data-digital-prev]");
    var next = container.querySelector("[data-digital-next]");
    var dots = container.querySelector("[data-digital-dots]");
    var toggle = container.querySelector("[data-digital-autoplay]");

    if (slides.length < 2) {
      if (controls) controls.hidden = true;
      container.classList.add("is-single");
      return;
    }
    container.dataset.digitalReady = "true";

    var slider = new Swiper(container, {
      slidesPerView: 1,
      speed: reduced.matches ? 0 : 620,
      rewind: true,
      watchOverflow: true,
      keyboard: { enabled: true, onlyInViewport: true },
      a11y: {
        enabled: true,
        containerRoleDescriptionMessage: "اسلایدر",
        itemRoleDescriptionMessage: "اسلاید",
        prevSlideMessage: "اسلاید قبلی",
        nextSlideMessage: "اسلاید بعدی",
        paginationBulletMessage: "رفتن به اسلاید {{index}}",
      },
      autoplay: reduced.matches ? false : { delay: 6000, disableOnInteraction: false, pauseOnMouseEnter: true },
      navigation: { nextEl: next, prevEl: prev, disabledClass: "is-disabled" },
      pagination: {
        el: dots,
        clickable: true,
        bulletElement: "button",
        bulletClass: "hm-digital-promo__dot",
        bulletActiveClass: "is-active",
      },
      on: {
        init: function (s) { animate(s); syncToggle(toggle, !!(s.autoplay && s.autoplay.running)); },
        slideChangeTransitionStart: animate,
      },
    });

    if (toggle) {
      toggle.addEventListener("click", function () {
        if (slider.autoplay.running) {
          slider.autoplay.stop();
          syncToggle(toggle, false);
        } else {
          slider.autoplay.start();
          syncToggle(toggle, true);
        }
      });
    }

    if ("ResizeObserver" in window) {
      var frame = 0;
      new ResizeObserver(function () {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(function () { slider.update(); });
      }).observe(container);
    }

    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) slider.update();
    });
  }

  function boot() {
    document.querySelectorAll("[data-digital-slider]").forEach(init);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
