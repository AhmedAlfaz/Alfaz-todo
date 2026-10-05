// ABDO service worker.
//
// Design rule: the update path must be ATOMIC for critical assets. An install that swallows a
// failure and then calls skipWaiting() hands control to a worker whose cache is missing a file -
// for a single-file app that means "slightly stale", for a split app it means a blank white
// screen offline. So: required files use addAll (all-or-nothing, install fails -> the old worker
// keeps serving and we fix the deploy), optional files are best-effort.

const VERSION = 'v49';
const CACHE_NAME = 'alfaz-todo-' + VERSION;
const CORE = ['.', 'index.html', 'sw.js', 'site-config.json'];
const OPTIONAL = [
  'manifest.json',
  'brand/abdo-icon-192-wb.png',
  'brand/abdo-icon-512-wb.png',
  'brand/abdo-icon-512-maskable-wb.png'
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    // Throws on any miss -> no skipWaiting -> current worker stays in control.
    await cache.addAll(CORE);
    await Promise.all(OPTIONAL.map(u => cache.add(u).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // HTML and navigations: network first, cache as the offline fallback. Never serve a cached
  // shell ahead of the network or updates become invisible for up to the CDN's max-age.
  if (req.mode === 'navigate' || url.pathname.endsWith('.html')) {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        if (fresh && fresh.ok) {
          const cache = await caches.open(CACHE_NAME);
          cache.put(req, fresh.clone());
        }
        return fresh;
      } catch (e) {
        const hit = (await caches.match(req)) || (await caches.match('index.html'));
        if (hit) return hit;
        throw e;
      }
    })());
    return;
  }

  // Static assets: cache first, fill on miss, and refresh in the background when a version bumps.
  event.respondWith((async () => {
    const hit = await caches.match(req);
    if (hit) return hit;
    const res = await fetch(req);
    if (res && res.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(req, res.clone());
    }
    return res;
  })());
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      const appPath = self.location.pathname;
      for (let client of clientList) {
        if (new URL(client.url).pathname === appPath && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('./');
      }
    })
  );
});

self.addEventListener('notificationclose', event => {
  event.notification.close();
});

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
