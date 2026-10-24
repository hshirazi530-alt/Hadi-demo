(function () {
  'use strict';

  var body = document.body;
  var sidebar = document.getElementById('jazzy-sidebar');
  var openSidebarButton = document.querySelector('[data-sidebar-open]');
  var closeSidebarButton = document.querySelector('[data-sidebar-close]');
  var collapseSidebarButton = document.querySelector('[data-sidebar-collapse]');
  var themeButton = document.querySelector('[data-theme-toggle]');
  var notificationMenu = document.querySelector('.dashboard-notifications');
  var notificationCount = document.querySelector('[data-notification-count]');
  var notificationValues = document.querySelector('[data-notification-values]');
  var markNotificationsRead = document.querySelector('[data-notifications-read]');

  function setSidebarOpen(isOpen) {
    var wasOpen = body.classList.contains('sidebar-open');
    body.classList.toggle('sidebar-open', isOpen);
    if (openSidebarButton) {
      openSidebarButton.setAttribute('aria-expanded', String(isOpen));
    }
    if (isOpen && sidebar) {
      var firstLink = sidebar.querySelector('a');
      if (firstLink) firstLink.focus();
    } else if (wasOpen && openSidebarButton) {
      openSidebarButton.focus();
    }
  }

  if (openSidebarButton) {
    openSidebarButton.addEventListener('click', function () {
      setSidebarOpen(true);
    });
  }

  if (closeSidebarButton) {
    closeSidebarButton.addEventListener('click', function () {
      setSidebarOpen(false);
    });
  }

  if (sidebar) {
    sidebar.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        setSidebarOpen(false);
      });
    });
  }

  if (collapseSidebarButton) {
    var sidebarIsCollapsed = body.classList.contains('sidebar-collapse');
    collapseSidebarButton.setAttribute('aria-pressed', String(sidebarIsCollapsed));
    collapseSidebarButton.addEventListener('click', function () {
      sidebarIsCollapsed = !body.classList.contains('sidebar-collapse');
      body.classList.toggle('sidebar-collapse', sidebarIsCollapsed);
      body.classList.toggle('sidebar-mini', sidebarIsCollapsed);
      collapseSidebarButton.setAttribute('aria-pressed', String(sidebarIsCollapsed));
      collapseSidebarButton.setAttribute(
        'aria-label',
        sidebarIsCollapsed ? 'بازکردن نوار کناری' : 'جمع‌کردن نوار کناری'
      );
      collapseSidebarButton.setAttribute(
        'title',
        sidebarIsCollapsed ? 'بازکردن نوار کناری' : 'جمع‌کردن نوار کناری'
      );
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      setSidebarOpen(false);
      document.querySelectorAll('.dashboard-menu[open]').forEach(function (menu) {
        menu.removeAttribute('open');
      });
    }
  });

  document.addEventListener('click', function (event) {
    document.querySelectorAll('.dashboard-menu[open]').forEach(function (menu) {
      if (!menu.contains(event.target)) menu.removeAttribute('open');
    });
  });

  var prefersDark = document.documentElement.dataset.adminTheme === 'dark';
  body.classList.toggle('admin-theme-dark', prefersDark);

  function syncThemeButton() {
    if (!themeButton) return;
    var darkEnabled = body.classList.contains('admin-theme-dark');
    var label = darkEnabled ? 'فعال‌کردن تم روشن' : 'فعال‌کردن تم تیره';
    var icon = themeButton.querySelector('i');
    var text = themeButton.querySelector('span');
    themeButton.setAttribute('aria-label', label);
    themeButton.setAttribute('title', label);
    if (icon) icon.className = darkEnabled ? 'fas fa-sun' : 'fas fa-moon';
    if (text) text.textContent = darkEnabled ? 'تم روشن' : 'تم تیره';
  }

  if (themeButton) {
    syncThemeButton();
    themeButton.addEventListener('click', function () {
      var darkEnabled = !body.classList.contains('admin-theme-dark');
      body.classList.toggle('admin-theme-dark', darkEnabled);
      document.documentElement.dataset.adminTheme = darkEnabled ? 'dark' : 'light';
      try {
        localStorage.setItem('hjm-admin-theme', darkEnabled ? 'dark' : 'light');
      } catch (error) {
        console.warn('ذخیره‌سازی تنظیم تم در این مرورگر در دسترس نیست.', error);
      }
      syncThemeButton();
      var settingsMenu = themeButton.closest('.dashboard-menu');
      if (settingsMenu) settingsMenu.removeAttribute('open');
    });
  }

  if (notificationCount && notificationValues && markNotificationsRead) {
    var currentProducts = notificationValues.dataset.products || '0';
    var currentOrders = notificationValues.dataset.orders || '0';
    var previousProducts = null;
    var previousOrders = null;
    var unreadCount = 0;

    try {
      previousProducts = localStorage.getItem('hjm-admin-read-products');
      previousOrders = localStorage.getItem('hjm-admin-read-orders');
    } catch (error) {
      console.warn('خواندن وضعیت اعلان‌ها از این مرورگر ممکن نیست.', error);
    }

    if (currentProducts !== previousProducts) unreadCount += Number(currentProducts);
    if (currentOrders !== previousOrders) unreadCount += Number(currentOrders);
    notificationCount.textContent = new Intl.NumberFormat('fa-IR').format(unreadCount);
    notificationCount.hidden = unreadCount === 0;

    markNotificationsRead.addEventListener('click', function () {
      try {
        localStorage.setItem('hjm-admin-read-products', currentProducts);
        localStorage.setItem('hjm-admin-read-orders', currentOrders);
      } catch (error) {
        console.warn('ذخیره‌سازی وضعیت اعلان‌ها در این مرورگر در دسترس نیست.', error);
      }
      notificationCount.hidden = true;
      if (notificationMenu) notificationMenu.removeAttribute('open');
    });
  }

  var dataElement = document.getElementById('dashboard-chart-data');
  var chart = dataElement ? JSON.parse(dataElement.textContent) : [];
  var labels = document.querySelector('.dashboard-chart-labels');
  var emptyMessage = document.querySelector('.dashboard-chart-empty');
  var numberFormat = new Intl.NumberFormat('fa-IR');
  var svgNamespace = 'http://www.w3.org/2000/svg';
  var chartStart = 40;
  var chartEnd = 880;
  var chartTop = 30;
  var chartBottom = 222;

  function renderChart() {
    if (!labels || !emptyMessage) return;
    var hasActivity = chart.some(function (item) {
      return item.orders || item.revenue;
    });
    emptyMessage.hidden = hasActivity;
    labels.replaceChildren();

    ['orders', 'revenue'].forEach(function (series) {
      var values = chart.map(function (item) {
        return Number(item[series]) || 0;
      });
      var maximum = Math.max.apply(Math, values.concat([1]));
      var points = values.map(function (value, index) {
        var x = chart.length === 1
          ? (chartStart + chartEnd) / 2
          : chartStart + index * (chartEnd - chartStart) / (chart.length - 1);
        var y = chartBottom - (value / maximum) * (chartBottom - chartTop);
        return { x: x, y: y, value: value, label: chart[index].label };
      });
      var line = document.querySelector('.dashboard-chart-line.' + series);
      var pointGroup = document.querySelector('.dashboard-chart-points.' + series);
      if (line) {
        line.setAttribute(
          'points',
          points.map(function (point) {
            return point.x + ',' + point.y;
          }).join(' ')
        );
      }
      if (pointGroup) {
        pointGroup.replaceChildren();
        points.forEach(function (point) {
          var circle = document.createElementNS(svgNamespace, 'circle');
          circle.setAttribute('cx', point.x);
          circle.setAttribute('cy', point.y);
          circle.setAttribute('r', '4');
          var title = document.createElementNS(svgNamespace, 'title');
          title.textContent = point.label + ': ' + numberFormat.format(point.value)
            + (series === 'revenue' ? ' تومان' : ' سفارش');
          circle.append(title);
          pointGroup.append(circle);
        });
      }
    });

    chart.forEach(function (item) {
      var label = document.createElement('span');
      label.textContent = item.label;
      labels.append(label);
    });
  }

  renderChart();
})();
