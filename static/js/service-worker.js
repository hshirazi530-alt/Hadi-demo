const CACHE_NAME = "hejrmarket-static-v4"; // مرحله ۵ سریع‌تر: bump for new icons
const OFFLINE_PAGE = "/static/offline.html";
const PRECACHE_ICONS = [
  "/static/assets/imgs/icons/purchase-step-5.png",
  "/static/assets/imgs/icons/purchase-step-1.png",
  "/static/assets/imgs/icons/purchase-step-2.png",
  "/static/assets/imgs/icons/purchase-step-3.png",
  "/static/assets/imgs/icons/purchase-step-4.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll([OFFLINE_PAGE, ...PRECACHE_ICONS]))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith("hejrmarket-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_PAGE))
    );
    return;
  }

  const isPurchaseIcon = /^\/static\/assets\/imgs\/icons\/purchase-step-\d+\.png$/.test(url.pathname);
  const isStaticAsset = (url.pathname.startsWith("/static/")
    && (/\.(?:css|js|woff2?|ttf|otf|png|webp)$/i.test(url.pathname)
      || /^\/static\/assets\/imgs\/theme\/icons\/hejrmarket-app-\d+\.png$/.test(url.pathname)))
      || isPurchaseIcon;

  if (!isStaticAsset) return;

  // Purchase icons: CacheFirst for instant step-5 render
  if (isPurchaseIcon) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_NAME);
      const cached = await cache.match(request);
      if (cached) {
        // revalidate in background
        fetch(request).then((resp) => {
          if (resp.ok) cache.put(request, resp.clone());
        }).catch(() => {});
        return cached;
      }
      const response = await fetch(request);
      if (response.ok) await cache.put(request, response.clone());
      return response;
    })());
    return;
  }

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    try {
      const response = await fetch(request);
      if (response.ok && response.type === "basic") {
        await cache.put(request, response.clone());
      }
      return response;
    } catch (error) {
      const cached = await cache.match(request);
      if (cached) return cached;
      throw error;
    }
  })());
});
