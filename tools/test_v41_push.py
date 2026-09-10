#!/usr/bin/env python3
"""v41 push client test. Real Chromium, real files, served over http.
Covers: inert-by-default, activation with config, no auto-prompt, the earned one-shot soft-ask,
schedule building for prayers + tasks + plans, and the sync POST shape.
A real OneSignal subscription needs HTTPS *and* the appId's configured site origin; 2c proves
OneSignal itself refuses any other origin, which is why the mocked run carries the rest."""
import json, sys, time, subprocess, signal
from playwright.sync_api import sync_playwright

REPO, PORT = '/home/user/Alfaz-todo', 8099
srv_proc = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
URL = f'http://127.0.0.1:{PORT}/index.html'
ALADHAN = '**/api.aladhan.com/**'
TIMINGS = {"Fajr": "04:47", "Sunrise": "06:12", "Dhuhr": "12:04", "Asr": "15:38", "Maghrib": "19:20", "Isha": "20:46"}
CFG = {"enabled": True, "appId": "test-app-id", "swPath": "push/onesignal/OneSignalSDKWorker.js",
       "swParam": {"scope": "push/onesignal/"}, "syncUrl": "http://127.0.0.1:9/sink",
       "writeToken": "tok-test", "leadMinutes": 0}

GEO = "Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition:(ok,err)=>err({code:1})},writable:true});"

# Mock that (a) survives our client's `window.OneSignalDeferred = []` assignment and
# (b) blocks OneSignal's CDN so its page script cannot overwrite the mock.
MOCK = """
window.__initCalls = []; window.__syncBodies = [];
const sub = { optIn: () => (window.__optIn = (window.__optIn||0)+1, Promise.resolve()),
              getIdAsync: () => Promise.resolve('player-mock-1'),
              addEventListener: () => {}, removeEventListener: () => {},
              get: () => ({ id: 'player-mock-1', token: 't', optedIn: true }) };
window.OneSignal = { __mock: true,
  init: (o) => { window.__initCalls.push(o); },
  User: { pushSubscription: sub, addAlias: () => {}, addTag: () => {} },
  Slidedown: { isInitialized: () => false, init: () => Promise.resolve(), show: () => Promise.resolve() },
  Notifications: { addEventListener: () => {} }, Session: { addEventListener: () => {} } };
Object.defineProperty(window, 'OneSignalDeferred', { configurable: true,
  set: function(v) { window.__q = v; },
  get: function() { return { push: function(fn) {
    try { fn(window.OneSignal); window.__deferredRan = true; } catch (e) { window.__initError = String(e); } } }; }
});
const of = window.fetch;
window.fetch = function(u, o) { if (String(u).indexOf('/sink') > -1 && o && o.body) window.__syncBodies.push(o.body); return of.apply(this, arguments); };
Object.defineProperty(Notification, 'permission', { value: 'granted', configurable: true });
Notification.requestPermission = function () { return Promise.resolve('granted'); };
"""

# OneSignal's own expected complaints (fake appId, foreign origin) + our dead test sink.
NOISE = ('net::ERR', 'push-config', 'push-sync', '127.0.0.1:9', 'favicon', 'Failed to load resource',
         'Can only be used on', "AppID doesn't match existing apps")

def clean(errs):
    return [e for e in errs if not any(n in e for n in NOISE)]

res = []
def check(name, cond, detail=''):
    res.append(cond)
    print(('PASS  ' if cond else 'FAIL  ') + name + (('   | ' + str(detail)[:185]) if detail else ''))

