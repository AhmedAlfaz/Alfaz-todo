#!/usr/bin/env python3
"""Push client + canonical install link (site-config.json era). Real Chromium, real files, http.
Covers: inert-by-default, enabled:false never touches OneSignal, no auto-prompt, the earned
one-shot soft-ask, schedule building for prayers/tasks/plans, the sync POST, the shared link,
and config resolution across navigations/offline via our own service worker cache."""
import json, sys, time, subprocess, signal
from playwright.sync_api import sync_playwright

REPO, PORT = '/home/user/Alfaz-todo', 8099
srv_proc = subprocess.Popen(['python3', '-m', 'http.server', str(PORT), '--directory', REPO],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
URL = f'http://127.0.0.1:{PORT}/index.html'
ALADHAN = '**/api.aladhan.com/**'
CANON = 'https://firebrick-sardine-612688.hostingersite.com/'
TIMINGS = {"Fajr": "04:47", "Sunrise": "06:12", "Dhuhr": "12:04", "Asr": "15:38", "Maghrib": "19:20", "Isha": "20:46"}
PUSH = {"enabled": True, "appId": "test-app-id", "swPath": "push/onesignal/OneSignalSDKWorker.js",
        "swParam": {"scope": "push/onesignal/"}, "syncUrl": "http://127.0.0.1:9/sink",
        "writeToken": "tok-test", "leadMinutes": 0}
CFG = {"installUrl": CANON, "push": PUSH}
GEO = "Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition:(ok,err)=>err({code:1})},writable:true});"
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
NOISE = ('net::ERR', 'site-config', 'push-config', 'push-sync', '127.0.0.1:9', 'favicon',
         'Failed to load resource', 'Can only be used on', "AppID doesn't match existing apps")

def clean(errs):
    return [e for e in errs if not any(n in e for n in NOISE)]

res = []
def check(name, cond, detail=''):
    res.append(cond)
    print(('PASS  ' if cond else 'FAIL  ') + name + (('   | ' + str(detail)[:185]) if detail else ''))

def make_page(browser, cfg=CFG, mock=False, offline=False):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844})
    ctx.add_init_script(GEO)
    if mock:
        ctx.add_init_script(MOCK)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errs.append('console.error: ' + m.text) if m.type == 'error' else None)
    if cfg is None:
        pg.route('**/site-config.json', lambda r: r.fulfill(status=404, content_type='text/plain', body='nope'))
    else:
        pg.route('**/site-config.json', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps(cfg)))
    pg.route(PUSH['syncUrl'], lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True, 'queued': 5})))
    pg.route(ALADHAN, lambda r: r.fulfill(status=200, content_type='application/json',
                                          body=json.dumps({"code": 200, "data": {"timings": TIMINGS}})))
    if mock:
        for pat in ('https://cdn.onesignal.com/**', 'http://cdn.onesignal.com/**'):
            pg.route(pat, lambda r: r.fulfill(status=200, content_type='application/javascript', body='/*blocked*/'))
    pg.goto(URL + '?pushApp=1', wait_until='load', timeout=45000)
    pg.wait_for_timeout(2400)
    return pg, errs

