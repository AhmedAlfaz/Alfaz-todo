import io, sys

# 1) index.html: a version line under the refresh button, labelled by i18n
P = '/home/user/Alfaz-todo/index.html'
s = io.open(P, encoding='utf-8').read()
anchor = """      <button onclick="openAudioStudioModal()" class="w-full flex items-center justify-center space-x-2 bg-indigo-600"""
assert s.count(anchor) == 1, 'sidebar anchor'
s = s.replace(anchor, """      <p id="app-version" class="text-center text-[11px] text-gray-400 dark:text-gray-500 py-1 select-all">
        <span data-i18n="appVersionLabel">App version</span>: <span id="app-version-num">…</span>
      </p>
""" + anchor)

for block_lang, key in (('en', '        shareAppBtn: "Share ABDO",'), ('ar', None)):
    if key:
        assert s.count(key) == 1, 'en anchor'
        s = s.replace(key, '        appVersionLabel: "App version", versionOutdated: "outdated — refresh",\n' + key)
lines = s.split('\n')
ar = next(i for i, l in enumerate(lines) if l.strip() == 'ar: {')
tgt = next(i for i in range(ar, ar + 240) if 'shareAppBtn:' in lines[i])
if 'appVersionLabel' not in '\n'.join(lines[ar:ar + 240]):
    lines.insert(tgt, '        appVersionLabel: "\u0625\u0635\u062f\u0627\u0631 \u0627\u0644\u062a\u0637\u0628\u064a\u0642", versionOutdated: "\u0642\u062f\u064a\u0645 \u2014 \u062d\u062f\u0651\u062b",')
    s = '\n'.join(lines)
io.open(P, 'w', encoding='utf-8').write(s)
print('index.html: version line + i18n')

# 2) client.js: read the version from the live cache name, so it can never drift from sw.js
C = '/home/user/Alfaz-todo/push/client.js'
c = io.open(C, encoding='utf-8').read()
start = c.index('  // ---- boot ----')
add = """  // The version label reads the service worker's own cache name. Deriving it there means it can
  // never drift out of sync with reality the way a hardcoded string in index.html would - and this
  // whole debug loop happened because 'is my phone on the new build?' was unanswerable from the app.
  function showVersion() {
    try {
      if (!('caches' in window)) return;
      caches.keys().then(function (ks) {
        var hit = null;
        for (var i = 0; i < ks.length; i++) { var m = /^alfaz-todo-v(\\d+)$/.exec(ks[i]); if (m) hit = m[1]; }
        var el = document.getElementById('app-version-num');
        if (el && hit) el.textContent = 'v' + hit;
      }).catch(function () {});
    } catch (e) {}
  }

"""
c = c[:start] + add + c[start:]
c = c.replace("  window.addEventListener('load', function () {\n    start();",
              "  window.addEventListener('load', function () {\n    showVersion();\n    start();")
io.open(C, 'w', encoding='utf-8').write(c)
print('client.js: version from cache name')

# 3) cron: a device count, so 'is my phone registered?' is one curl
K = '/home/user/Alfaz-todo/push/push-cron.php'
k = io.open(K, encoding='utf-8').read()
old = """    . ($lasterr ? "  last_error=" . substr(preg_replace('/\\s+/', ' ', $lasterr), 0, 170) : '') . "\\n";"""
new = """    . ($lasterr ? "  last_error=" . substr(preg_replace('/\\s+/', ' ', $lasterr), 0, 170) : '')
    . (isset($_GET['devices']) ? '  devices=' . (count(glob(dirname($cfg['dir']) . '/user-*.json') ?: [])) : '')
    . "\\n";"""
assert k.count(old) == 1, 'cron tail anchor'
io.open(K, 'w', encoding='utf-8').write(k.replace(old, new))
print('push-cron.php: ?devices=1')

for f in (P, C, K):
    t = io.open(f, encoding='utf-8').read()
    d = 0
    for ch in t:
        if f.endswith('.php') or f.endswith('.js'):
            d += (ch == '{') - (ch == '}')
    if d:
        print('  !! unbalanced', f, d); sys.exit(1)
print('braces balanced')