def make_page(browser, cfg=True, mock=False):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844})
    ctx.add_init_script(GEO)
    if mock:
        ctx.add_init_script(MOCK)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append('console.error: ' + m.text) if m.type == 'error' else None)
    if cfg:
        pg.route('**/push-config.json', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(CFG)))
    else:
        pg.route('**/push-config.json', lambda r: r.fulfill(status=404, content_type='text/plain', body='nope'))
    pg.route(CFG['syncUrl'], lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True, 'queued': 5})))
    pg.route(ALADHAN, lambda r: r.fulfill(status=200, content_type='application/json',
                                          body=json.dumps({"code": 200, "data": {"timings": TIMINGS}})))
    if mock:
        pg.route('https://cdn.onesignal.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body='/*blocked*/'))
        pg.route('http://cdn.onesignal.com/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body='/*blocked*/'))
    pg.goto(URL + '?pushApp=1', wait_until='load', timeout=45000)
    pg.wait_for_timeout(2200)
    return pg, errs

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox', '--disable-dev-shm-usage'])

    # 1) no config on the origin => total inertness
    pg, e1 = make_page(b, cfg=False)
    st = pg.evaluate("() => ({ mod: typeof window.__abdoPush, os: typeof window.OneSignal })")
    check('1a: no config -> module never initialises, app unchanged', st['mod'] == 'undefined', st['mod'])
    check('1b: OneSignal page SDK still loads (any failure is ours, not theirs)', st['os'] in ('object', 'function'), st['os'])
    check('1c: no JS errors on the inert path', not clean(e1), clean(e1)[:2])
    pg.close()

    # 2) config present: reads it, says nothing, and the real SDK rejects the foreign origin
    pg, e2 = make_page(b)
    st2 = pg.evaluate("""() => ({ mod: typeof window.__abdoPush,
        state: window.__abdoPush ? window.__abdoPush.state() : null,
        cfg: window.__abdoPush ? window.__abdoPush.cfg.appId : null,
        askOpen: !!document.getElementById('push-ask-modal'),
        perm: ('Notification' in window) ? Notification.permission : 'none' })""")
    check('2a: config read and appId recorded, still inert without opt-in',
          st2['mod'] == 'object' and st2['cfg'] == CFG['appId'] and st2['state'] == 'off', st2)
    check('2b: zero-annoyance: no modal and no native prompt on load',
          st2['askOpen'] is False and st2['perm'] == 'default', st2)
    check('2c: an unknown appId is contained (our client records it, the app never errors)',
          st2['mod'] == 'object' and not clean(e2), clean(e2)[:2])

    # 2d) the REAL Hostinger appId from a foreign origin: OneSignal's own site-origin refusal
    REAL = dict(CFG); REAL['appId'] = '1d96cd6b-a496-4572-adfa-e3e35fde235b'
    ctx4 = b.new_context(viewport={'width': 390, 'height': 844})
    ctx4.add_init_script(GEO)
    pg4 = ctx4.new_page()
    e5 = []
    pg4.on('pageerror', lambda e: e5.append('pageerror: ' + str(e)))
    pg4.on('console', lambda m: e5.append('console.error: ' + m.text) if m.type == 'error' else None)
    pg4.route('**/push-config.json', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(REAL)))
    pg4.route(ALADHAN, lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({"code": 200, "data": {"timings": TIMINGS}})))
    pg4.goto(URL + '?pushApp=1', wait_until='load', timeout=45000)
    pg4.wait_for_timeout(3500)
    refused = [e for e in e5 if 'Can only be used on' in e]
    ours = [e for e in e5 if 'Can only be used on' not in e and not any(n in e for n in NOISE)]
    check('2d: the real appId is bound to its origin - OneSignal refuses ours, loudly',
          bool(refused), refused[0][:88] if refused else [e[:70] for e in e5][:2])
    check('2e: that refusal stays inside OneSignal - nothing ABDO-side throws', not ours, ours[:2])

    # 3) schedule built from the app's own data
    sched = pg.evaluate("""() => {
        const before = window.__abdoPush.buildEvents();
        const d = new Date(Date.now()+30*60000);
        const iso = d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);
        const hhmm = ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2);
        tasks.push({ text:'Push test task', completed:false, done:false, due_date:iso, due_time:hhmm,
                     reminder_minutes:15, reminder_fired:false });
        const ev2 = window.__abdoPush.buildEvents();
        return { before: before.length, afterTask: ev2.length,
                 taskEvents: ev2.filter(e=>e.id.indexOf('t:')===0),
                 prayerEvents: ev2.filter(e=>e.id.indexOf('p:')===0),
                 past: ev2.filter(e=>e.send_at <= Date.now()/1000 - 120).length,
                 futureOk: ev2.every(e=>e.send_at > Date.now()/1000 - 120), sample: ev2[0] };
    }""")
    check('3a: 7 days x 5 prayers, minus the ones already past today',
          25 <= sched['before'] <= 35, f"prayer events={sched['before']}")
    check('3b: a task with a reminder adds exactly one event', len(sched['taskEvents']) == 1, sched['taskEvents'])
    check('3c: nothing dated in the past can surprise someone at 3am', sched['futureOk'] is True and sched['past'] == 0, f"past={sched['past']}")
    check('3d: event shape matches what the sender reads',
          all(k in sched['sample'] for k in ('id', 'send_at', 'title', 'body')), json.dumps(sched['sample'])[:110])
    check('5b: the real-SDK path raised no app error', not clean(e2), clean(e2)[:2])

    # 4) declines are remembered
    pg.evaluate("() => { window.__abdoPush.markInterested(); }")
    pg.evaluate("() => { window.abdoPushLater(); }")
    time.sleep(0.2)
    sn = pg.evaluate("() => ({ modal: !!document.getElementById('push-ask-modal'), snooze: localStorage.getItem('alfaz_push_snooze') })")
    check('4a: "Maybe later" closes and stores a snooze', sn['modal'] is False and bool(sn['snooze']), sn)
    pg.evaluate("() => { window.abdoPushNever(); }")
    check('4b: "No thanks" persists as off', pg.evaluate("() => window.__abdoPush.state()") == 'off')

    # 5) no fake success when OneSignal cannot subscribe here
    pg2 = None
    acc = pg.evaluate("""() => new Promise(r => { window.abdoPushAccept();
        setTimeout(() => r({ state: window.__abdoPush.state(), player: localStorage.getItem('alfaz_push_player') }), 2000); })""")
    check('5a: no fake success when OneSignal cannot subscribe', acc['state'] != 'on' or not acc['player'], acc)

    # 6) mocked SDK: our init args, opt-in, player capture, the POST
    pg2, e3 = make_page(b, cfg=True, mock=True)
    m = pg2.evaluate("""() => ({ init: window.__initCalls[0]||{}, ran: !!window.__deferredRan, err: window.__initError||null })""")
    check('6a: init runs via OneSignalDeferred with appId + isolated worker path',
          m['init'].get('appId') == 'test-app-id' and 'push/onesignal' in str(m['init'].get('serviceWorkerPath')) and m['ran'] is True,
          json.dumps({k: m['init'].get(k) for k in ('appId', 'serviceWorkerPath')})[:150])
    check('6b: autoPrompt false and welcome notification disabled (our two rules)',
          m['init'].get('autoPrompt') is False and m['init'].get('welcomeNotification', {}).get('disable') is True,
          sorted(m['init'].keys()))
    pg2.evaluate("() => { const el=document.getElementById('plan-reminder'); if (el) { el.value='15'; } }")
    pg2.evaluate("() => window.abdoPushAccept()")
    pg2.wait_for_timeout(1800)
    aft = pg2.evaluate("""() => ({ state: window.__abdoPush.state(), optIn: window.__optIn,
        player: localStorage.getItem('alfaz_push_player'),
        sync: (window.__syncBodies||[]).map(b => JSON.parse(b)) })""")
    check('6c: accepting opts in exactly once and flips state to on',
          aft['state'] == 'on' and aft['optIn'] == 1, {k: aft[k] for k in ('state', 'optIn')})
    check('6d: player id captured for targeted sends', aft['player'] == 'player-mock-1', aft['player'])
    first_sync = aft['sync'][0] if aft['sync'] else {}
    ok_sync = all(k in first_sync for k in ('uid', 'token', 'player', 'events')) and len(first_sync.get('events', [])) > 0
    check('6e: one schedule POST reaches the sender with uid + token + player + events', ok_sync,
          json.dumps({k: v for k, v in first_sync.items() if k != 'events'} | {'events_n': len(first_sync.get('events', []))})[:175] if aft['sync'] else 'no POST')
    check('6f: no JS errors with the mocked SDK', not clean(e3), clean(e3)[:2])

    # 7) the ask is earned, and one-shot
    pg3, e4 = make_page(b, cfg=True, mock=True)
    pg3.evaluate("() => localStorage.clear()")
    pg3.reload(wait_until='load'); pg3.wait_for_timeout(1800)
    bare = pg3.evaluate("() => ({ modal: !!document.getElementById('push-ask-modal'), decided: !!localStorage.getItem('alfaz_push_state') })")
    check('7a: a brand-new visitor is not asked, and not recorded as refusing',
          bare['modal'] is False and bare['decided'] is False, bare)
    earned = pg3.evaluate("""() => { window.__abdoPush.markInterested();
        return { modal: !!document.getElementById('push-ask-modal'), perm: Notification.permission }; }""")
    check('7b: asking is still refused until the user has a reminder of their own', earned['modal'] is False, earned)
    pg3.evaluate("() => { tasks.push({ text:'x', done:false, due_date:'2026-09-11', due_time:'20:00', reminder_minutes:15 }); window.__abdoPush.markInterested(); }")
    txt = pg3.evaluate("() => { const m=document.getElementById('push-ask-modal'); return m ? m.innerText.replace(/\\s+/g,' ').slice(0,160) : ''; }")
    perm_now = pg3.evaluate("() => Notification.permission")
    check('7c: with a reminder set, the soft-ask opens and the native dialog is untouched',
          bool(txt) and perm_now in ('default', 'granted'), f"modal={txt[:60]!r} perm={perm_now}")
    again = pg3.evaluate("""() => { window.abdoPushLater(); window.__abdoPush.markInterested();
        return !!document.getElementById('push-ask-modal'); }""")
    check('7d: someone who says "later" is never re-asked', again is False, again)
    b.close()