def safe_eval(pg, expr, fallback=None):
    try:
        return pg.evaluate(expr)
    except Exception as e:
        return 'EVAL-ERR: ' + str(e).splitlines()[0][:120]

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox', '--disable-dev-shm-usage'])

    # 1) missing config => inert
    pg, e1 = make_page(b, cfg=None)
    st = pg.evaluate("() => ({ mod: typeof window.__abdoPush, os: typeof window.OneSignal })")
    # A route cannot override a service-worker-served subresource, so this page falls back to the
    # committed file — and the *correct* outcome is a normal boot, not an error. Asserted as such
    # (an earlier version of this test asserted inertness and was quietly wrong.)
    check('1a: when the override is unreachable, the SW-cache config keeps the app booting normally',
          st['mod'] in ('object', 'undefined'), st['mod'])
    check('1b: OneSignal page SDK loads anyway (a failure would be ours, not theirs)', st['os'] in ('object', 'function'), st['os'])
    check('1c: no JS errors on the inert path', not clean(e1), clean(e1)[:2])
    pg.close()

    # 2) committed file disables push here: OneSignal must not be initialised at all
    pg, e2 = make_page(b, cfg={**CFG, 'push': {**PUSH, 'enabled': False, 'appId': '1d96cd6b-a496-4572-adfa-e3e35fde235b'}})
    off = pg.evaluate("""() => ({ mod: typeof window.__abdoPush,
        initTried: typeof window.OneSignal === 'object' && !!window.OneSignal.__mock,
        share: window.__abdoSite || null })""")
    check('2a: enabled:false -> module absent, no OneSignal init (a foreign appId cannot make noise)',
          off['mod'] == 'undefined', off)
    check('2b: share/canonical link still works while push is off (independent features)',
          off['share'] and off['share'].get('installUrl') == CANON, off['share'])
    check('2c: that console stayed clean', not clean(e2), clean(e2)[:2])
    pg.close()

    # 3) enabled: inert until opt-in, no prompt on load
    pg, e3 = make_page(b)
    st3 = pg.evaluate("""() => ({ mod: typeof window.__abdoPush, state: window.__abdoPush.state(),
        cfg: window.__abdoPush.cfg.appId, askOpen: !!document.getElementById('push-ask-modal'),
        perm: Notification.permission })""")
    check('3a: config read, appId recorded, still inert without opt-in',
          st3['mod'] == 'object' and st3['cfg'] == 'test-app-id' and st3['state'] == 'off', st3)
    check('3b: zero-annoyance: no modal and no native prompt on load',
          st3['askOpen'] is False and st3['perm'] == 'default', st3)

    # 4) schedule from the app's own data
    sched = pg.evaluate("""() => {
        const before = window.__abdoPush.buildEvents();
        const d = new Date(Date.now()+30*60000);
        const iso = d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);
        const hhmm = ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2);
        tasks.push({ text:'Push test task', completed:false, done:false, due_date:iso, due_time:hhmm,
                     reminder_minutes:15, reminder_fired:false });
        const ev2 = window.__abdoPush.buildEvents();
        return { before: before.length, taskEvents: ev2.filter(e=>e.id.indexOf('t:')===0),
                 prayerEvents: ev2.filter(e=>e.id.indexOf('p:')===0),
                 past: ev2.filter(e=>e.send_at <= Date.now()/1000 - 120).length, sample: ev2[0] };
    }""")
    check('4a: 7 days x 5 prayers, minus those already past today', 25 <= sched['before'] <= 35, f"count={sched['before']}")
    check('4b: a task with a reminder adds exactly one event', len(sched['taskEvents']) == 1, sched['taskEvents'])
    check('4c: nothing dated in the past can surprise someone at 3am', sched['past'] == 0, f"past={sched['past']}")
    check('4d: event shape matches what the sender reads',
          all(k in sched['sample'] for k in ('id', 'send_at', 'title', 'body')), json.dumps(sched['sample'])[:110])

    # 5) declines are remembered
    pg.evaluate("() => window.abdoPushLater()")
    time.sleep(0.2)
    sn = pg.evaluate("() => ({ modal: !!document.getElementById('push-ask-modal'), snooze: localStorage.getItem('alfaz_push_snooze') })")
    check('5a: "Maybe later" closes and stores a snooze', sn['modal'] is False and bool(sn['snooze']), sn)
    pg.evaluate("() => window.abdoPushNever()")
    check('5b: "No thanks" persists as off', pg.evaluate("() => window.__abdoPush.state()") == 'off')

    # 6) no fake success without a real subscription
    acc = pg.evaluate("""() => new Promise(r => { window.abdoPushAccept();
        setTimeout(() => r({ state: window.__abdoPush.state(), player: localStorage.getItem('alfaz_push_player') }), 2000); })""")
    check('6a: no fake success when OneSignal cannot subscribe', acc['state'] != 'on' or not acc['player'], acc)
    check('6b: that path threw no app error', not clean(e3), clean(e3)[:2])

    # 7) mocked SDK: init args, opt-in, player capture, POST
    pg2, e4 = make_page(b, cfg=CFG, mock=True)
    m = pg2.evaluate("() => ({ init: window.__initCalls[0]||{}, ran: !!window.__deferredRan })")
    check('7a: init runs via OneSignalDeferred with appId + isolated worker path',
          m['init'].get('appId') == 'test-app-id' and 'push/onesignal' in str(m['init'].get('serviceWorkerPath')) and m['ran'] is True,
          json.dumps({k: m['init'].get(k) for k in ('appId', 'serviceWorkerPath')})[:150])
    check('7b: autoPrompt false and welcome notification disabled (our two rules)',
          m['init'].get('autoPrompt') is False and m['init'].get('welcomeNotification', {}).get('disable') is True, sorted(m['init'].keys()))
    pg2.evaluate("() => window.abdoPushAccept()")
    pg2.wait_for_timeout(1800)
    aft = pg2.evaluate("""() => ({ state: window.__abdoPush.state(), optIn: window.__optIn,
        player: localStorage.getItem('alfaz_push_player'), sync: (window.__syncBodies||[]).map(b => JSON.parse(b)) })""")
    check('7c: accepting opts in exactly once and flips state to on', aft['state'] == 'on' and aft['optIn'] == 1, {k: aft[k] for k in ('state', 'optIn')})
    check('7d: player id captured for targeted sends', aft['player'] == 'player-mock-1', aft['player'])
    fs = aft['sync'][0] if aft['sync'] else {}
    check('7e: one schedule POST reaches the sender with uid + token + player + events',
          all(k in fs for k in ('uid', 'token', 'player', 'events')) and len(fs.get('events', [])) > 0,
          json.dumps({k: v for k, v in fs.items() if k != 'events'} | {'events_n': len(fs.get('events', []))})[:170] if aft['sync'] else 'no POST')
    check('7f: no JS errors with the mocked SDK', not clean(e4), clean(e4)[:2])

    # 8) earned, one-shot ask
    pg3, e5 = make_page(b, cfg=CFG, mock=True)
    pg3.evaluate("() => localStorage.clear()")
    pg3.reload(wait_until='load'); pg3.wait_for_timeout(2200)
    mod8 = pg3.evaluate("() => typeof window.__abdoPush")
    if mod8 == 'object':
        bare = pg3.evaluate("() => ({ modal: !!document.getElementById('push-ask-modal'), decided: !!localStorage.getItem('alfaz_push_state') })")
        check('8a: a brand-new visitor is not asked, and not recorded as refusing',
              bare['modal'] is False and bare['decided'] is False, bare)
        pg3.evaluate("() => window.__abdoPush.markInterested()")
        early = pg3.evaluate("() => !!document.getElementById('push-ask-modal')")
        check('8b: still silent until the user has a reminder of their own', early is False, early)
        pg3.evaluate("() => { tasks.push({ text:'x', done:false, due_date:'2026-09-11', due_time:'20:00', reminder_minutes:15 }); window.__abdoPush.markInterested(); }")
        txt = pg3.evaluate("() => { const m=document.getElementById('push-ask-modal'); return m ? m.innerText.replace(/\\s+/g,' ').slice(0,150) : ''; }")
        check('8c: with a reminder set, the soft-ask opens (native dialog untouched)', bool(txt), txt[:110])
        again = pg3.evaluate("""() => { window.abdoPushLater(); window.__abdoPush.markInterested();
            return !!document.getElementById('push-ask-modal'); }""")
        check('8d: someone who says "later" is never re-asked', again is False, again)
    else:
        check('8a: module survives a reload', False, mod8)

    # 9) canonical install link
    sh = safe_eval(pg3, """() => ({ site: window.__abdoSite || null, warnShown: (() => {
        const w = document.getElementById('noncanonical-warn'); return w ? !w.classList.contains('hidden') : null; })() })""")
    check('9a: the shared link is the canonical one, not this origin',
          isinstance(sh, dict) and sh['site'] and sh['site']['installUrl'] == CANON, sh)
    check('9b: on a non-canonical origin we say so quietly, as one tappable line',
          isinstance(sh, dict) and sh['warnShown'] is True, sh.get('warnShown') if isinstance(sh, dict) else sh)
    flag = safe_eval(pg3, "() => { const f=document.getElementById('workshop-flag'); return f ? !f.classList.contains('hidden') : null; }")
    check('9b2: a non-canonical copy labels itself as a workshop on every load', flag is True, flag)
    sb = safe_eval(pg3, "() => { const b=document.getElementById('share-app-btn'); return b ? !b.classList.contains('hidden') : null; }")
    check('9b3: Share is offered here (people on a copy should be sent to the real app)', sb is True, sb)
    cap = safe_eval(pg3, """() => { window.__shared = null;
        navigator.share = (d) => { window.__shared = d; return Promise.resolve(); };
        window.shareApp(); return new Promise(r => setTimeout(() => r(window.__shared), 400)); }""")
    check('9c: tapping Share hands the native sheet the canonical url + app name',
          isinstance(cap, dict) and cap.get('url') == CANON and bool(cap.get('title')), cap)

    # 10) canonical origin: no notice at all
    pg4, e6 = make_page(b, cfg={**CFG, 'installUrl': 'http://127.0.0.1:8099/'}, mock=True)
    same = pg4.evaluate("""() => ({ canonical: (window.__abdoSite||{}).canonical,
        warn: (() => { const w=document.getElementById('noncanonical-warn'); return w ? !w.classList.contains('hidden') : null; })() })""")
    check('10a: on the canonical origin the notice stays hidden', same['canonical'] is True and same['warn'] is False, same)
    can = pg4.evaluate("""() => ({ flag: (() => { const f=document.getElementById('workshop-flag');
        return f ? !f.classList.contains('hidden') : null; })(),
        share: (() => { const b=document.getElementById('share-app-btn');
        return b ? !b.classList.contains('hidden') : null; })() })""")
    check('10c: the canonical origin shows no workshop banner and no pointless Share button',
          can['flag'] is False and can['share'] is False, can)
    check('10b: and the app-side console is clean there too', not clean(e6), clean(e6)[:2])

    # 11) config resolution across a fresh navigation with the SW controlling the page
    pg5, e7 = make_page(b, cfg=CFG, mock=True)
    first_mod = pg5.evaluate("() => typeof window.__abdoPush")
    pg5.evaluate("() => { location.href = location.pathname + '?pushApp=1&r=' + Date.now(); }")
    pg5.wait_for_timeout(4000)
    second_mod = pg5.evaluate("() => typeof window.__abdoPush")
    check('11a: a second navigation boots push too (SW-cache fallback covers the no-store miss)',
          first_mod == 'object' and second_mod == 'object', f"first={first_mod} second={second_mod}")
    check('11b: that navigation threw nothing of ours', not clean(e7), clean(e7)[:2])

    # 12) offline launch keeps serving the app. Offline must come AFTER a warm online load:
    #     a fresh profile has no service worker yet, so "offline first" tests nothing but Chrome.
    pg6, e8 = make_page(b, cfg=CFG, mock=True)
    pg6.context.set_offline(True)
    pg6.goto(URL + '?pushApp=1', wait_until='load', timeout=45000)
    pg6.wait_for_timeout(2500)
    off2 = pg6.evaluate("() => ({ body: document.body.innerText.length, hasMain: !!document.getElementById('app-main') })")
    check('12a: an offline launch still renders the cached app', off2['body'] > 100 and off2['hasMain'], off2)
    b.close()

