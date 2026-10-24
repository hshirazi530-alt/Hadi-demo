// Product detail tabs — vanilla JS + WAI-ARIA tab pattern.
// Keyboard: ArrowLeft/ArrowRight (RTL aware), Home, End.
// No layout shift: panels stay in the DOM, only `hidden` toggles.

const TABS_SELECTOR = "[data-product-tabs]";
const STORAGE_KEY = "hm-product-detail-tab";

function activateTab(root, tab, focus) {
  const tablist = root.querySelector("[data-tabs-tablist]");
  const tabs = Array.from(tablist.querySelectorAll("[data-tabs-tab]"));
  const panels = Array.from(root.querySelectorAll("[data-tabs-panel]"));

  tabs.forEach(function (t) {
    const selected = t === tab;
    t.setAttribute("aria-selected", String(selected));
    t.tabIndex = selected ? 0 : -1;
  });
  panels.forEach(function (p) {
    p.hidden = p.id !== tab.dataset.tabsTarget;
  });

  if (focus) tab.focus();
}

function initTabs(root) {
  const tablist = root.querySelector("[data-tabs-tablist]");
  if (!tablist) return;
  const tabs = Array.from(tablist.querySelectorAll("[data-tabs-tab]"));
  if (!tabs.length) return;

  // Restore last selected tab (e.g. after posting a review).
  let initial = tabs[0];
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      const match = tabs.find(function (t) {
        return t.dataset.tabsTarget === saved;
      });
      if (match) initial = match;
    }
  } catch (err) {
    /* sessionStorage unavailable — ignore */
  }
  activateTab(root, initial, false);

  tablist.addEventListener("click", function (event) {
    const tab = event.target.closest("[data-tabs-tab]");
    if (!tab) return;
    sessionStorage.setItem(STORAGE_KEY, tab.dataset.tabsTarget);
    activateTab(root, tab, false);
  });

  // RTL: ArrowLeft = next, ArrowRight = previous (mirrors visual order).
  tablist.addEventListener("keydown", function (event) {
    const current = tabs.indexOf(event.target.closest("[data-tabs-tab]"));
    if (current === -1) return;

    let next = null;
    if (event.key === "ArrowLeft") {
      next = tabs[(current + 1) % tabs.length];
    } else if (event.key === "ArrowRight") {
      next = tabs[(current - 1 + tabs.length) % tabs.length];
    } else if (event.key === "Home") {
      next = tabs[0];
    } else if (event.key === "End") {
      next = tabs[tabs.length - 1];
    } else {
      return;
    }

    event.preventDefault();
    sessionStorage.setItem(STORAGE_KEY, next.dataset.tabsTarget);
    activateTab(root, next, true);
  });

  // Deep link: the rating link jumps to the reviews tab.
  const goto = root.querySelector("[data-tabs-goto]");
  if (goto) {
    goto.addEventListener("click", function () {
      const target = goto.dataset.tabsGoto;
      const tab = tabs.find(function (t) {
        return t.dataset.tabsTarget === target;
      });
      if (tab) {
        sessionStorage.setItem(STORAGE_KEY, target);
        activateTab(root, tab, false);
      }
    });
  }
}

function init() {
  document.querySelectorAll(TABS_SELECTOR).forEach(initTabs);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
