const CACHE_NAME = 'alfaz-todo-v22';
const SHELL = [
  './',
  './index.html',
  './manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    for (const url of SHELL) {
      try { await cache.add(url); } catch (e) {}
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_NAME && k !== 'alfaz-prayer-v1').map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith((async () => {
    try {
      const fresh = await fetch(req);
      if (fresh && fresh.ok && (req.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname.endsWith('/'))) {
        const cache = await caches.open(CACHE_NAME);
        cache.put(req, fresh.clone());
      }
      return fresh;
    } catch (e) {
      const cached = await caches.match(req);
      if (cached) return cached;
      if (req.mode === 'navigate') {
        return (await caches.match('./index.html')) || (await caches.match('./'));
      }
      throw e;
    }
  })());
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (let client of clientList) {
        if (client.url === '/' && 'focus' in client) {
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
  event.waitUntil(Promise.resolve());
});

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
