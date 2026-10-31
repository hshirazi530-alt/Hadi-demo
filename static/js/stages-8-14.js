(function () {
  'use strict';
  var digits = '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩';
  function ascii(value) {
    return value.replace(/[۰-۹٠-٩]/g, function (char) { return String(digits.indexOf(char) % 10); });
  }
  document.querySelectorAll('[data-iran-mobile-suffix]').forEach(function (input) {
    input.addEventListener('input', function () {
      var raw = ascii(input.value).replace(/[\s()\-]/g, '');
      var suffix = raw;
      if (/^09[0-9]{9}$/.test(raw)) suffix = raw.slice(2);
      else if (/^(?:\+98|0098|98)9[0-9]{9}$/.test(raw)) suffix = raw.slice(-9);
      input.value = suffix;
      input.setCustomValidity('');
    });
    input.addEventListener('invalid', function () {
      input.setCustomValidity('پس از +989 دقیقاً ۹ رقم شمارهٔ همراه را وارد کنید.');
    });
  });

  var helper = document.querySelector('[data-shopping-assistant]');
  if (!helper) return;
  var mobile = helper.querySelector('[data-helper-mobile]');
  if (mobile) {
    var mobileError = helper.querySelector('#hm-chat-mobile-error');
    function validateMobile(show) {
      var invalid = mobile.value.length !== 9;
      mobile.setAttribute('aria-invalid', String(show && invalid));
      mobileError.hidden = !show || !invalid;
    }
    mobile.addEventListener('input', function () {
      mobile.value = ascii(mobile.value).replace(/[^0-9]/g, '').slice(0, 9);
      if (mobile.getAttribute('aria-invalid') === 'true') validateMobile(true);
    });
    mobile.addEventListener('blur', function () { validateMobile(true); });
  }
  var panel = helper.querySelector('#hm-helper-panel');
  var toggle = helper.querySelector('[data-helper-toggle]');
  var close = helper.querySelector('[data-helper-close]');
  function setOpen(open, restoreFocus) {
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    if (open) close.focus({ preventScroll: true });
    else if (restoreFocus) toggle.focus({ preventScroll: true });
  }
  toggle.addEventListener('click', function () { setOpen(panel.hidden, false); });
  close.addEventListener('click', function () { setOpen(false, true); });
  helper.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !panel.hidden) { setOpen(false, true); event.preventDefault(); }
  });
  helper.querySelectorAll('[data-helper-choice]').forEach(function (button) {
    button.addEventListener('click', function () {
      var key = button.getAttribute('data-helper-choice');
      helper.querySelectorAll('[data-helper-answer]').forEach(function (answer) {
        answer.hidden = answer.getAttribute('data-helper-answer') !== key;
      });
    });
  });
}());
