/**
 * admin-list-layout.js
 * Normalizes all admin changelist tables to the product-page pattern:
 * checkbox (rightmost in RTL) -> image -> title -> other params.
 *
 * Uses a <colgroup> with explicit pixel widths under table-layout: fixed,
 * so the image column stays narrow and the title column absorbs the rest.
 */
(function () {
  'use strict';

  var CHECKBOX_W = 42;
  var IMAGE_W = 84;
  var MAX_TITLE_W = 380;

  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

  function measureNatural(table, headCells, bodyRows) {
    // clear colgroup influence + inline widths, switch to auto, measure, restore
    var prevLayout = table.style.tableLayout;
    var prevWidth = table.style.width;
    headCells.forEach(function (c) { c.style.width = ''; });
    bodyRows.forEach(function (row) {
      Array.prototype.forEach.call(row.querySelectorAll('td, th'), function (c) { c.style.width = ''; });
    });
    table.style.tableLayout = 'auto';
    table.style.width = 'auto';
    var natural = headCells.map(function (c) { return Math.ceil(c.getBoundingClientRect().width) + 1; });
    if (bodyRows.length) {
      var bodyCells = bodyRows[0].querySelectorAll('td, th');
      headCells.forEach(function (_, i) {
        if (bodyCells[i]) {
          var bw = Math.ceil(bodyCells[i].getBoundingClientRect().width) + 1;
          if (bw > natural[i]) natural[i] = bw;
        }
      });
    }
    table.style.tableLayout = prevLayout;
    table.style.width = prevWidth;
    return natural;
  }

  function fixTable(table) {
    var container = table.closest('.table-responsive, .card-body, .results');
    var available = container ? container.clientWidth : table.parentElement.clientWidth;
    if (!available) return;

    var head = table.querySelector('thead');
    if (!head) return;
    var headCells = Array.prototype.slice.call(head.querySelectorAll('th, td'));
    if (headCells.length < 2) return;
    var bodyRows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));

    var natural = measureNatural(table, headCells, bodyRows);

    // col 0 = checkbox (fixed), col 1 = image (fixed), col 2 = title (flex), rest = natural
    var widths = headCells.map(function (_, i) {
      if (i === 0) return CHECKBOX_W;
      if (i === 1) return IMAGE_W;
      return natural[i];
    });

    var total = widths.reduce(function (a, b) { return a + b; }, 0);
    var titleIdx = 2;

    if (total > available) {
      var overflow = total - available;
      if (widths[titleIdx] !== undefined) {
        var take = clamp(widths[titleIdx] - 60, 0, overflow);
        widths[titleIdx] -= take;
        overflow -= take;
      }
      if (overflow > 0) {
        var flexTotal = 0;
        for (var i = 3; i < widths.length; i++) flexTotal += widths[i];
        if (flexTotal > 0) {
          for (var j = 3; j < widths.length; j++) {
            widths[j] = Math.max(56, widths[j] - (widths[j] / flexTotal) * overflow);
          }
        }
      }
      total = widths.reduce(function (a, b) { return a + b; }, 0);
    } else if (total < available) {
      if (widths[titleIdx] !== undefined) widths[titleIdx] += (available - total);
      total = available;
    }
    if (widths[titleIdx] !== undefined) widths[titleIdx] = clamp(widths[titleIdx], 60, MAX_TITLE_W);

    // build/replace colgroup
    var colgroup = table.querySelector('colgroup');
    if (!colgroup) {
      colgroup = document.createElement('colgroup');
      table.insertBefore(colgroup, table.firstChild);
    }
    colgroup.innerHTML = '';
    widths.forEach(function (w) {
      var col = document.createElement('col');
      col.style.width = w + 'px';
      colgroup.appendChild(col);
    });
    table.style.setProperty('width', total + 'px', 'important');
  }

  function fixAll() {
    var tables = document.querySelectorAll('#result_list, .results table');
    tables.forEach(function (t) { fixTable(t); });
  }

  var timer = null;
  function schedule() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(fixAll, 80);
  }

  function init() {
    schedule();
    window.addEventListener('resize', schedule);
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        if (mutations[i].addedNodes && mutations[i].addedNodes.length) { schedule(); break; }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
