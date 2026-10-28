(function () {
  'use strict';
  var cartStatusTimer;

  function getCookie(name) {
    var prefix = name + '=';
    var cookies = document.cookie ? document.cookie.split(';') : [];

    for (var i = 0; i < cookies.length; i += 1) {
      var cookie = cookies[i].trim();
      if (cookie.indexOf(prefix) === 0) {
        return decodeURIComponent(cookie.slice(prefix.length));
      }
    }

    return '';
  }

  function showCartMessage(message, isError) {
    var status = document.getElementById('store-cart-status');
    if (!status) return;

    status.textContent = message;
    status.classList.toggle('is-error', Boolean(isError));
    status.classList.add('is-visible');
    window.clearTimeout(cartStatusTimer);
    cartStatusTimer = window.setTimeout(function () {
      status.classList.remove('is-visible');
    }, 3500);
  }

  function updateCartBadges(count) {
    document.querySelectorAll('.cart-items-count').forEach(function (badge) {
      badge.textContent = count;
    });
  }

  function postCartAction(url, values) {
    return fetch(url, {
      method: 'POST',
      body: new URLSearchParams(values),
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      }
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok || !data.data) {
          throw new Error(data.message || 'به‌روزرسانی سبد خرید انجام نشد.');
        }
        return data;
      });
    });
  }

  /* ---------- Warranty selector live price update (Feature 7) ---------- */
  function formatToman(amount) {
    var value = Number(amount) || 0;
    return value.toLocaleString('fa-IR');
  }

  function initWarrantySelector() {
    var wrap = document.querySelector('[data-warranty-wrap]');
    if (!wrap) return;

    var card = wrap.closest('.product-cart-wrap');
    if (!card) return;

    var basePrice = Number(card.dataset.productPrice) || 0;
    var currentPriceEl = document.querySelector('.hm-price-card__current');

    function updatePrice() {
      var selected = wrap.querySelector('[data-warranty-option]:checked');
      var warrantyPrice = selected ? (Number(selected.dataset.warrantyPrice) || 0) : 0;
      var total = basePrice + warrantyPrice;

      wrap.querySelectorAll('.hm-warranty__option').forEach(function (label) {
        var input = label.querySelector('[data-warranty-option]');
        label.classList.toggle('is-active', input === selected);
      });

      if (currentPriceEl) {
        var small = currentPriceEl.querySelector('small');
        currentPriceEl.childNodes.forEach(function (node) {
          if (node.nodeType === 3 && node.textContent.trim()) {
            node.textContent = ' ' + formatToman(total) + ' ';
          }
        });
        if (small) {
          small.textContent = 'تومان';
        }
      }
    }

    wrap.querySelectorAll('[data-warranty-option]').forEach(function (input) {
      input.addEventListener('change', updatePrice);
    });
    updatePrice();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWarrantySelector);
  } else {
    initWarrantySelector();
  }
  /* ---------- End warranty selector ---------- */

  var imageZoomDialog = document.querySelector('[data-image-zoom-dialog]');
  if (imageZoomDialog) {
    var zoomedImage = imageZoomDialog.querySelector('[data-image-zoom-view]');
    var zoomCaption = imageZoomDialog.querySelector('[data-image-zoom-caption]');
    var closeZoomButton = imageZoomDialog.querySelector('[data-image-zoom-close]');

    function openImageZoom(image, fallbackAlt, preferredSource) {
      var source = preferredSource || image.currentSrc || image.src;
      if (!source) return;

      zoomedImage.src = source;
      zoomedImage.alt = fallbackAlt || image.alt || 'نمای بزرگ محصول';
      zoomCaption.textContent = zoomedImage.alt;
      imageZoomDialog.showModal();
    }

    document.addEventListener('click', function (event) {
      var image = event.target.closest('img');
      var gallery = event.target.closest('.store-product-gallery__main');
      var surface = event.target.closest(
        '.store-product-card__image, .beauty-product-card__image, .store-cart-item__image, ' +
        '.product-thumbnail, ' +
        '.comparison-product, .product-img-action-wrap .product-img, ' +
        '.detail-gallery .product-image-slider'
      );

      if (!gallery && !surface) return;
      if (event.target.closest('button')) return;
      if (event.detail === 0 && event.target === surface && surface.matches('a')) return;

      var productCard = event.target.closest('[data-product-title]');
      if (gallery && gallery.dataset.spinDragged === 'true') {
        delete gallery.dataset.spinDragged;
        return;
      }

      var imageToShow = image ||
        (surface && surface.querySelector('img')) ||
        (gallery && gallery.querySelector('[data-gallery-main]'));
      if (!imageToShow) return;

      var productLink = imageToShow.closest('a');
      if (productLink) event.preventDefault();
      var fallbackAlt = productCard ? productCard.dataset.productTitle : '';
      if (gallery) {
        var productInfo = document.querySelector('.store-product-info[data-product-title]');
        if (productInfo) fallbackAlt = productInfo.dataset.productTitle;
      }
      openImageZoom(
        imageToShow,
        fallbackAlt,
        gallery && imageToShow.dataset.galleryOriginalSrc
      );
    });

    closeZoomButton.addEventListener('click', function () {
      imageZoomDialog.close();
    });

    imageZoomDialog.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        imageZoomDialog.close();
      }
    });

    imageZoomDialog.addEventListener('click', function (event) {
      if (event.target === imageZoomDialog) imageZoomDialog.close();
    });
  }

  document.addEventListener('click', function (event) {
    var cartAction = event.target.closest('[data-cart-action]');
    if (!cartAction) return;

    var cartPage = cartAction.closest('.store-cart-page');
    var productId = cartAction.dataset.product;
    var item = cartAction.closest('.store-cart-item');
    if (!cartPage || !productId || !item) return;

    var values = { id: productId };
    if (cartAction.dataset.cartAction === 'update') {
      var quantity = item.querySelector('input[type="number"]');
      values.qty = quantity ? quantity.value : '';
    }

    var endpoint = cartAction.dataset.cartAction === 'remove'
      ? cartPage.dataset.deleteUrl
      : cartPage.dataset.updateUrl;
    var originalText = cartAction.textContent;
    cartAction.disabled = true;
    postCartAction(endpoint, values)
      .then(function (data) {
        updateCartBadges(data.totalcartitems);
        window.location.reload();
      })
      .catch(function (error) {
        cartAction.disabled = false;
        cartAction.textContent = originalText;
        showCartMessage(error.message || 'ارتباط با سبد خرید برقرار نشد؛ دوباره تلاش کنید.', true);
      });
  });

  document.querySelectorAll('[data-product-3d]').forEach(function (viewer) {
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    var maxAngle = 10;
    var zoomButton = viewer.querySelector('[data-zoom-toggle]');
    var zoomLocked = false;

    function setAngle(x, y) {
      viewer.style.setProperty('--product-tilt-x', y.toFixed(2) + 'deg');
      viewer.style.setProperty('--product-tilt-y', x.toFixed(2) + 'deg');
    }

    function setZoom(active) {
      viewer.classList.toggle('is-zoomed', active);
      if (zoomButton) {
        zoomButton.setAttribute('aria-pressed', active ? 'true' : 'false');
        zoomButton.setAttribute(
          'aria-label',
          active ? 'بستن بزرگ‌نمایی تصویر محصول' : 'بزرگ‌نمایی تصویر محصول'
        );
        var label = zoomButton.querySelector('span');
        if (label) label.textContent = active ? 'بستن بزرگ‌نمایی' : 'بزرگ‌نمایی';
      }
    }

    function resetAngle() {
      viewer.style.removeProperty('--product-tilt-x');
      viewer.style.removeProperty('--product-tilt-y');
    }

    var spinSources = (viewer.dataset.spinFrames || '').split('|').filter(Boolean);
    if (spinSources.length > 1) {
      var mainImage = viewer.querySelector('[data-gallery-main]');
      var resetSpinButton = viewer.querySelector('[data-spin-reset]');
      var currentFrame = 0;
      var dragging = false;
      var dragStartX = 0;
      var lastPointerX = 0;
      var accumulatedDelta = 0;

      function showFrame(index) {
        currentFrame = (index + spinSources.length) % spinSources.length;
        mainImage.src = spinSources[currentFrame];
        mainImage.alt = viewer.getAttribute('aria-label') + '؛ نمای ' + (currentFrame + 1) + ' از ' + spinSources.length;
      }

      function showOriginalImage() {
        mainImage.src = mainImage.dataset.galleryOriginalSrc;
        mainImage.alt = mainImage.dataset.galleryOriginalAlt || mainImage.alt;
      }

      spinSources.forEach(function (source, index) {
        if (index === 0) return;
        var image = new Image();
        image.src = source;
      });

      viewer.addEventListener('pointerdown', function (event) {
        if (event.target.closest('button')) return;
        delete viewer.dataset.spinDragged;
        dragging = true;
        dragStartX = event.clientX;
        accumulatedDelta = 0;
        lastPointerX = event.clientX;
        viewer.classList.add('is-spinning');
        viewer.setPointerCapture(event.pointerId);
      });

      viewer.addEventListener('pointermove', function (event) {
        if (!dragging) return;
        if (Math.abs(event.clientX - dragStartX) > 5) {
          viewer.dataset.spinDragged = 'true';
        }
        accumulatedDelta += event.clientX - lastPointerX;
        lastPointerX = event.clientX;
        var frameDistance = Math.max(6, viewer.clientWidth / spinSources.length);
        var frameSteps = Math.trunc(accumulatedDelta / frameDistance);
        if (frameSteps) {
          showFrame(currentFrame - frameSteps);
          accumulatedDelta -= frameSteps * frameDistance;
        }
      });

      function stopSpinning() {
        dragging = false;
        viewer.classList.remove('is-spinning');
      }

      viewer.addEventListener('pointerup', stopSpinning);
      viewer.addEventListener('pointercancel', stopSpinning);
      viewer.addEventListener('lostpointercapture', stopSpinning);
      viewer.addEventListener('keydown', function (event) {
        if (event.key === 'Home') {
          showOriginalImage();
          event.preventDefault();
        } else if (event.key === 'ArrowLeft') {
          showFrame(currentFrame + 1);
          event.preventDefault();
        } else if (event.key === 'ArrowRight') {
          showFrame(currentFrame - 1);
          event.preventDefault();
        } else if (event.key === 'Enter' || event.key === ' ') {
          if (imageZoomDialog) {
            openImageZoom(
              mainImage,
              mainImage.alt,
              mainImage.dataset.galleryOriginalSrc
            );
          }
          event.preventDefault();
        }
      });
      if (resetSpinButton) {
        resetSpinButton.addEventListener('click', function () {
          showOriginalImage();
          viewer.focus();
        });
      }
      if (zoomButton) {
        zoomButton.addEventListener('click', function () {
          zoomLocked = !zoomLocked;
          setZoom(zoomLocked);
        });
      }
      return;
    }

    if (!reduceMotion.matches) {
      viewer.addEventListener('pointermove', function (event) {
        var bounds = viewer.getBoundingClientRect();
        var x = (event.clientX - bounds.left) / bounds.width;
        var y = (event.clientY - bounds.top) / bounds.height;
        viewer.style.setProperty('--product-zoom-origin', (x * 100).toFixed(2) + '% ' + (y * 100).toFixed(2) + '%');

        if (event.pointerType === 'mouse') {
          setZoom(true);
          if (event.buttons !== 0) return;
          setAngle((0.5 - y) * maxAngle * 2, (x - 0.5) * maxAngle * 2);
        }
      });

      viewer.addEventListener('pointerleave', function () {
        if (!zoomLocked) setZoom(false);
        resetAngle();
      });
    }

    viewer.addEventListener('blur', resetAngle);
    viewer.addEventListener('keydown', function (event) {
      var currentX = parseFloat(viewer.style.getPropertyValue('--product-tilt-x')) || 0;
      var currentY = parseFloat(viewer.style.getPropertyValue('--product-tilt-y')) || 0;
      var step = 3;

      if (event.key === 'Home') {
        resetAngle();
        event.preventDefault();
      } else if (event.key === 'ArrowUp') {
        setAngle(currentY, Math.min(maxAngle, currentX + step));
        event.preventDefault();
      } else if (event.key === 'ArrowDown') {
        setAngle(currentY, Math.max(-maxAngle, currentX - step));
        event.preventDefault();
      } else if (event.key === 'ArrowLeft') {
        setAngle(Math.max(-maxAngle, currentY - step), currentX);
        event.preventDefault();
      } else if (event.key === 'ArrowRight') {
        setAngle(Math.min(maxAngle, currentY + step), currentX);
        event.preventDefault();
      } else if (event.key === 'Enter' || event.key === ' ') {
        if (imageZoomDialog) {
          var mainImage = viewer.querySelector('[data-gallery-main]');
          if (mainImage) openImageZoom(mainImage, mainImage.alt);
        }
        event.preventDefault();
      }
    });

    if (zoomButton) {
      zoomButton.addEventListener('click', function () {
        zoomLocked = !zoomLocked;
        setZoom(zoomLocked);
      });
    }
  });

  document.addEventListener('pointermove', function (event) {
    if (event.pointerType !== 'mouse') return;
    var imageLink = event.target.closest('.store-product-card__image, .beauty-product-card__image');
    if (!imageLink) return;

    var bounds = imageLink.getBoundingClientRect();
    var x = (event.clientX - bounds.left) / bounds.width;
    var y = (event.clientY - bounds.top) / bounds.height;
    imageLink.style.setProperty('--image-zoom-origin', (x * 100).toFixed(2) + '% ' + (y * 100).toFixed(2) + '%');
    imageLink.classList.add('is-zoomed');
    var image = imageLink.querySelector('img');
    if (image) image.style.transition = 'none';
  });

  document.addEventListener('pointerout', function (event) {
    var imageLink = event.target.closest('.store-product-card__image, .beauty-product-card__image');
    if (!imageLink || (event.relatedTarget && imageLink.contains(event.relatedTarget))) return;
    imageLink.classList.remove('is-zoomed');
    var image = imageLink.querySelector('img');
    if (image) {
      image.style.transition = 'none';
      image.style.removeProperty('transform');
      window.requestAnimationFrame(function () {
        image.style.removeProperty('transition');
      });
    }
  });

  document.addEventListener('click', function (event) {
    var galleryThumb = event.target.closest('[data-gallery-thumb]');
    if (galleryThumb) {
      var gallery = galleryThumb.closest('.store-product-gallery');
      var mainImage = gallery && gallery.querySelector('[data-gallery-main]');
      if (!mainImage) return;

      var zoomViewer = gallery.querySelector('[data-product-3d]');
      var zoomButton = gallery.querySelector('[data-zoom-toggle]');
      if (zoomButton && zoomButton.getAttribute('aria-pressed') === 'true') {
        zoomButton.click();
      } else if (zoomViewer) {
        zoomViewer.classList.remove('is-zoomed');
      }
      mainImage.src = galleryThumb.dataset.galleryImage;
      mainImage.alt = galleryThumb.dataset.galleryAlt || '';
      gallery.querySelectorAll('[data-gallery-thumb]').forEach(function (thumb) {
        thumb.setAttribute('aria-pressed', thumb === galleryThumb ? 'true' : 'false');
      });
      return;
    }

    var button = event.target.closest('.product-cart-btn');
    if (!button) return;

    var card = button.closest('.product-cart-wrap');
    if (!card || button.disabled) return;

    var cartUrl = card.dataset.cartUrl;
    if (!cartUrl) {
      showCartMessage('اتصال به سبد خرید در دسترس نیست؛ لطفاً صفحه را دوباره بارگذاری کنید.', true);
      return;
    }

    var originalLabel = button.textContent.trim();

    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = 'در حال افزودن…';

    // گارانتی انتخابی کاربر (Feature 7)
    var warrantyMonths = '0';
    var warrantyInput = card.querySelector('[data-warranty-option]:checked');
    if (warrantyInput) {
      warrantyMonths = warrantyInput.value || '0';
    }

    postCartAction(cartUrl, {
      id: card.dataset.productId || '',
      pid: card.dataset.productPid || '',
      title: card.dataset.productTitle || '',
      price: card.dataset.productPrice || '',
      image: card.dataset.productImage || '',
      qty: (card.querySelector('[class*="product-quantity-"]') || {}).value || '1',
      warranty_months: warrantyMonths,
      // These values only detect a stale page; the server owns the prices.
      expected_base_price: card.dataset.warrantyEnabled === 'true' ? (card.dataset.productPrice || '') : '',
      expected_warranty_price: warrantyInput ? (warrantyInput.dataset.warrantyPrice || '0') : ''
    }).then(function (data) {
        updateCartBadges(data.totalcartitems);
        button.textContent = 'به سبد خرید اضافه شد';
        showCartMessage('«' + (card.dataset.productTitle || 'محصول') + '» به سبد خرید اضافه شد.', false);
      })
      .catch(function (error) {
        button.textContent = originalLabel;
        showCartMessage(error.message || 'ارتباط با سبد خرید برقرار نشد؛ دوباره تلاش کنید.', true);
      })
      .finally(function () {
        button.disabled = false;
        button.removeAttribute('aria-busy');
        if (button.textContent === 'به سبد خرید اضافه شد') {
          window.setTimeout(function () {
            button.textContent = originalLabel;
          }, 2200);
        }
      });
  });

  var consultationForm = document.getElementById('contact-form') || document.getElementById('consultation-form');
  if (consultationForm) {
    consultationForm.addEventListener('submit', function (event) {
      event.preventDefault();

      var messageBox = document.getElementById('contact-form-status') || document.getElementById('cf-msg');
      var submitButton = consultationForm.querySelector('[type="submit"]');
      if (!messageBox || !submitButton) return;

      messageBox.textContent = '';
      messageBox.className = 'form-message';

      if (!consultationForm.reportValidity()) return;

      var originalLabel = submitButton.textContent;
      submitButton.disabled = true;
      submitButton.textContent = 'در حال ارسال…';
      messageBox.setAttribute('aria-busy', 'true');

      fetch(consultationForm.action, {
        method: 'POST',
        body: new FormData(consultationForm),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        }
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok || data.status !== 'success') {
              throw new Error(data.message || 'ثبت درخواست انجام نشد.');
            }
            return data;
          });
        })
        .then(function (data) {
          messageBox.textContent = data.message;
          messageBox.classList.add('success');
          consultationForm.reset();
        })
        .catch(function (error) {
          messageBox.textContent = error.message || 'ارتباط با سرور برقرار نشد؛ کمی بعد دوباره تلاش کنید.';
          messageBox.classList.add('error');
        })
        .finally(function () {
          submitButton.disabled = false;
          submitButton.textContent = originalLabel;
          messageBox.removeAttribute('aria-busy');
        });
    });
  }

  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (event) {
      var target = document.querySelector(anchor.getAttribute('href'));
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
        block: 'start'
      });
    });
  });

  // ---- Preloader (brand loading screen) ----
  (function () {
    var preloader = document.getElementById('hm-preloader');
    if (!preloader) return;
    var MIN_VISIBLE = 900;
    var start = Date.now();
    var hidden = false;

    function hide() {
      if (hidden) return;
      hidden = true;
      var wait = Math.max(0, MIN_VISIBLE - (Date.now() - start));
      window.setTimeout(function () {
        preloader.classList.add('is-done');
        window.setTimeout(function () {
          if (preloader.parentNode) preloader.parentNode.removeChild(preloader);
        }, 800);
      }, wait);
    }

    if (document.readyState === 'complete') hide();
    else window.addEventListener('load', hide);
    window.setTimeout(hide, 4000);
  })();
})();
