(function () {
  'use strict';

  var body = document.body;
  if (body.classList.contains('larkon-admin') && body.classList.contains('sidebar-collapse')) {
    body.classList.remove('sidebar-collapse');
    document.cookie = 'jazzy_menu=open; path=/; SameSite=Lax';
  }

  var loginEmail = document.querySelector('.login-box input[name="username"]');
  if (loginEmail) {
    loginEmail.type = 'email';
    loginEmail.dir = 'ltr';
    loginEmail.autocomplete = 'username';
    loginEmail.placeholder = 'ایمیل';
    loginEmail.setAttribute('aria-label', 'ایمیل');
  }

  var loginPassword = document.querySelector('.login-box input[name="password"]');
  if (loginPassword) {
    loginPassword.placeholder = 'گذرواژه';
    loginPassword.setAttribute('aria-label', 'گذرواژه');
    loginPassword.autocomplete = 'current-password';
  }

  var globalSearch = document.querySelector('.main-header .form-control-navbar');
  if (globalSearch) {
    globalSearch.placeholder = 'جست‌وجو در محصولات';
    globalSearch.setAttribute('aria-label', 'جست‌وجو در محصولات');
    var searchButton = document.querySelector('.main-header .btn-navbar');
    if (searchButton) searchButton.setAttribute('aria-label', 'جست‌وجو');
  }

  var dashboardLink = document.querySelector('.nav-sidebar > .nav-item > .nav-link p');
  if (dashboardLink) dashboardLink.textContent = 'داشبورد';

  var accountLabel = document.querySelector('#jazzy-usermenu .dropdown-header');
  if (accountLabel) accountLabel.textContent = 'حساب کاربری';

  var profileLink = document.querySelector('#jazzy-usermenu .dropdown-footer');
  if (profileLink) profileLink.textContent = 'نمایش پروفایل';

  var loader = document.getElementById('hjm-admin-loader');
  if (loader) {
    var hidden = false;
    var hideTimer;

    function showLoader() {
      window.clearTimeout(hideTimer);
      hidden = false;
      loader.hidden = false;
      loader.classList.remove('is-hidden');
      loader.removeAttribute('aria-hidden');
    }

    function hideLoader() {
      if (hidden) return;

      hidden = true;
      window.clearTimeout(loadFallbackTimer);
      loader.classList.add('is-hidden');
      loader.setAttribute('aria-hidden', 'true');
      hideTimer = window.setTimeout(function () {
        loader.hidden = true;
      }, 260);
    }

    function onPageLoaded() {
      window.setTimeout(hideLoader, 220);
    }

    if (document.readyState === 'complete') onPageLoaded();
    else window.addEventListener('load', onPageLoaded, { once: true });

    var loadFallbackTimer = window.setTimeout(hideLoader, 15000);

    document.addEventListener('submit', function (event) {
      var form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (form.matches('[data-no-admin-loader], [data-ajax], [data-ajax-submit]')) return;
      if (form.target && form.target !== '_self') return;
      if (form.method.toLowerCase() === 'dialog') return;

      window.setTimeout(function () {
        if (!event.defaultPrevented) showLoader();
      }, 0);
    }, true);

    document.addEventListener('click', function (event) {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      var link = event.target.closest('a[href]');
      if (!link || link.hasAttribute('download')) return;
      if (link.target && link.target !== '_self') return;
      if (link.closest('[data-toggle], [data-widget], .dropdown-toggle')) return;

      var destination = new URL(link.href, window.location.href);
      if (destination.origin !== window.location.origin || !destination.pathname.startsWith('/admin/')) return;
      if (destination.pathname === window.location.pathname && destination.search === window.location.search) return;

      window.setTimeout(function () {
        if (!event.defaultPrevented) showLoader();
      }, 0);
    }, true);

    window.addEventListener('pageshow', function (event) {
      if (event.persisted) hideLoader();
    });
  }

  var sidebar = document.querySelector('.main-sidebar');
  if (sidebar) {
    var searchForm = globalSearch && globalSearch.closest('form');
    if (searchForm) {
      var searchPath = new URL(searchForm.action, window.location.href).pathname.replace(/\/$/, '');
      var hasProductAccess = Array.prototype.some.call(
        sidebar.querySelectorAll('.nav-link[href]'),
        function (link) {
          return new URL(link.href, window.location.href).pathname.replace(/\/$/, '') === searchPath;
        }
      );
      if (!hasProductAccess) searchForm.hidden = true;
    }

    sidebar.querySelectorAll('.has-treeview > .nav-link').forEach(function (link, index) {
      var group = link.parentElement;
      var submenu = group.querySelector('.nav-treeview');
      if (!submenu) return;
      if (!submenu.id) submenu.id = 'admin-menu-group-' + index;
      link.setAttribute('aria-controls', submenu.id);
      link.setAttribute('aria-expanded', String(group.classList.contains('menu-open')));
      link.addEventListener('click', function () {
        window.setTimeout(function () {
          link.setAttribute('aria-expanded', String(group.classList.contains('menu-open')));
        }, 0);
      });
    });

    var sidebarToggle = document.querySelector('[data-widget="pushmenu"]');
    if (sidebarToggle) {
      var isMobileViewport = window.matchMedia('(max-width: 991.98px)').matches;
      var isSidebarCollapsed = body.classList.contains('sidebar-collapse');
      sidebarToggle.setAttribute(
        'aria-label',
        isMobileViewport
          ? 'باز کردن منو'
          : (isSidebarCollapsed ? 'باز کردن نوار کناری' : 'جمع‌کردن نوار کناری')
      );
      sidebarToggle.setAttribute(
        'aria-expanded',
        String(isMobileViewport ? body.classList.contains('sidebar-open') : !isSidebarCollapsed)
      );
      sidebarToggle.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopImmediatePropagation();

        var isMobile = window.matchMedia('(max-width: 991.98px)').matches;
        var stateClass = isMobile ? 'sidebar-open' : 'sidebar-collapse';
        var isVisible = body.classList.toggle(stateClass);
        sidebarToggle.setAttribute('aria-expanded', String(isMobile ? isVisible : !isVisible));
        sidebarToggle.setAttribute(
          'aria-label',
          isMobile
            ? (isVisible ? 'بستن منو' : 'باز کردن منو')
            : (isVisible ? 'باز کردن نوار کناری' : 'جمع‌کردن نوار کناری')
        );
        if (isMobile && isVisible) {
          var firstMenuLink = sidebar.querySelector('.nav-link[href]');
          if (firstMenuLink) firstMenuLink.focus();
        }
      });

      document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape' || !body.classList.contains('sidebar-open')) return;
        body.classList.remove('sidebar-open');
        sidebarToggle.setAttribute('aria-expanded', 'false');
        sidebarToggle.setAttribute('aria-label', 'باز کردن منو');
        sidebarToggle.focus();
      });

      var contentWrapper = document.querySelector('.content-wrapper');
      if (contentWrapper) {
        contentWrapper.addEventListener('click', function (event) {
          if (event.target !== contentWrapper || !body.classList.contains('sidebar-open')) return;
          body.classList.remove('sidebar-open');
          sidebarToggle.setAttribute('aria-expanded', 'false');
          sidebarToggle.setAttribute('aria-label', 'باز کردن منو');
        });
      }

      sidebar.querySelectorAll('.nav-treeview .nav-link').forEach(function (link) {
        link.addEventListener('click', function () {
          if (!window.matchMedia('(max-width: 991.98px)').matches) return;
          body.classList.remove('sidebar-open');
          sidebarToggle.setAttribute('aria-expanded', 'false');
          sidebarToggle.setAttribute('aria-label', 'باز کردن منو');
        });
      });
    }
  }

  var navLinks = document.querySelectorAll('.nav-sidebar .nav-link');
  if (navLinks.length) {
    var currentPath = window.location.pathname.replace(/\/$/, '');
    navLinks.forEach(function (link) {
      var href = (link.getAttribute('href') || '').replace(/\/$/, '');
      if (!href) return;
      if (href === currentPath || (currentPath.indexOf(href) === 0 && href !== '/admin')) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
        var submenu = link.closest('.nav-treeview');
        if (submenu) {
          submenu.style.display = 'block';
          var parentItem = submenu.closest('.has-treeview');
          if (parentItem) {
            parentItem.classList.add('menu-open');
            var parentLink = parentItem.querySelector(':scope > .nav-link');
            if (parentLink) parentLink.setAttribute('aria-expanded', 'true');
          }
        }
      }
    });
  }
})();