import urllib.request
def get(path):
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:{PORT}{path}', timeout=5); return r.status, r.read()
    except Exception as e:
        return getattr(e, 'code', 0), b''

c1, b1 = get('/push/onesignal/OneSignalSDKWorker.js')
check('8a: OneSignal worker served from our subdirectory, never the root', c1 == 200 and b'importScripts' in b1, f"HTTP {c1}")
c2, b2 = get('/push-config.json')
check('8b: committed config carries the public appId and an empty writeToken',
      c2 == 200 and b'1d96cd6b' in b2 and b'"writeToken": ""' in b2, f"HTTP {c2}")
c3, b3 = get('/sw.js')
check('8c: our own worker still owns the root scope', c3 == 200 and b'alfaz-todo-v41' in b3, f"HTTP {c3}")
src_txt = open(f'{REPO}/index.html', encoding='utf-8').read()
check('8d: index.html loads OneSignal + the client, both deferred (no render block)',
      'OneSignalSDK.page.js" defer' in src_txt and 'push/client.js" defer' in src_txt)
check('8e: push files are served, and nothing sensitive is in the committed config',
      b'1d96cd6b' in b2 and b'REST' not in b2 and b'push-config.php' in open(f'{REPO}/.gitignore', 'rb').read())

srv_proc.send_signal(signal.SIGTERM)
try: srv_proc.wait(timeout=5)
except Exception: srv_proc.kill()
p = sum(1 for c in res if c)
print(f"\nSUMMARY: {p}/{len(res)} passed")
sys.exit(0 if p == len(res) else 1)
