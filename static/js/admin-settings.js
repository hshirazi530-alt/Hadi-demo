(function () {
  'use strict';

  var form = document.querySelector('[data-settings-form]');
  if (!form) return;

  var storageKey = form.dataset.storageKey;
  var feedback = form.querySelector('[data-settings-feedback]');
  var inputs = Array.prototype.slice.call(form.querySelectorAll('[data-setting]'));
  var navigation = document.querySelector('[data-settings-nav]');
  var defaultValues = {};
  var savedValues = {};

  function showFeedback(message, state) {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.dataset.state = state || '';
  }

  function readValue(input) {
    if (input.type === 'checkbox') return input.checked;
    if (input.type === 'radio') {
      var selected = form.querySelector(
        '[data-setting="' + input.dataset.setting + '"]:checked'
      );
      return selected ? selected.value : null;
    }
    return input.value;
  }

  function applyValue(input, value) {
    if (input.type === 'checkbox') {
      input.checked = Boolean(value);
    } else if (input.type === 'radio') {
      input.checked = input.value === value;
    } else if (value !== null && value !== undefined) {
      input.value = String(value);
    }
  }

  function collectValues() {
    var values = {};
    inputs.forEach(function (input) {
      if (input.type === 'radio' && !input.checked) return;
      values[input.dataset.setting] = readValue(input);
    });
    return values;
  }

  function restoreValues(values) {
    inputs.forEach(function (input) {
      if (!Object.prototype.hasOwnProperty.call(values, input.dataset.setting)) return;
      applyValue(input, values[input.dataset.setting]);
    });
    updateAppearance();
    clearErrors();
  }

  function clearErrors() {
    form.querySelectorAll('[data-error-for]').forEach(function (message) {
      message.textContent = '';
    });
    inputs.forEach(function (input) {
      input.removeAttribute('aria-invalid');
    });
  }

  function setError(input, message) {
    var error = form.querySelector(
      '[data-error-for="' + input.dataset.setting + '"]'
    );
    input.setAttribute('aria-invalid', 'true');
    if (error) error.textContent = message;
  }

  function validate() {
    clearErrors();
    var firstInvalid = null;

    inputs.forEach(function (input) {
      if (input.type === 'radio' && !input.checked) return;
      var value = input.value.trim();
      var message = '';

      if (input.required && !value) {
        message = 'تکمیل این فیلد الزامی است.';
      } else if (value && input.type === 'email'
        && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        message = 'یک نشانی ایمیل معتبر وارد کنید.';
      } else if (value && input.type === 'number') {
        var number = Number(value);
        if (!Number.isFinite(number)) {
          message = 'یک مقدار عددی معتبر وارد کنید.';
        } else if (input.dataset.min && number < Number(input.dataset.min)) {
          message = 'مقدار نباید کمتر از ' + input.dataset.min + ' باشد.';
        } else if (input.dataset.max && number > Number(input.dataset.max)) {
          message = 'مقدار نباید بیشتر از ' + input.dataset.max + ' باشد.';
        }
      }

      if (message) {
        setError(input, message);
        if (!firstInvalid) firstInvalid = input;
      }
    });

    var couponMinimum = form.querySelector('[data-setting="coupon_min"]');
    var couponMaximum = form.querySelector('[data-setting="coupon_max"]');
    if (couponMinimum && couponMaximum
      && Number(couponMinimum.value) > Number(couponMaximum.value)) {
      setError(couponMaximum, 'حداکثر تخفیف باید برابر یا بیشتر از حداقل باشد.');
      if (!firstInvalid) firstInvalid = couponMaximum;
    }

    if (firstInvalid) {
      firstInvalid.focus();
      showFeedback('لطفاً خطاهای مشخص‌شده را بررسی کنید.', 'error');
      return false;
    }
    return true;
  }

  function updateAppearance() {
    var selectedAppearance = form.querySelector(
      '[data-setting="appearance"]:checked'
    );
    var appearance = selectedAppearance ? selectedAppearance.value : 'forest';
    document.body.dataset.settingsAppearance = appearance;
  }

  var hasUnsavedChanges = false;

  function markAsChanged() {
    hasUnsavedChanges = true;
    showFeedback('تغییرات ذخیره‌نشده دارید.', '');
  }

  inputs.forEach(function (input) {
    if (input.type === 'checkbox') {
      defaultValues[input.dataset.setting] = input.dataset.defaultChecked === 'true';
    } else if (input.type === 'radio') {
      if (input.dataset.defaultChecked === 'true') {
        defaultValues[input.dataset.setting] = input.value;
      }
    } else {
      defaultValues[input.dataset.setting] = input.dataset.defaultValue || input.value;
    }

    input.addEventListener('input', function () {
      var error = form.querySelector(
        '[data-error-for="' + input.dataset.setting + '"]'
      );
      input.removeAttribute('aria-invalid');
      if (error) error.textContent = '';
      markAsChanged();
      if (input.dataset.setting === 'appearance') updateAppearance();
    });
    input.addEventListener('change', function () {
      if (input.dataset.setting === 'appearance') updateAppearance();
      markAsChanged();
    });
    input.addEventListener('blur', function () {
      if (input.required && !input.value.trim()) {
        setError(input, 'تکمیل این فیلد الزامی است.');
      } else if (input.type === 'email' && input.value.trim()
        && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value.trim())) {
        setError(input, 'یک نشانی ایمیل معتبر وارد کنید.');
      } else if (input.type === 'number' && input.value < 0) {
         setError(input, 'مقدار نمی‌تواند منفی باشد.');
      }
    });
  });

  window.addEventListener('beforeunload', function (event) {
    if (hasUnsavedChanges) {
      event.preventDefault();
      event.returnValue = '';
    }
  });

  try {
    var stored = localStorage.getItem(storageKey);
    if (stored) {
      var parsed = JSON.parse(stored);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Saved settings have an invalid format.');
      }
      restoreValues(parsed);
      savedValues = collectValues();
      showFeedback('تنظیمات ذخیره‌شده از این مرورگر بارگذاری شد.', 'success');
    } else {
      restoreValues(defaultValues);
      savedValues = collectValues();
      showFeedback('هنوز تنظیمی ذخیره نشده است؛ مقادیر پیش‌فرض نمایش داده می‌شوند.', '');
    }
  } catch (error) {
    restoreValues(defaultValues);
    savedValues = collectValues();
    showFeedback('خواندن تنظیمات ذخیره‌شده ممکن نشد؛ امکان ذخیرهٔ جدید را بررسی کنید.', 'error');
    console.error('Could not load local store settings.', error);
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!validate()) return;

    showFeedback('در حال ذخیره‌سازی...', '');
    
    // شبیه‌سازی تاخیر شبکه برای تجربه کاربری بهتر
    setTimeout(function() {
        var values = collectValues();
        try {
          localStorage.setItem(storageKey, JSON.stringify(values));
          savedValues = values;
          hasUnsavedChanges = false;
          showFeedback('تغییرات با موفقیت در مرورگر فعلی ذخیره شد.', 'success');
        } catch (error) {
          showFeedback('ذخیره‌سازی در این مرورگر ممکن نشد؛ فضای ذخیره‌سازی را بررسی کنید.', 'error');
          console.error('Could not save local store settings.', error);
        }
    }, 600);
  });

  var resetButton = form.querySelector('[data-settings-reset]');
  if (resetButton) {
    resetButton.addEventListener('click', function () {
      if (hasUnsavedChanges && !confirm('آیا از لغو تغییرات ذخیره‌نشده اطمینان دارید؟')) {
        return;
      }
      restoreValues(savedValues);
      hasUnsavedChanges = false;
      showFeedback('تغییرات ذخیره‌نشده لغو شد.', '');
    });
  }

  if (navigation) {
    var sectionLinks = Array.prototype.slice.call(
      navigation.querySelectorAll('a[href^="#"]')
    );
    sectionLinks.forEach(function (link) {
      link.addEventListener('click', function () {
        sectionLinks.forEach(function (item) {
          item.removeAttribute('aria-current');
        });
        link.setAttribute('aria-current', 'location');
      });
    });

    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        var visible = entries
          .filter(function (entry) {
            return entry.isIntersecting;
          })
          .sort(function (first, second) {
            return second.intersectionRatio - first.intersectionRatio;
          })[0];
        if (!visible) return;
        sectionLinks.forEach(function (link) {
          if (link.hash === '#' + visible.target.id) {
            link.setAttribute('aria-current', 'location');
          } else {
            link.removeAttribute('aria-current');
          }
        });
      }, { rootMargin: '-15% 0px -70% 0px', threshold: [0, 0.2, 0.5] });

      sectionLinks.forEach(function (link) {
        var section = document.querySelector(link.hash);
        if (section) observer.observe(section);
      });
    }
  }

  updateAppearance();
})();
