/**
 * admin-sidebar-fix.js — مدیریت پویای عرض سایدبار
 * مشکل: قانون width: var(--larkon-sidebar-width) !important در admin-rtl.css
 * با انتخابگر body.larkon-admin #jazzy-sidebar (specificity 1,1,1) وجود دارد
 * و حتی قوانین با specificity بالاتر در مدیا‌کوئری‌ها به‌درستی اعمال نمی‌شوند.
 * این اسکریپت عرض سایدبار را در حالت جمع‌شده و موبایل به‌صورت پویا تنظیم می‌کند.
 */
(function () {
  'use strict';

  var SIDEBAR_SELECTOR = '#jazzy-sidebar, .main-sidebar';
  var COLLAPSED_WIDTH = '73.6px'; // 4.6rem
  var MOBILE_WIDTH = 'min(286px, 85vw)';

  function getSidebar() {
    return document.querySelector(SIDEBAR_SELECTOR);
  }

  function isCollapsed() {
    return document.body.classList.contains('sidebar-collapse') &&
           document.body.classList.contains('sidebar-mini');
  }

  function isMobile() {
    return window.innerWidth < 992;
  }

  function isSidebarOpen() {
    return document.body.classList.contains('sidebar-open');
  }

  function updateSidebarWidth() {
    var sidebar = getSidebar();
    if (!sidebar) return;

    if (isCollapsed() && !isMobile()) {
      // حالت جمع‌شده در دسکتاپ
      sidebar.style.setProperty('width', COLLAPSED_WIDTH, 'important');
    } else if (isMobile()) {
      // حالت موبایل
      sidebar.style.setProperty('width', MOBILE_WIDTH, 'important');
    } else {
      // حالت عادی — پاک کردن عرض اعمال‌شده
      sidebar.style.removeProperty('width');
    }
  }

  // مشاهدهٔ تغییرات کلاس‌های body
  var observer = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      if (mutations[i].attributeName === 'class') {
        updateSidebarWidth();
        break;
      }
    }
  });

  function init() {
    var sidebar = getSidebar();
    if (!sidebar) return;

    observer.observe(document.body, { attributes: true });
    window.addEventListener('resize', updateSidebarWidth);
    updateSidebarWidth();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
