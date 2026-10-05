#!/usr/bin/env python3
"""Atomic-install gate for sw.js.

Why this test exists: sw.js used to swallow every cache failure and then skipWaiting() anyway.
With one index.html that meant "slightly stale". After splitting into several JS files it would
mean a blank offline app. This proves the safe half of that claim directly.

  python3 tools/test_sw_atomic.py
"""
import os, json, os, shutil, subprocess, sys, tempfile, threading, http.server, time

try:
    from playwright.sync_api import sync_playwright

except ModuleNotFoundError:
    sys.stderr.write('RUNTIME DEPENDENCY MISSING: pip install playwright (and a chromium binary)\n')
    sys.exit(3)

def _chromium():
    return os.environ.get('CHROME') or shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome') or None
REPO = '/home/user/Alfaz-todo'
CHROMIUM = shutil.which('chromium') or shutil.which('chromium-browser') or '/usr/bin/chromium'


def serve(root, port):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=root, **k)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def build(broken):
    """Copy the app; optionally remove a CORE asset so addAll must fail."""
    d = tempfile.mkdtemp(prefix='abdo-sw-')
    for f in ['index.html', 'sw.js', 'site-config.json', 'manifest.json']:
        shutil.copy(os.path.join(REPO, f), d)
    os.makedirs(os.path.join(d, 'brand'), exist_ok=True)
    for f in os.listdir(os.path.join(REPO, 'brand')):
        shutil.copy(os.path.join(REPO, 'brand', f), os.path.join(d, 'brand', f))
    if broken:
        os.remove(os.path.join(d, 'site-config.json'))   # CORE member -> install must abort
    return d


def run(label, broken, port):
    root = build(broken)
    srv = serve(root, port)
    time.sleep(0.4)
    out = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=_chromium(),
                               args=['--no-sandbox', '--disable-dev-shm-usage'])
        ctx = b.new_context()
        pg = ctx.new_page()
        try:
            pg.goto(f'http://127.0.0.1:{port}/index.html', wait_until='load', timeout=30000)
            pg.evaluate("""async () => {
                window.__r = {};
                const reg = await navigator.serviceWorker.register('/sw.js');
                window.__r.waiting = !!reg.waiting;
                await new Promise(r => setTimeout(r, 2500));
                window.__r.active = !!reg.active;
                window.__r.controller = !!navigator.serviceWorker.controller;
                window.__r.caches = (await caches.keys()).filter(k => k.startsWith('alfaz-todo'));
                window.__r.size = await (async () => {
                    const ks = (await caches.keys()).filter(k => k.startsWith('alfaz-todo'));
                    let n = 0; for (const k of ks) n += (await (await caches.open(k)).keys()).length;
                    return n;
                })();
            }""")
            out = pg.evaluate("() => window.__r")
        finally:
            b.close()
            srv.shutdown()
            shutil.rmtree(root, ignore_errors=True)
    print(f'  {label}: {json.dumps(out)}')
    return out


print('sw.js atomic-install gate')
print('-----------------------')
ok = True

# Good deploy: every CORE file present -> worker activates and caches all 9 assets.
good = run('complete deploy ', False, 8231)
a = good.get('active') and len(good.get('caches', [])) == 1 and good.get('size', 0) >= 8
print(('  PASS  ' if a else '  FAIL  ') + 'complete deploy caches the shell and activates')
ok &= a

# Broken deploy: a CORE file is missing -> addAll throws -> no activation, old worker keeps control.
bad = run('missing-asset ', True, 8232)
b = (not bad.get('controller')) and not bad.get('active')
print(('  PASS  ' if b else '  FAIL  ') + 'broken deploy does NOT take control (no skipWaiting on failure)')
ok &= b

if not b:
    print('  >> This is the dangerous case: a partial cache would be served to offline users.')

sys.exit(0 if ok else 1)
