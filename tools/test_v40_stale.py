#!/usr/bin/env python3
"""Deterministic real-browser verification of the v40 prayer-times staleness patch.
The app fetches at boot by itself, so every scenario: blocks geolocation (no boot fetch),
mocks or aborts Aladhan, seeds the cache, then calls fetchPrayerTimes exactly once."""
import json, threading, http.server, sys, time, datetime
from playwright.sync_api import sync_playwright

APP, PORT = '/home/user/Alfaz-todo', 8138
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=APP, **k)
    def log_message(self, *a): pass
srv = http.server.HTTPServer(('127.0.0.1', PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'

# exactly the 5 keys the app persists (line 2524)
TIMINGS = {"Fajr":"04:47","Dhuhr":"12:04","Asr":"15:38","Maghrib":"19:20","Isha":"20:46"}
DS = datetime.date.today().strftime('%d-%m-%Y')
KEY = f'alfatore_prayers_{DS}'
MOCK = json.dumps({"code":200,"status":"OK","data":{"timings":{**TIMINGS,"Sunrise":"06:12"}}})
GEO = "Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition:(ok,err)=>err({code:1})},writable:true});"

def seed_js(payload):
    return f"localStorage.clear(); localStorage.setItem({json.dumps(KEY)}, {json.dumps(json.dumps(payload))});"

def scenario(browser, payload=None, lang='en', net='abort'):
    ctx = browser.new_context(viewport={'width':390,'height':844}, locale=lang)
    init = GEO
    if payload is not None: init += seed_js(payload)
    if lang == 'ar': init += "localStorage.setItem('alfatore_lang','ar');"
    ctx.add_init_script(init)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append('console.error: '+m.text) if m.type == 'error' else None)
    if net == 'abort':
        pg.route("**/api.aladhan.com/**", lambda r: r.abort())
    else:
        pg.route("**/api.aladhan.com/**", lambda r: r.fulfill(status=200, content_type='application/json', body=MOCK))
    pg.goto(URL, wait_until='domcontentloaded', timeout=30000)
    pg.evaluate("try { fetchPrayerTimes(27.2574, 33.8108); } catch(e) {}")
    pg.wait_for_timeout(2500)
    st = pg.evaluate("""() => {
      const el = document.getElementById('prayer-freshness');
      return { hasEl: !!el, hidden: el ? el.classList.contains('hidden') : null,
               text: el ? (el.textContent||'').trim() : null,
               cards: document.querySelectorAll('#prayer-cards .prayer-card').length,
               keys: Object.keys(window.prayerTimings||{}).sort().join(','),
               lang: window.currentLang, dir: document.documentElement.dir };
    }""")
    st['saved'] = pg.evaluate(f"""() => {{ try {{ return JSON.parse(localStorage.getItem({json.dumps(KEY)})); }} catch(e) {{ return 'RAW:'+localStorage.getItem({json.dumps(KEY)}); }} }}""")
    st['errs'] = [e for e in errs if 'net::ERR_FAILED' not in e and 'Failed to load resource' not in e]
    ctx.close()
    return st

res = []
def check(name, cond, detail=""):
    res.append(cond)
    print(("PASS  " if cond else "FAIL  ") + name + (("   | " + str(detail)[:180]) if detail else ""))

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-dev-shm-usage'])

    # A: stale v2 cache + offline -> warn with the true age, cards from cache
    A = scenario(b, {"v":2,"cached_at":int(time.time()*1000)-20*3600*1000,"date_key":DS,"timings":TIMINGS}, net='abort')
    print("  A:", {k:A[k] for k in ('hidden','text','cards','keys')})
    check("A: stale cache warns instead of passing as current", A['hidden'] is False and '~20h old' in (A['text'] or ''), A['text'])
    check("A: cached prayer cards still render (5, no Sunrise)", A['cards'] == 5, f"cards={A['cards']} keys={A['keys']}")

    # B: fresh cache -> silent
    B = scenario(b, {"v":2,"cached_at":int(time.time()*1000)-5*60*1000,"date_key":DS,"timings":TIMINGS}, net='abort')
    print("  B:", {k:B[k] for k in ('hidden','cards')})
    check("B: recent cache stays silent (no nagging)", B['hidden'] is True, f"hidden={B['hidden']}")

    # C: legacy v39 shape (bare object, no metadata) -> renders + flagged as untrusted
    C = scenario(b, TIMINGS, net='abort')
    print("  C:", {k:C[k] for k in ('hidden','text','cards','keys')})
    check("C: pre-v40 cache format still renders 5 cards", C['cards'] == 5, f"cards={C['cards']} keys={C['keys']}")
    check("C: legacy data with no timestamp is flagged, never trusted silently",
          C['hidden'] is False and 'earlier day' in (C['text'] or ''), C['text'])

    # D: Arabic
    D = scenario(b, {"v":2,"cached_at":int(time.time()*1000)-20*3600*1000,"date_key":DS,"timings":TIMINGS}, lang='ar', net='abort')
    print("  D:", {k:D[k] for k in ('hidden','text','lang','dir')})
    check("D: warning is Arabic, not an EN fallback",
          D['hidden'] is False and 'أوقات' in (D['text'] or '') and 'ساعة' in (D['text'] or ''), D['text'])
    check("D: RTL still applied", D['dir'] == 'rtl', D['dir'])

    # E: online success -> v2 written, warning disappears
    E = scenario(b, {"v":2,"cached_at":int(time.time()*1000)-30*3600*1000,"date_key":DS,"timings":TIMINGS}, net='ok')
    saved = E['saved'] if isinstance(E['saved'], dict) else {}
    print("  E:", {k:E[k] for k in ('hidden','cards')}, "saved.v=", saved.get('v'))
    check("E: successful fetch persists the new v2 shape", saved.get('v') == 2 and saved.get('timings',{}).get('Fajr')=='04:47', json.dumps(saved, ensure_ascii=False)[:120])
    check("E: fresh server data clears the warning", E['hidden'] is True, f"hidden={E['hidden']}")

    allerrs = sum([s['errs'] for s in (A,B,C,D,E)], [])
    check("no JS errors in any scenario", not allerrs, allerrs[:3])
    b.close()

srv.shutdown()
passed = sum(1 for c in res if c)
print(f"\nSUMMARY: {passed}/{len(res)} passed")
sys.exit(0 if passed == len(res) else 1)
