/* LootTracker service worker
   Strategy:
   - App shell (HTML/icons/manifest): cache-first, so the app opens instantly & offline.
   - API calls (/api/*): network-first, so deals are always fresh; fall back to last
     cached response only if the network is unavailable.
*/
const VERSION = "loottracker-v1";
const SHELL = [
  "/",
  "/manifest.json",
  "/static/icon-192.png",
  "/static/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Network-first for live deal data.
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(VERSION).then((c) => c.put(request, copy)).catch(() => {});
          return resp;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first for the app shell & static assets.
  event.respondWith(
    caches.match(request).then((cached) => {
      return (
        cached ||
        fetch(request)
          .then((resp) => {
            const copy = resp.clone();
            caches.open(VERSION).then((c) => c.put(request, copy)).catch(() => {});
            return resp;
          })
          .catch(() => caches.match("/"))
      );
    })
  );
});
