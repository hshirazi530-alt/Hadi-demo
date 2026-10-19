(function () {
  'use strict';

  var form = document.getElementById('product-create-form');
  var input = document.getElementById('product-images-input');
  var list = document.getElementById('product-image-list');
  var errors = document.getElementById('product-image-errors');
  var status = document.getElementById('product-upload-status');
  if (!form || !input || !list || !errors || !status) return;
  var sourceChecks = Array.prototype.slice.call(
    document.querySelectorAll('[data-source-check]')
  );
  var sourceStatus = document.getElementById('product-source-status');

  var maxCount = Number(input.dataset.maxCount);
  var maxFileBytes = Number(input.dataset.maxFileBytes);
  var maxTotalBytes = Number(input.dataset.maxTotalBytes);
  var supportedExtensions = /\.(jpe?g|png|webp)$/i;
  var files = [];
  var nextFileId = 0;
  var localCoverId = null;

  function setStatus(message, isError) {
    status.textContent = message;
    status.classList.toggle('is-error', Boolean(isError));
  }

  function selectedSourceChecks() {
    return sourceChecks.filter(function (checkbox) {
      return checkbox.checked;
    });
  }

  function validLocalFiles() {
    return files.filter(function (entry) {
      return !entry.error;
    });
  }

  function chooseFirstLocalCover() {
    var firstValid = files.find(function (entry) {
      return !entry.error;
    });
    localCoverId = firstValid ? firstValid.id : null;
  }

  function updateSourceControls() {
    var selected = selectedSourceChecks();
    var firstSelectedRadio = null;

    sourceChecks.forEach(function (checkbox) {
      var radio = checkbox.closest('.product-source__item').querySelector('[data-source-cover]');
      radio.disabled = !checkbox.checked;
      radio.required = false;
      if (!checkbox.checked) radio.checked = false;
      if (checkbox.checked && !firstSelectedRadio) firstSelectedRadio = radio;
    });

    if (firstSelectedRadio) firstSelectedRadio.required = true;
    if (sourceStatus) {
      sourceStatus.textContent = selected.length
        ? selected.length + ' تصویر از پوشه انتخاب شده است؛ تصویر اصلی را مشخص کنید.'
        : 'تصویری از پوشه انتخاب نشده است.';
    }
  }

  function sourceSelectionSize() {
    return selectedSourceChecks().reduce(function (sum, checkbox) {
      return sum + Number(checkbox.dataset.size || 0);
    }, 0);
  }

  function releasePreviews() {
    files.forEach(function (entry) {
      if (entry.previewUrl) URL.revokeObjectURL(entry.previewUrl);
    });
  }

  function validateSelection(selection) {
    var sourceCount = selectedSourceChecks().length;
    var totalBytes = sourceSelectionSize() + selection.reduce(function (sum, file) {
      return sum + file.size;
    }, 0);

    return selection.map(function (file, index) {
      var fileTypeSupported = !file.type ||
        ['image/jpeg', 'image/png', 'image/webp'].indexOf(file.type.toLowerCase()) !== -1;
      var error = '';

      if (!supportedExtensions.test(file.name) || !fileTypeSupported) {
        error = 'قالب پشتیبانی‌نشده؛ فقط JPEG، PNG و WebP مجاز است.';
      } else if (file.size <= 0) {
        error = 'فایل خالی است.';
      } else if (file.size > maxFileBytes) {
        error = 'حجم این فایل بیشتر از حد مجاز است.';
      } else if (totalBytes > maxTotalBytes) {
        error = 'حجم مجموع فایل‌های انتخاب‌شده از حد مجاز بیشتر است.';
      } else if (index + sourceCount >= maxCount) {
        error = 'تعداد تصاویر از حد مجاز بیشتر است.';
      }

      return {
        id: nextFileId++,
        file: file,
        error: error,
        previewUrl: fileTypeSupported && supportedExtensions.test(file.name) && file.size
          ? URL.createObjectURL(file)
          : ''
      };
    });
  }

  function syncInputFiles() {
    if (typeof DataTransfer !== 'function') return false;

    var transfer = new DataTransfer();
    files.forEach(function (entry) {
      if (!entry.error) transfer.items.add(entry.file);
    });
    input.files = transfer.files;
    return true;
  }

  function renderFiles() {
    list.replaceChildren();
    var validFileIndex = 0;
    files.forEach(function (entry, index) {
      var item = document.createElement('div');
      item.className = 'product-upload__item' + (entry.error ? ' is-invalid' : '');

      if (entry.previewUrl) {
        var preview = document.createElement('img');
        preview.className = 'product-upload__preview';
        preview.src = entry.previewUrl;
        preview.alt = 'پیش‌نمایش ' + entry.file.name;
        item.appendChild(preview);
      }

      var fileInfo = document.createElement('div');
      fileInfo.className = 'product-upload__file';
      fileInfo.textContent = entry.file.name;
      var fileStatus = document.createElement('span');
      fileStatus.className = 'product-upload__file-status';
      fileStatus.textContent = entry.error || 'آمادهٔ ارسال و تبدیل به WebP';
      fileInfo.appendChild(fileStatus);
      item.appendChild(fileInfo);

      if (!entry.error) {
        var coverLabel = document.createElement('label');
        coverLabel.className = 'product-upload__cover-choice';
        var coverInput = document.createElement('input');
        coverInput.type = 'radio';
        coverInput.name = 'local_cover_index';
        coverInput.value = String(validFileIndex);
        coverInput.required = validFileIndex === 0;
        coverInput.checked = entry.id === localCoverId;
        coverInput.addEventListener('change', function () {
          localCoverId = entry.id;
          renderFiles();
        });
        coverLabel.appendChild(coverInput);
        coverLabel.appendChild(document.createTextNode('تصویر اصلی'));
        fileInfo.appendChild(coverLabel);
        validFileIndex += 1;
      }

      var remove = document.createElement('button');
      remove.className = 'product-upload__remove';
      remove.type = 'button';
      remove.textContent = 'حذف';
      remove.setAttribute('aria-label', 'حذف تصویر ' + entry.file.name);
      remove.addEventListener('click', function () {
        if (entry.previewUrl) URL.revokeObjectURL(entry.previewUrl);
        files.splice(index, 1);
        if (entry.id === localCoverId) chooseFirstLocalCover();
        if (!syncInputFiles()) {
          input.value = '';
          files.forEach(function (current) {
            if (current.previewUrl) URL.revokeObjectURL(current.previewUrl);
          });
          files = [];
          localCoverId = null;
          setStatus('مرورگر اجازهٔ ویرایش جداگانهٔ فایل‌های انتخابی را نمی‌دهد؛ لطفاً تصاویر باقی‌مانده را دوباره انتخاب کنید.', true);
        } else {
          setStatus(files.length ? files.length + ' تصویر آماده است.' : 'تصویری انتخاب نشده است.', false);
        }
        renderFiles();
      });
      item.appendChild(remove);
      list.appendChild(item);
    });

    errors.replaceChildren();
    files.forEach(function (entry) {
      if (!entry.error) return;
      var error = document.createElement('li');
      error.textContent = entry.file.name + ': ' + entry.error;
      errors.appendChild(error);
    });
  }

  input.addEventListener('change', function () {
    releasePreviews();
    files = validateSelection(Array.prototype.slice.call(input.files || []));
    chooseFirstLocalCover();
    syncInputFiles();
    renderFiles();

    var invalidCount = files.filter(function (entry) {
      return Boolean(entry.error);
    }).length;
    if (invalidCount) {
      setStatus(invalidCount + ' تصویر نیاز به اصلاح یا حذف دارد.', true);
    } else if (files.length) {
      setStatus(files.length + ' تصویر برای پردازش آماده است.', false);
    } else {
      setStatus('تصویری انتخاب نشده است.', false);
    }
  });

  sourceChecks.forEach(function (checkbox) {
    checkbox.addEventListener('change', function () {
      var selected = selectedSourceChecks();
      var local = validLocalFiles();
      var combinedCount = selected.length + local.length;
      var combinedSize = sourceSelectionSize() + local.reduce(function (sum, entry) {
        return sum + entry.file.size;
      }, 0);

      if (combinedCount > maxCount || combinedSize > maxTotalBytes) {
        checkbox.checked = false;
        updateSourceControls();
        setStatus(
          combinedCount > maxCount
            ? 'تعداد مجموع تصاویر از حد مجاز بیشتر است.'
            : 'حجم مجموع تصاویر از حد مجاز بیشتر است.',
          true
        );
        return;
      }

      updateSourceControls();
      setStatus(
        local.length + selectedSourceChecks().length + ' تصویر برای محصول انتخاب شده است.',
        false
      );
    });
  });
  updateSourceControls();

  form.addEventListener('submit', function (event) {
    var invalidCount = files.filter(function (entry) {
      return Boolean(entry.error);
    }).length;
    var validCount = files.filter(function (entry) {
      return !entry.error;
    }).length + selectedSourceChecks().length;

    if (invalidCount || !validCount) {
      event.preventDefault();
      setStatus(
        invalidCount
          ? 'ابتدا خطاهای تصاویر را برطرف کنید.'
          : 'برای محصول دست‌کم یک تصویر انتخاب کنید.',
        true
      );
      return;
    }

    var sourceSelection = selectedSourceChecks();
    if (sourceSelection.length && validLocalFiles().length) {
      event.preventDefault();
      setStatus('برای جلوگیری از ابهام، تصاویر را فقط از یک روش انتخاب کنید.', true);
      return;
    }

    if (
      sourceSelection.length &&
      !sourceSelection.some(function (checkbox) {
        return checkbox.closest('.product-source__item').querySelector('[data-source-cover]').checked;
      })
    ) {
      event.preventDefault();
      setStatus('تصویر اصلی را از میان تصاویر انتخاب‌شده در پوشه مشخص کنید.', true);
      return;
    }

    if (validLocalFiles().length && localCoverId === null) {
      event.preventDefault();
      setStatus('تصویر اصلی را از میان تصاویر بارگذاری‌شده مشخص کنید.', true);
      return;
    }

    if (!form.reportValidity()) {
      event.preventDefault();
      return;
    }

    setStatus('تصاویر در حال ارسال، بررسی و تبدیل امن به WebP هستند…', false);
    form.querySelectorAll('button[type="submit"]').forEach(function (button) {
      button.disabled = true;
    });
  });

  window.addEventListener('pagehide', releasePreviews);
})();
