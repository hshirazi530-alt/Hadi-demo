(function () {
  'use strict';

  var body = document.body;
  var sidebar = document.getElementById('admin-sidebar');
  var openButton = document.querySelector('[data-sidebar-open]');
  var closeButton = document.querySelector('[data-sidebar-close]');
  var collapseButton = document.querySelector('[data-sidebar-collapse]');
  var sidebarGroups = Array.prototype.slice.call(
    document.querySelectorAll('[data-sidebar-group]')
  );

  function setSidebarOpen(isOpen) {
    var wasOpen = body.classList.contains('admin-sidebar-open');
    body.classList.toggle('admin-sidebar-open', isOpen);
    if (openButton) openButton.setAttribute('aria-expanded', String(isOpen));
    if (isOpen && sidebar) {
      var firstLink = sidebar.querySelector('a');
      if (firstLink) firstLink.focus();
    } else if (wasOpen && openButton) {
      openButton.focus();
    }
  }

  if (openButton) {
    openButton.addEventListener('click', function () {
      setSidebarOpen(true);
    });
  }

  if (closeButton) {
    closeButton.addEventListener('click', function () {
      setSidebarOpen(false);
    });
  }

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      setSidebarOpen(false);
      sidebarGroups.forEach(function (group) {
        group.removeAttribute('open');
      });
    }
  });

  function placeCollapsedSubmenu(group) {
    if (!group.open || !body.classList.contains('admin-sidebar-collapsed')) return;
    var summary = group.querySelector(':scope > summary');
    var submenu = group.querySelector(':scope > .admin-subnav');
    if (!summary || !submenu) return;
    submenu.style.top = Math.max(
      8,
      Math.min(summary.getBoundingClientRect().top, window.innerHeight - submenu.offsetHeight - 8)
    ) + 'px';
  }

  sidebarGroups.forEach(function (group) {
    var summary = group.querySelector(':scope > summary');
    if (!summary) return;
    summary.addEventListener('click', function () {
      window.setTimeout(function () {
        placeCollapsedSubmenu(group);
      }, 0);
    });
    group.addEventListener('toggle', function () {
      placeCollapsedSubmenu(group);
    });
  });

  document.addEventListener('click', function (event) {
    sidebarGroups.forEach(function (group) {
      if (!group.contains(event.target)) group.removeAttribute('open');
    });
  });

  window.addEventListener('resize', function () {
    sidebarGroups.forEach(placeCollapsedSubmenu);
  });

  if (sidebar) {
    sidebar.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        setSidebarOpen(false);
      });
    });
  }

  if (collapseButton) {
    var isCollapsed = false;
    try {
      isCollapsed = localStorage.getItem('hjm-admin-sidebar-collapsed') === 'true';
    } catch (error) {
      console.warn('خواندن وضعیت منوی کناری از این مرورگر ممکن نیست.', error);
    }
    body.classList.toggle('admin-sidebar-collapsed', isCollapsed);
    collapseButton.setAttribute('aria-pressed', String(isCollapsed));
    collapseButton.setAttribute(
      'aria-label',
      isCollapsed ? 'بازکردن نوار کناری' : 'جمع‌کردن نوار کناری'
    );
    collapseButton.setAttribute(
      'title',
      isCollapsed ? 'بازکردن نوار کناری' : 'جمع‌کردن نوار کناری'
    );
    collapseButton.addEventListener('click', function () {
      var collapsed = body.classList.toggle('admin-sidebar-collapsed');
      isCollapsed = collapsed;
      body.classList.toggle('sidebar-mini', collapsed);
      collapseButton.setAttribute('aria-label', collapsed ? 'بازکردن نوار کناری' : 'جمع‌کردن نوار کناری');
      collapseButton.setAttribute('title', collapsed ? 'بازکردن نوار کناری' : 'جمع‌کردن نوار کناری');
      collapseButton.setAttribute('aria-pressed', String(collapsed));
      try {
        localStorage.setItem('hjm-admin-sidebar-collapsed', String(collapsed));
      } catch (error) {
        console.warn('ذخیره‌سازی وضعیت منوی کناری در این مرورگر ممکن نیست.', error);
      }
      sidebarGroups.forEach(placeCollapsedSubmenu);
    });
  }

  document.querySelectorAll('[data-dismiss-flash]').forEach(function (button) {
    button.addEventListener('click', function () {
      var flash = button.closest('.admin-flash');
      if (flash) flash.remove();
    });
  });

  var mobileSearch = document.querySelector('.admin-search');
  if (mobileSearch) {
    mobileSearch.addEventListener('click', function () {
      if (window.matchMedia('(max-width: 640px)').matches && !mobileSearch.classList.contains('is-open')) {
        mobileSearch.classList.add('is-open');
        var searchInput = mobileSearch.querySelector('input');
        if (searchInput) searchInput.focus();
      }
    });
    document.addEventListener('click', function (event) {
      if (!mobileSearch.contains(event.target)) mobileSearch.classList.remove('is-open');
    });
  }

  document.querySelectorAll('[data-fa-number]').forEach(function (element) {
    var numericValue = Number(element.dataset.faNumber);
    if (Number.isFinite(numericValue)) {
      element.textContent = new Intl.NumberFormat('fa-IR', {
        maximumFractionDigits: 0
      }).format(numericValue);
    }
  });

  var selectAll = document.querySelector('[data-select-all]');
  var productSelections = Array.prototype.slice.call(
    document.querySelectorAll('[data-product-select]')
  );
  var bulkBar = document.querySelector('[data-bulk-bar]');
  var selectedCount = document.querySelector('[data-selected-count]');
  var selectedInputs = document.querySelector('[data-selected-inputs]');
  var bulkForm = document.getElementById('bulk-delete-form');

  function syncSelections() {
    var checked = productSelections.filter(function (checkbox) {
      return checkbox.checked;
    });

    if (bulkBar) bulkBar.classList.toggle('is-visible', checked.length > 0);
    if (selectedCount) {
      selectedCount.textContent = new Intl.NumberFormat('fa-IR').format(checked.length);
    }
    if (selectAll) {
      selectAll.checked = productSelections.length > 0 && checked.length === productSelections.length;
      selectAll.indeterminate = checked.length > 0 && checked.length < productSelections.length;
    }
    if (selectedInputs) {
      selectedInputs.replaceChildren();
      checked.forEach(function (checkbox) {
        var hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'selected_products';
        hidden.value = checkbox.value;
        selectedInputs.appendChild(hidden);
      });
    }
  }

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      productSelections.forEach(function (checkbox) {
        checkbox.checked = selectAll.checked;
      });
      syncSelections();
    });
  }

  productSelections.forEach(function (checkbox) {
    checkbox.addEventListener('change', syncSelections);
  });

  if (bulkForm) {
    bulkForm.addEventListener('submit', function (event) {
      if (!productSelections.some(function (checkbox) { return checkbox.checked; })) {
        event.preventDefault();
      }
    });
  }

  var confirmDialog = document.querySelector('[data-confirm-dialog]');
  var confirmDescription = document.getElementById('confirm-description');
  var confirmButton = document.querySelector('[data-confirm-submit]');
  var cancelButton = document.querySelector('[data-confirm-cancel]');
  var pendingForm = null;
  var pendingSubmitter = null;

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form.matches('[data-confirm-delete]')) return;
    if (form.dataset.confirmed === 'true') {
      delete form.dataset.confirmed;
      return;
    }

    event.preventDefault();
    pendingForm = form;
    pendingSubmitter = event.submitter || null;
    if (confirmDescription) {
      confirmDescription.textContent =
        (pendingSubmitter && pendingSubmitter.dataset.confirmMessage) ||
        form.dataset.confirmMessage ||
        'این عملیات قابل بازگشت نیست.';
    }

    if (confirmDialog && typeof confirmDialog.showModal === 'function') {
      confirmDialog.showModal();
    } else if (window.confirm(confirmDescription ? confirmDescription.textContent : 'تأیید حذف؟')) {
      submitPendingForm();
    }
  });

  function submitPendingForm() {
    if (!pendingForm) return;
    var form = pendingForm;
    var submitter = pendingSubmitter;
    pendingForm = null;
    pendingSubmitter = null;
    form.dataset.confirmed = 'true';
    if (typeof form.requestSubmit === 'function') {
      if (submitter) form.requestSubmit(submitter);
      else form.requestSubmit();
    } else {
      HTMLFormElement.prototype.submit.call(form);
    }
  }

  if (confirmButton) {
    confirmButton.addEventListener('click', function () {
      if (confirmDialog && confirmDialog.open) confirmDialog.close();
      submitPendingForm();
    });
  }

  if (cancelButton) {
    cancelButton.addEventListener('click', function () {
      if (confirmDialog && confirmDialog.open) confirmDialog.close();
      pendingForm = null;
      pendingSubmitter = null;
    });
  }

  if (confirmDialog) {
    confirmDialog.addEventListener('click', function (event) {
      if (event.target === confirmDialog) confirmDialog.close();
    });
  }
})();
