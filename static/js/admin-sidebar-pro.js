/**
 * admin-sidebar-pro.js — زیرمنوهای جمع‌شونده و مدیریت سایدبار حرفه‌ای
 * منوی تخت (flat) پنل ادمین را به منوی گروه‌بندی‌شده با زیرمنو تبدیل می‌کند.
 */
(function () {
  'use strict';

  var TREEVIEW_SELECTOR = '.nav-sidebar';
  var COLLAPSED_WIDTH = '4.6rem';
  var MOBILE_WIDTH = 'min(286px, 85vw)';

  /* ---- تعریف گروه‌بندی منو ----
   * هر گروه: { title, icon, items: [url, ...] }
   * آیتم‌هایی که در groups نباشند در گروه «سایر» قرار می‌گیرند.
   */
  var GROUPS = [
    {
      title: 'فروشگاه',
      icon: 'fas fa-store',
      items: [
        '/admin/core/product',
        '/admin/core/category',
        '/admin/core/subcategory',
        '/admin/core/vendor',
        '/admin/core/coupon',
        '/admin/core/productbundle'
      ]
    },
    {
      title: 'سفارشات',
      icon: 'fas fa-receipt',
      items: [
        '/admin/core/cartorder',
        '/admin/core/cartorderproducts',
        '/admin/core/paymentattempt'
      ]
    },
    {
      title: 'محتوا و بازاریابی',
      icon: 'fas fa-bullhorn',
      items: [
        '/admin/core/herobanner',
        '/admin/core/banner',
        '/admin/core/digitalbanner',
        '/admin/core/amazingofferssettings',
        '/admin/core/storetrustfeature',
        '/admin/core/faq',
        '/admin/core/productreview'
      ]
    },
    {
      title: 'کاربران',
      icon: 'fas fa-users',
      items: [
        '/admin/userauths/user',
        '/admin/userauths/profile',
        '/admin/userauths/contactus',
        '/admin/auth/group'
      ]
    },
    {
      title: 'سایر',
      icon: 'fas fa-ellipsis-h',
      items: [
        '/admin/core/address',
        '/admin/core/wishlist_model',
        '/admin/ipn/paypalipn',
        '/admin/taggit/tag'
      ]
    }
  ];

  var ICON_BY_URL = {
    '/admin/core/product': 'fas fa-box-open',
    '/admin/core/category': 'fas fa-tags',
    '/admin/core/subcategory': 'fas fa-layer-group',
    '/admin/core/vendor': 'fas fa-store-alt',
    '/admin/core/coupon': 'fas fa-percent',
    '/admin/core/productbundle': 'fas fa-gift',
    '/admin/core/cartorder': 'fas fa-shopping-cart',
    '/admin/core/cartorderproducts': 'fas fa-boxes',
    '/admin/core/paymentattempt': 'fas fa-credit-card',
    '/admin/core/herobanner': 'fas fa-images',
    '/admin/core/banner': 'fas fa-image',
    '/admin/core/digitalbanner': 'fas fa-desktop',
    '/admin/core/amazingofferssettings': 'fas fa-fire',
    '/admin/core/storetrustfeature': 'fas fa-shield-alt',
    '/admin/core/faq': 'fas fa-question-circle',
    '/admin/core/productreview': 'fas fa-star',
    '/admin/userauths/user': 'fas fa-user',
    '/admin/userauths/profile': 'fas fa-id-card',
    '/admin/userauths/contactus': 'fas fa-envelope',
    '/admin/auth/group': 'fas fa-users-cog',
    '/admin/core/address': 'fas fa-map-marker-alt',
    '/admin/core/wishlist_model': 'fas fa-heart',
    '/admin/ipn/paypalipn': 'fas fa-paypal',
    '/admin/taggit/tag': 'fas fa-hashtag'
  };

  function getSidebar() {
    return document.querySelector('.main-sidebar, #jazzy-sidebar');
  }

  function getNav() {
    var sb = getSidebar();
    return sb ? sb.querySelector(TREEVIEW_SELECTOR) : null;
  }

  /* ---- ساخت ساختار درختی منو ---- */
  function buildTree() {
    var nav = getNav();
    if (!nav) return;
    if (nav.getAttribute('data-hjm-tree') === '1') return; // جلوگیری از اجرای دوباره

    var currentPath = window.location.pathname.replace(/\/+$/, '');
    var itemMap = {};   // url -> li element
    var allItems = Array.prototype.slice.call(nav.querySelectorAll(':scope > li.nav-item'));

    allItems.forEach(function (li) {
      var link = li.querySelector('a.nav-link');
      if (!link) return;
      var href = link.getAttribute('href') || '';
      href = href.replace(/\/+$/, '');
      if (href) itemMap[href] = li;
    });

    var dashboardItem = itemMap['/admin'];
    var fragment = document.createDocumentFragment();

    // 1) داشبورد اول
    if (dashboardItem) {
      fragment.appendChild(dashboardItem);
    }

    // 2) گروه‌ها
    GROUPS.forEach(function (group) {
      var groupItems = [];
      group.items.forEach(function (url) {
        var li = itemMap[url];
        if (li) {
          groupItems.push(li);
          delete itemMap[url];
        }
      });
      if (!groupItems.length) return;

      var groupLi = document.createElement('li');
      groupLi.className = 'nav-item has-treeview';
      groupLi.setAttribute('data-group', group.title);

      var groupLink = document.createElement('a');
      groupLink.className = 'nav-link menu-arrow';
      groupLink.setAttribute('href', '#');
      groupLink.setAttribute('role', 'button');
      groupLink.setAttribute('aria-expanded', 'false');

      var icon = document.createElement('i');
      icon.className = 'nav-icon ' + group.icon;

      var p = document.createElement('p');
      p.textContent = group.title;

      var arrow = document.createElement('i');
      arrow.className = 'right fas fa-angle-left';

      groupLink.appendChild(icon);
      groupLink.appendChild(p);
      groupLink.appendChild(arrow);

      var sub = document.createElement('ul');
      sub.className = 'nav nav-treeview';
      sub.setAttribute('role', 'menu');

      groupItems.forEach(function (li) {
        // آیکن آیتم را بهبود بزن
        var link = li.querySelector('a.nav-link');
        var href = (link.getAttribute('href') || '').replace(/\/+$/, '');
        var iconEl = li.querySelector('.nav-icon');
        if (iconEl && ICON_BY_URL[href]) {
          iconEl.className = 'nav-icon ' + ICON_BY_URL[href];
        }
        // آیتم فعال را روی گروه باز نگه دار
        if (href === currentPath) {
          groupLi.classList.add('menu-open');
          groupLink.setAttribute('aria-expanded', 'true');
        }
        sub.appendChild(li);
      });

      groupLi.appendChild(groupLink);
      groupLi.appendChild(sub);
      fragment.appendChild(groupLi);
    });

    // 3) آیتم‌های باقی‌مانده (در صورت وجود)
    Object.keys(itemMap).forEach(function (url) {
      if (url === '/admin') return;
      fragment.appendChild(itemMap[url]);
    });

    // پاک کردن و افزودن مجدد
    while (nav.firstChild) nav.removeChild(nav.firstChild);
    nav.appendChild(fragment);
    nav.setAttribute('data-hjm-tree', '1');

    // 4) حذف nav-header های قدیمی (گروه‌بندی قبلی)
    nav.querySelectorAll(':scope > li.nav-header').forEach(function (h) {
      h.remove();
    });

    bindToggle();
    updateActiveState();
  }

  /* ---- باز/بسته کردن زیرمنو ---- */
  function bindToggle() {
    var nav = getNav();
    if (!nav) return;
    nav.querySelectorAll('li.has-treeview > a.menu-arrow').forEach(function (link) {
      if (link.getAttribute('data-hjm-bound') === '1') return;
      link.setAttribute('data-hjm-bound', '1');
      link.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var li = link.closest('li.has-treeview');
        if (!li) return;
        var open = li.classList.toggle('menu-open');
        link.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });
  }

  /* ---- وضعیت فعال ---- */
  function updateActiveState() {
    var nav = getNav();
    if (!nav) return;
    var currentPath = window.location.pathname.replace(/\/+$/, '');
    nav.querySelectorAll('a.nav-link').forEach(function (link) {
      var href = (link.getAttribute('href') || '').replace(/\/+$/, '');
      if (!href || href === '#') return;
      if (href === currentPath) {
        link.classList.add('active');
      } else if (href !== '/admin' || currentPath !== '/admin') {
        link.classList.remove('active');
      }
    });
  }

  /* ---- مدیریت عرض سایدبار ---- */
  function isCollapsed() {
    return document.body.classList.contains('sidebar-collapse');
  }

  function isMobile() {
    return window.innerWidth < 992;
  }

  function updateSidebarWidth() {
    var sidebar = getSidebar();
    if (!sidebar) return;
    if (isCollapsed() && !isMobile()) {
      sidebar.style.setProperty('width', COLLAPSED_WIDTH, 'important');
    } else if (isMobile()) {
      sidebar.style.setProperty('width', menuOpen() ? MOBILE_WIDTH : MOBILE_WIDTH, 'important');
    } else {
      sidebar.style.removeProperty('width');
    }
  }

  function menuOpen() {
    return document.body.classList.contains('sidebar-open');
  }

  /* ---- init ---- */
  var observer = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      if (mutations[i].attributeName === 'class') {
        updateSidebarWidth();
        break;
      }
    }
  });

  function init() {
    buildTree();
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