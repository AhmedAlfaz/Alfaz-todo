// ABDO push notifications — client side.
//
// Everything here is inert unless `push-config.json` exists on the origin and contains an appId.
// That is deliberate: the app behaves exactly as it did before push existed when the file is
// missing, on a fresh checkout, in a sandbox, or if OneSignal's CDN is blocked (a CDN failure is
// what silently killed sign-in once, on phone networks).
//
// The OneSignal page SDK is loaded by index.html with `defer`; our init is queued through
// OneSignalDeferred so correctness never depends on network script order.
(function () {
  'use strict';

  var STATE_KEY = 'alfaz_push_state';   // unset = never decided | 'on' | 'off'
  var SNOOZE_KEY = 'alfaz_push_snooze'; // timestamp: "ask me later"
  var ASKED_KEY = 'alfaz_push_asked';   // we raise the soft-ask at most once per install
  var UID_KEY = 'alfaz_push_uid';
  var SNOOZE_DAYS = 30;
  var cfg = null;
  var osReady = false;
  var lastSynced = 0;

  function ls(k, v) {
    try {
      if (v === undefined) return localStorage.getItem(k);
      localStorage.setItem(k, v);
    } catch (e) {}
    return null;
  }
  // Unset must not mean "refused": if it did, a user who dismissed the ask once could be
  // re-asked forever, and a user who never saw it would be treated as opted out.
  function state() { return ls(STATE_KEY) || 'off'; }
  function setState(s) { ls(STATE_KEY, s); }
  function decided() { var v = ls(STATE_KEY); return v === 'on' || v === 'off'; }
  function snoozed() {
    var sn = parseInt(ls(SNOOZE_KEY) || '0', 10);
    return !!(sn && Date.now() < sn);
  }

  // A guest has no uid, so the device gets one that its own queue can be addressed by. It is
  // dropped on sign-out so one person's device id cannot keep carrying another's prayer times.
  function pushUid() {
    try { if (window.currentUser && currentUser.id) return String(currentUser.id); } catch (e) {}
    var id = ls(UID_KEY);
    if (!id) {
      id = 'dev' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
      ls(UID_KEY, id);
    }
    return id;
  }
  function clearOnSignOut() {
    try { localStorage.removeItem(UID_KEY); localStorage.removeItem('alfaz_push_player'); } catch (e) {}
    syncPush('signout');
  }

  function canPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return false;
    if (!window.isSecureContext) return false;
    return true;
  }

  // iOS: push needs a home-screen install. Since iOS 17.4 EU users get no standalone mode at all,
  // so promising them alerts would be a lie. We stay quiet instead of prompting.
  function pushLooksImpossible() {
    var ua = navigator.userAgent || '';
    var ios = /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
    if (!ios) return false;
    var standalone = false;
    try { standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true; } catch (e) {}
    if (standalone) return false;
    var tz = '';
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
    return !standalone || /^Europe\//.test(tz);
  }

  // ---- OneSignal init ----
  function initOneSignal() {
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    window.OneSignalDeferred.push(function (OneSignal) {
      try {
        OneSignal.init({
          appId: cfg.appId,
          serviceWorkerPath: cfg.swPath || 'push/onesignal/OneSignalSDKWorker.js',
          serviceWorkerParam: cfg.swParam || { scope: 'push/onesignal/' },
          // We own the prompt (soft-ask only, never on load) and we do not want a "thanks for
          // subscribing" message landing on top of a real prayer alert.
          autoPrompt: false,
          // Off by default and it counts page views in localStorage (os_pageViews). An Islamic
          // app that advertises privacy has no business measuring browsing without asking.
          pageViewsEnabled: false,
          welcomeNotification: { disable: true },
          notify: true
        });
        osReady = true;
      } catch (e) { osReady = false; return; }   // a broken SDK must never surface as an ABDO error
      // OneSignal reports a wrong-origin appId with a page error. That is our own doing (one file
      // serves both origins), so contain it: no red console line for the user, no ABDO breakage.
      window.addEventListener('error', function (ev) {
        var m = ev && ev.message || '';
        if (/Can only be used on|AppID doesn't match existing apps|OneSignal/i.test(m)) {
          osReady = false;
          try { if (window.__abdoTrace) window.__abdoTrace.push(['onesignal refused', m.slice(0, 60)]); } catch (e2) {}
          ev.preventDefault();
        }
      }, true);
      if (state() === 'on') { try { enable(true).catch(function () {}); } catch (e) {} }
      else maybeAsk();
    });
  }

  function playerId() { return ls('alfaz_push_player'); }

  // Derive this device's queue-write token: HMAC-SHA256(uid + ':' + appId) with a PUBLIC
  // constant, base64url - byte-for-byte what push-lib.php's push_token_for() computes with the
  // server secret. Deliberate: no write credential is ever copy-pasted into a public config file.
  function deriveToken(uid, appId) {
    var secret = cfg.writeToken || '';
    if (!window.crypto || !crypto.subtle) return Promise.resolve('');
    return crypto.subtle.importKey('raw', new TextEncoder().encode(appId), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
      .then(function (k) { return crypto.subtle.sign('HMAC', k, new TextEncoder().encode(uid + ':' + secret)); })
      .then(function (sig) {
        var raw = String.fromCharCode.apply(null, new Uint8Array(sig));
        var mac = encodeURIComponent(btoa(raw));                 // matches PHP base64_encode + rawurlencode
        return btoa(uid + ':' + appId + ':' + mac).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
      })
      .catch(function () { return ''; });
  }

  function enable(silent) {
    if (!osReady || !window.OneSignal) return Promise.reject(new Error('OneSignal not ready'));
    return window.OneSignal.User.pushSubscription.optIn()
      .then(function () { return window.OneSignal.User.pushSubscription.getIdAsync(); })
      .then(function (id) {
        if (id) ls('alfaz_push_player', id);
        setState('on');
        if (!silent) { try { showToast(i18n[currentLang].pushOnToast || '🔔 Alerts are on', 'success'); } catch (e) {} }
        return syncPush('enable');
      })
      .catch(function (err) {
        // Explicitly NOT claiming success: no state flip, no toast that promises alerts.
        if (!silent) { try { showToast(i18n[currentLang].pushFailToast || 'Could not turn on alerts', 'error'); } catch (e) {} }
        throw err;
      });
  }

  function disable() {
    setState('off');
    if (osReady && window.OneSignal) { try { window.OneSignal.User.pushSubscription.optOut(); } catch (e) {} }
    return syncPush('disable');
  }

  // ---- schedule, from the data the app already has ----
  // Prayer times come from the app's own fetch (today only), so days 2..7 reuse today's times
  // until a later tier computes them locally. A few minutes of drift on a "time to pray" nudge
  // beats no nudge; exact times for tasks and plans are not approximated at all.
  function buildEvents() {
    var ev = [], now = new Date();
    try {
      if (typeof prayerTimings === 'object' && prayerTimings) {
        var keep = { Fajr: 1, Dhuhr: 1, Asr: 1, Maghrib: 1, Isha: 1 };
        for (var d = 0; d < 7; d++) {
          for (var p in prayerTimings) {
            if (!keep[p]) continue;
            var t = String(prayerTimings[p] || '').split(':');
            if (t.length < 2) continue;
            var day = new Date(now.getFullYear(), now.getMonth(), now.getDate() + d,
                              +t[0], +t[1] - (cfg.leadMinutes || 0), 0, 0);
            if (day.getTime() < Date.now() - 60000) continue;      // never queue the past
            if (ev.length >= (cfg.maxEvents || 60)) break;
            ev.push({ id: 'p:' + p + ':' + isoDay(day), send_at: Math.floor(day.getTime() / 1000),
                      title: '🕌 ' + p,
                      body: p + ' — ' + (currentLang === 'ar' ? 'حان وقت الصلاة' : 'time to pray'),
                      link: './' });
          }
        }
      }
      if (typeof tasks === 'object' && tasks) {
        for (var i = 0; i < tasks.length && ev.length < 120; i++) {
          var tk = tasks[i];
          if (!tk || tk.completed || tk.done || !tk.due_date) continue;
          var at = taskFireTime(tk);
          if (!at || at.getTime() < Date.now() - 60000) continue;
          ev.push({ id: 't:' + tk.due_date + ':' + String(tk.text || '').slice(0, 24),
                    send_at: Math.floor(at.getTime() / 1000), title: '✅',
                    body: String(tk.text || '').slice(0, 120), link: './' });
        }
      }
      if (typeof userPlans === 'object' && userPlans) {
        for (var j = 0; j < userPlans.length && ev.length < 120; j++) {
          var pl = userPlans[j];
          if (!pl || !pl.date) continue;
          if (pl.reminder_minutes === null || pl.reminder_minutes === undefined) continue;
          for (var k = 0; k < 7; k++) {
            var dd = new Date(now.getFullYear(), now.getMonth(), now.getDate() + k);
            var iso = isoDay(dd);
            if (typeof planOccursOnDate === 'function' && !planOccursOnDate(pl, iso)) continue;
            var hm = String(pl.time || '09:00').split(':');
            var fire = new Date(dd.getFullYear(), dd.getMonth(), dd.getDate(),
                                +hm[0], +hm[1] - (pl.reminder_minutes || 0), 0, 0);
            if (fire.getTime() < Date.now() - 60000) continue;
            if (ev.length >= 120) break;
            ev.push({ id: 'pl:' + pl.id + ':' + iso, send_at: Math.floor(fire.getTime() / 1000),
                      title: '📅', body: String(pl.title || '').slice(0, 120), link: './' });
          }
        }
      }
    } catch (e) { /* a malformed plan must not break the app */ }
    return ev;
  }

  function isoDay(d) {
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  function taskFireTime(tk) {
    try {
      if (tk.reminder_minutes === null || tk.reminder_minutes === undefined) return null;
      var parts = String(tk.due_date).split('-');
      var t = String(tk.due_time || '20:00').split(':');
      var base = new Date(+parts[0], +parts[1] - 1, +parts[2], +t[0], +t[1], 0, 0);
      base.setMinutes(base.getMinutes() - (+tk.reminder_minutes));
      return base;
    } catch (e) { return null; }
  }

  // ---- hand the schedule to our own sender ----
  function syncPush() {
    if (!cfg || !cfg.syncUrl || state() !== 'on') return Promise.resolve(null);
    if (Date.now() - lastSynced < 30000) return Promise.resolve(null);
    var ev = [];
    try { ev = buildEvents(); } catch (e) {}
    var body = { uid: pushUid(), token: '', player: playerId() || pushUid(), events: ev };
    lastSynced = Date.now();
    var prep = deriveToken(body.uid, cfg.appId).then(function (t) { body.token = t; return body; });
    return prep.then(function (payload) {
      return fetch(cfg.syncUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (j) { try { window.__abdoPush.lastSync = j; } catch (e) {} return j; })
      .catch(function () { return null; });   // offline/blocked: the in-app alarms still work
  }

  // The prompt is earned, never assumed: at most once per install, never while snoozed, never
  // after a decision, and only when the user already asked for a reminder of their own.
  function maybeAsk() {
    if (decided() || ls(ASKED_KEY) || snoozed()) return;
    var hasReason = false;
    try {
      hasReason = !!(document.getElementById('plan-reminder') && document.getElementById('plan-reminder').value) ||
                  (typeof tasks === 'object' && tasks && tasks.some(function (t) {
                    return t && t.reminder_minutes !== undefined && t.reminder_minutes !== null && !t.done;
                  }));
    } catch (e) {}
    if (!hasReason) return;
    softAsk();
  }
  function markInterested() { try { if (!decided() && !ls(ASKED_KEY)) maybeAsk(); } catch (e) {} }

  function softAsk() {
    if (document.getElementById('push-ask-modal')) return;
    var ar = currentLang === 'ar';
    var wrap = document.createElement('div');
    wrap.id = 'push-ask-modal';
    wrap.className = 'hidden fixed inset-0 bg-black/80 z-[96] flex items-center justify-center p-4';
    wrap.innerHTML =
      '<div class="bg-white dark:bg-gray-800 rounded-2xl p-6 w-full max-w-sm shadow-2xl">' +
      '<h3 class="text-lg font-bold text-gray-800 dark:text-white mb-2">' + (ar ? 'تذكيرات العبادة' : 'Prayer & task alerts') + '</h3>' +
      '<p class="text-sm text-gray-600 dark:text-gray-300 mb-5">' +
      (ar ? 'نرسل تنبيهًا عند وقت الصلاة وعند مهامك وخططك. بدون إعلانات ولا تتبّع، ويمكنك إيقافها في أي وقت.'
          : 'One alert at prayer time, and one for the tasks and plans you scheduled. No ads, no tracking, and you can switch it off any time.') +
      '</p>' +
      '<div class="space-y-2">' +
      '<button onclick="abdoPushAccept()" class="w-full bg-green-600 hover:bg-green-700 text-white py-3 px-4 rounded-lg font-semibold transition">' + (ar ? 'نعم، فعّل التنبيهات' : 'Yes, turn alerts on') + '</button>' +
      '<button onclick="abdoPushLater()" class="w-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 py-3 px-4 rounded-lg font-medium transition">' + (ar ? 'لاحقًا' : 'Maybe later') + '</button>' +
      '<button onclick="abdoPushNever()" class="w-full text-gray-500 dark:text-gray-400 py-2 px-4 text-sm">' + (ar ? 'لا، شكرًا' : 'No thanks') + '</button>' +
      '</div></div>';
    document.body.appendChild(wrap);
    wrap.classList.remove('hidden');
  }

  window.abdoPushAccept = function () {
    closeAsk();
    var go = function () { try { enable(false).catch(function () {}); } catch (e) {} };
    if ('Notification' in window && Notification.permission === 'default') {
      try { Notification.requestPermission().then(function (p) { if (p === 'granted') go(); }); } catch (e) {}
    } else go();
  };
  window.abdoPushLater = function () {
    closeAsk();
    try { ls(SNOOZE_KEY, String(Date.now() + SNOOZE_DAYS * 86400000)); ls(ASKED_KEY, '1'); } catch (e) {}
  };
  window.abdoPushNever = function () {
    closeAsk();
    setState('off');
    try { ls(ASKED_KEY, '1'); } catch (e) {}
  };
  function closeAsk() { var m = document.getElementById('push-ask-modal'); if (m) m.remove(); }

  window.abdoPushDisable = disable;   // Settings toggle can call this later

  // ---- config load, with fallbacks the app's own service worker cannot break ----
  // `cache: 'no-store'` guarantees a miss never lands in HTTP cache; offline, it simply fails.
  // So we also try the shell copy our sw.js pre-caches, then the plain cached response.
  // Without this, an offline launch would quietly lose push while keeping the UI that claims it.
  function loadSiteConfig(cb) {
    // Trace only where a developer can see it: never for real users, and only on loopback.
    var trace = null;
    try {
      var h = location.hostname;
      if (h === 'localhost' || h === '127.0.0.1') {
        trace = window.__abdoTrace = window.__abdoTrace || [];
        trace.push(['start', Date.now()]);
      }
    } catch (e) {}
    var done = function (j) { try { if (trace) trace.push(['resolved', j ? 'ok' : 'null']); } catch (e) {} cb(j); };
    var settled = false;
    var finish = function (j) { if (!settled) { settled = true; done(j); } };
    void trace;
    var fromCache = function () {
      try {
        if (!('caches' in window)) return fetch('site-config.json').then(function (r) { return r.ok ? r.json() : null; });
        return caches.match('site-config.json').then(function (hit) {
          if (hit) return hit.json();
          return fetch('site-config.json').then(function (r) { return r.ok ? r.json() : null; });
        });
      } catch (e) { return Promise.resolve(null); }
    };
    fetch('site-config.json', { cache: 'no-store' })
      .then(function (r) { try { if (trace) trace.push(['no-store', r.status]); } catch (e) {} return r.ok ? r.json() : null; })
      .then(function (j) { if (j) { finish(j); return; } return fromCache().then(function (k) { try { if (trace) trace.push(['fallback', k ? 'hit' : 'miss']); } catch (e) {} finish(k); }); })
      .catch(function (e) { try { if (trace) trace.push(['no-store threw', String(e && e.name || e)]); } catch (e2) {} fromCache().then(finish); });
  }

  // ---- canonical install link ----
  // Two hosting links = two apps as far as the browser (and push) is concerned. Rather than
  // pretend, one link is declared canonical and everything users are asked to share uses it.
  function canonicalUrl(j) {
    var here = location.origin + location.pathname.replace(/[^/]*$/, '');
    return (j && j.installUrl) || here;
  }
  function showWorkshopFlag() {
    try {
      var f = document.getElementById('workshop-flag');
      if (f) f.classList.remove('hidden');
    } catch (e) {}
  }

  function setupShare() {
    loadSiteConfig(function (j) {
      var url = canonicalUrl(j);
      try { window.__abdoSite = { installUrl: url, canonical: sameOrigin(url) }; } catch (e) {}
      var btn = document.getElementById('share-app-btn');
      if (btn) btn.addEventListener('click', function () { shareApp(); });
      // On a non-canonical origin, send installs to the one that can do push - as one button,
      // not a banner, so nobody is nagged on open.
      var nonCanonical = !!j.installUrl && !sameOrigin(j.installUrl);
      // On the canonical origin a "share this app" button is pointless - you are already there.
      var sb = document.getElementById('share-app-btn');
      if (sb && !nonCanonical) sb.classList.add('hidden');
      if (nonCanonical) showWorkshopFlag();
      var warn = document.getElementById('noncanonical-warn');
      if (warn && nonCanonical) {
        warn.innerHTML = '<i class="fas fa-info-circle me-1"></i>' +
          (currentLang === 'ar' ? 'لأفضل تجربة وللتذكيرات، ثبّت من الرابط الرئيسي' : 'For install prompts and reminders, use the main link');
        warn.classList.remove('hidden');
        warn.addEventListener('click', function () { shareApp(); });
      }
    });
  }
  function sameOrigin(u) {
    try { return new URL(u, location.href).origin === location.origin; } catch (e) { return true; }
  }
  window.shareApp = function () {
    var fire = function (u) {
      if (navigator.share) { navigator.share({ title: appDisplayName(currentLang), url: u }).catch(function () {}); return; }
      var done = function () { try { showToast('🔗 ' + (i18n[currentLang].copiedLink || 'Link copied'), 'success'); } catch (e) {} };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(u).then(done, function () { fallbackCopy(u); done(); });
      else { fallbackCopy(u); done(); }
    };
    if (window.__abdoSite && window.__abdoSite.installUrl) return fire(window.__abdoSite.installUrl);
    loadSiteConfig(function (j) { fire(canonicalUrl(j)); });
  };
  function fallbackCopy(u) {
    try {
      var ta = document.createElement('textarea');
      ta.value = u; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.left = '-9999px';
      document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
    } catch (e) {}
  }

  // ---- boot ----
  function bootPush(pc) {
    try { if (window.__abdoTrace) window.__abdoTrace.push(['bootPush', pc ? (pc.enabled === false ? 'disabled' : 'enabled') : 'no-push-node']); } catch (e) {}
    // Disabled here (e.g. GitHub Pages reusing the Hostinger appId) must not even load
    // OneSignal: their SDK would throw a visible console error for zero benefit.
    if (!pc || !pc.appId || pc.enabled === false) return;
    cfg = pc;
    try {
      window.__abdoPush = { cfg: cfg, state: state, decided: decided, buildEvents: buildEvents,
                            sync: syncPush, uid: pushUid, markInterested: markInterested,
                            maybeAsk: maybeAsk, enable: enable, disable: disable };
    } catch (e) {}
    initOneSignal();
  }

  function start() {
    try { if (window.__abdoTrace) window.__abdoTrace.push(['gates', canPush() ? 'canPush' : 'no-push', pushLooksImpossible() ? 'impossible' : 'possible']); } catch (e) {}
    if (!canPush() || pushLooksImpossible()) { setupShare(); return; }   // no config paid for by devices that cannot use it
    var host = location.hostname || '';
    if (host === 'localhost' || host === '127.0.0.1') {
      var q = new URLSearchParams(location.search);
      if (!q.get('pushApp')) return;                   // local dev opts in explicitly
    }
    loadSiteConfig(function (j) {
      setupShare();
      bootPush(j && j.push ? j.push : null);
    });
  }

  window.addEventListener('load', function () {
    start();
    document.addEventListener('signout', clearOnSignOut);
  });
})();
