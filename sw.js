const CACHE_NAME = 'alfaz-todo-v2';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  '/audio/makkah.mp3',
  '/audio/madinah.mp3',
  '/audio/alaqsa.mp3',
  '/audio/egypt.mp3',
  '/audio/turkey.mp3',
  '/audio/azan-alafasy.mp3',
  '/audio/azan-alafasy-alt.mp3',
  '/audio/azan-ahmad-nafees.mp3',
  '/audio/azan-hafiz-ozcan.mp3',
  '/audio/azan-alafasy-dubai.mp3',
  '/audio/azan-mansour-zahrani.mp3',
  '/audio/azan-al-aqsa-mujir.mp3',
  '/audio/azan-madinah-haram.mp3'
];
const PRAYER_CACHE = 'alfaz-prayer-v1';
const PRAYER_TTL = 24 * 60 * 60 * 1000;

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(c => c.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME && k !== PRAYER_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  if (url.hostname === 'api.aladhan.com') {
    e.respondWith(
      caches.open(PRAYER_CACHE).then(async cache => {
        const cached = await cache.match(e.request);
        if (cached) {
          const data = await cached.json();
          const age = Date.now() - (data._cachedAt || 0);
          if (age < PRAYER_TTL) return cached;
        }
        try {
          const res = await fetch(e.request);
          if (res.ok) {
            const clone = res.clone();
            const body = await clone.json();
            body._cachedAt = Date.now();
            const wrapped = new Response(JSON.stringify(body), {
              status: clone.status,
              headers: clone.headers
            });
            cache.put(e.request, wrapped);
          }
          return res;
        } catch {
          return cached || new Response(JSON.stringify({ error: 'offline' }), { status: 503 });
        }
      })
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).catch(() => {
      if (e.request.mode === 'navigate') return caches.match('/index.html');
    }))
  );
});

self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'Alfaz todo', {
      body: data.body || '',
      icon: '/ALFA LOGO icon.jpg',
      badge: '/ALFA LOGO icon.jpg',
      tag: 'alfaz-prayer',
      requireInteraction: true
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow('/index.html'));
});