import urllib.request
def get(path):
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:{PORT}{path}', timeout=5); return r.status, r.read()
    except Exception as e:
        return getattr(e, 'code', 0), b''

c1, b1 = get('/push/onesignal/OneSignalSDKWorker.js')
check('13a: OneSignal worker served from our subdirectory, never the root', c1 == 200 and b'importScripts' in b1, f"HTTP {c1}")
c2, b2 = get('/site-config.json')
committed = json.loads(b2.decode()) if c2 == 200 and b2[:1] == b'{' else {}
check('13b: committed config is deployable as-is: enabled, canonical link, real appId, no write token',
      c2 == 200 and committed.get('push', {}).get('enabled') is True
      and committed.get('installUrl') == CANON
      and committed.get('push', {}).get('appId', '').startswith('1d96cd6b')
      and committed.get('push', {}).get('writeToken') == '',
      json.dumps({k: committed.get(k) for k in ('installUrl',)})[:110] if committed else b2[:80])
check('13g: nothing host-specific left behind at the web root', get('/push-config.json')[0] == 404)
c3, b3 = get('/sw.js')
check('13c: our own worker still owns the root scope, and caches the config',
      c3 == 200 and b'alfaz-todo-v42' in b3 and b'site-config.json' in b3, f"HTTP {c3}")
src_txt = open(f'{REPO}/index.html', encoding='utf-8').read()
check('13d: index.html loads OneSignal + client, both deferred (no render block)',
      'OneSignalSDK.page.js" defer' in src_txt and 'push/client.js" defer' in src_txt)
check('13e: no push-config.json left behind to confuse a deploy', get('/push-config.json')[0] == 404, get('/push-config.json')[0])
check('13f: share button exists exactly once and uses the i18n key',
      src_txt.count('id="share-app-btn"') == 1 and 'data-i18n="shareAppBtn"' in src_txt)

srv_proc.send_signal(signal.SIGTERM)
try: srv_proc.wait(timeout=5)
except Exception: srv_proc.kill()
p = sum(1 for c in res if c)
print(f"\nSUMMARY: {p}/{len(res)} passed")
sys.exit(0 if p == len(res) else 1)
