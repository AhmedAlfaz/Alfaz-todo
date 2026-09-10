#!/usr/bin/env python3
"""ABDO v40 patch: visible staleness for cached prayer times + i18n + cache hygiene.
Every replacement asserts exactly 1 match; aborts with no write if any check fails."""
import io, re, sys

P = '/home/user/Alfaz-todo/index.html'
SW = '/home/user/Alfaz-todo/sw.js'

s = io.open(P, encoding='utf-8').read()
orig_len = len(s)

def sub(text, old, new, label):
    n = text.count(old)
    if n != 1:
        print(f"ABORT [{label}]: anchor matched {n} times, expected 1")
        sys.exit(1)
    print(f"ok  [{label}]")
    return text.replace(old, new)

# ---- 1. cache read: keep timings + freshness metadata, tolerate legacy shape ----
old = """      const cacheKey = `alfatore_prayers_${ds}`;
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try { prayerTimings = JSON.parse(cached); } catch(e) { prayerTimings = {}; }
        renderPrayerCards(); updateNextPrayer();
      }"""
new = """      const cacheKey = `alfatore_prayers_${ds}`;
      const cached = localStorage.getItem(cacheKey);
      let cachedAt = 0;
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          if (parsed && parsed.v === 2 && parsed.timings) {
            prayerTimings = parsed.timings; cachedAt = parsed.cached_at || 0;
          } else {
            prayerTimings = parsed || {};   // legacy v1: bare timings object
          }
        } catch(e) { prayerTimings = {}; }
        renderPrayerCards(); updateNextPrayer();
      }"""
s = sub(s, old, new, 'cache read v2 + legacy tolerance')

# ---- 2. cache write: store metadata so we can tell "today" from "yesterday" ----
old = """          localStorage.setItem(cacheKey, JSON.stringify(prayerTimings));"""
new = """          localStorage.setItem(cacheKey, JSON.stringify({ v: 2, cached_at: Date.now(), date_key: ds, timings: prayerTimings }));
          cachedAt = Date.now();"""
s = sub(s, old, new, 'cache write v2 metadata')

# ---- 3. render the freshness state (after the cards so the element exists) ----
old = """    function renderPrayerCards() {"""
new = """    function renderPrayerFreshness() {
      const el = document.getElementById('prayer-freshness');
      if (!el) return;
      const t = i18n[currentLang];
      if (!Object.keys(prayerTimings || {}).length) { el.classList.add('hidden'); return; }
      const fresh = cachedAt && (Date.now() - cachedAt) < 12 * 3600 * 1000;
      if (fresh) { el.classList.add('hidden'); return; }
      el.classList.remove('hidden');
      const ago = cachedAt ? Math.max(0, Math.round((Date.now() - cachedAt) / 3600000)) : null;
      el.innerHTML = `<i class="fas fa-triangle-exclamation me-1"></i> ${ago === null ? t.prayerTimesStaleUnknown : t.prayerTimesStale.replace('{h}', ago)}`;
    }

    function renderPrayerCards() {"""
s = sub(s, old, new, 'renderPrayerFreshness helper')

# ---- 4. call it at the end of renderPrayerCards ----
old = """      }
    }

    function updateNextPrayer() {"""
new = """      }
      renderPrayerFreshness();
    }

    function updateNextPrayer() {"""
s = sub(s, old, new, 'call freshness from render')

# ---- 5. the element ----
old = """        <p class="text-sm text-blue-600 dark:text-blue-400 font-medium" id="next-prayer-text">
          <i class="fas fa-clock me-1"></i> Loading prayer times...
        </p>"""
new = """        <p class="text-sm text-blue-600 dark:text-blue-400 font-medium" id="next-prayer-text">
          <i class="fas fa-clock me-1"></i> Loading prayer times...
        </p>
        <p id="prayer-freshness" class="hidden mt-2 text-xs text-amber-600 dark:text-amber-400 font-medium"></p>"""
s = sub(s, old, new, 'prayer-freshness element')

# ---- 6. i18n ----
s = sub(s, '        enableNotif: "Enable Notifications", notifEnabled: "Notifications Enabled \u2713",',
        '        enableNotif: "Enable Notifications", notifEnabled: "Notifications Enabled \u2713",\n'
        '        prayerTimesStale: "These times are ~{h}h old \u2014 check your connection and refresh.",\n'
        '        prayerTimesStaleUnknown: "These times may be from an earlier day \u2014 refresh when online.",',
        'i18n en')
# insert into the `ar:` block only, by line position (indentation- and quote-agnostic)
lines = s.split('\n')
ar_start = next((i for i, l in enumerate(lines) if l.strip() == 'ar: {'), None)
if ar_start is None:
    print("ABORT [i18n ar]: 'ar: {' block not found"); sys.exit(1)
tgt = None
for i in range(ar_start, min(ar_start + 200, len(lines))):
    if 'enableNotif:' in lines[i] and 'notifEnabled:' in lines[i]:
        tgt = i; break
if tgt is None:
    print("ABORT [i18n ar]: enableNotif line inside ar block not found"); sys.exit(1)
if 'prayerTimesStale' in '\n'.join(lines[ar_start:ar_start + 200]):
    print("ABORT [i18n ar]: key already present"); sys.exit(1)
indent = lines[tgt][:len(lines[tgt]) - len(lines[tgt].lstrip())]
lines.insert(tgt + 1, indent + 'prayerTimesStale: "هذه الأوقات قديمة منذ نحو {h} ساعة — تأكد من الاتصال وحدّث.",')
lines.insert(tgt + 2, indent + 'prayerTimesStaleUnknown: "ربما هذه الأوقات من يوم سابق — حدّثها عند توفر اتصال.",')
s = '\n'.join(lines)
print(f"ok  [i18n ar] inserted after line {tgt + 1} (indent {len(indent)} spaces)")

# ---- 7. refresh query v39 -> v40 ----
s = sub(s, "?v=39&t=", "?v=40&t=", 'refresh query')

io.open(P, 'w', encoding='utf-8').write(s)
print(f"\nindex.html {orig_len} -> {len(s)} bytes (delta {len(s)-orig_len})")
if len(s) < 250000:
    print("ABORT: file shrank below expected size"); sys.exit(1)

# ---- sw.js hygiene ----
w = io.open(SW, encoding='utf-8').read()
wlen = len(w)
old = "await Promise.all(keys.filter(k => k !== CACHE_NAME && k !== 'alfaz-prayer-v1').map(k => caches.delete(k)));"
new = "await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));"
if w.count(old) != 1:
    print(f"ABORT [sw dead cache ref]: matched {w.count(old)}"); sys.exit(1)
w = w.replace(old, new)
if "alfaz-todo-v39" not in w:
    print("ABORT [sw version]: v39 not found"); sys.exit(1)
w = w.replace("alfaz-todo-v39", "alfaz-todo-v40")
print("ok  [sw dead cache ref removed + version v40]")
io.open(SW, 'w', encoding='utf-8').write(w)
print(f"sw.js {wlen} -> {len(w)} bytes")
print("\nDONE")
