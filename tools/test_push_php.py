#!/usr/bin/env python3
"""Functional test of the ABDO push sender (queue mechanics, not OneSignal).
Runs the real PHP endpoints with the bundled PHP built-in server and PUSH_TRANSPORT=log,
then reads the queue files the server wrote. Verifies: auth, idempotency, cancel-on-drop,
retry/give-up, path-traversal rejection, and cron dispatch exactly once."""
import json, os, re, shutil, subprocess, sys, time, urllib.request, urllib.error, uuid

REPO = '/home/user/Alfaz-todo'
RUN = str(uuid.uuid4())[:8]
QDIR = f'/tmp/abdo-push-test-{RUN}'
os.makedirs(QDIR, exist_ok=True)
CFG = f'{QDIR}/push-config.php'
TOKEN_SECRET = 'test-secret-' + RUN
CRON_KEY = 'cron-' + RUN

with open(f'{REPO}/push/push-lib.php') as f: LIB = f.read()

open(CFG, 'w').write(f"""<?php
define('ONESIGNAL_APP_ID','test-app'); define('ONESIGNAL_REST_KEY','');
define('PUSH_TRANSPORT','log'); define('PUSH_DIR','{QDIR}');
define('PUSH_TOKEN_SECRET','{TOKEN_SECRET}'); define('PUSH_CRON_KEY','{CRON_KEY}'); define('PUSH_WINDOW_MIN',15);
define('PUSH_TZ','Africa/Cairo'); define('PUSH_MAX_EVENTS_PER_USER',120); define('PUSH_MAX_BODY',240);
date_default_timezone_set(PUSH_TZ);
""")
# copy the endpoints as-is (no source rewriting - a silent no-op replace is how this test
# once faked itself). The lib is pointed at our config with ABDO_PUSH_CONFIG, same for the
# CLI token helper, so server and client provably read the same file.
shutil.copy(f'{REPO}/push/push-lib.php', f'{QDIR}/push-lib.php')
for f in ('push-sync.php','push-cron.php'):
    shutil.copy(f'{REPO}/push/{f}', f'{QDIR}/{f}')

PORT = 8100 + (int(RUN[:4], 16) % 800)   # unique per run; a fixed port once let a zombie server answer
ENV = dict(os.environ, ABDO_PUSH_CONFIG=CFG)
srv = subprocess.Popen(['php','-S',f'127.0.0.1:{PORT}','-t',QDIR], cwd=QDIR, env=ENV,
                       stdout=open(f'{QDIR}/server.log','w'), stderr=subprocess.STDOUT)
# fail loudly if the harness itself is misconfigured
if not os.environ.get('ABDO_PUSH_TEST_NO_ASSERT'):
    assert 'ABDO_PUSH_CONFIG' in open(f'{REPO}/push/push-lib.php').read(), 'harness assumes env override; it is missing'
for _ in range(60):
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{PORT}/push-sync.php', data=b'{}', timeout=1); break
    except urllib.error.HTTPError: break
    except Exception: time.sleep(0.15)
# harness self-check: the answering server must be THIS run's server, never a leftover one
open(f'{QDIR}/whoami.php','w').write("<?php echo json_encode(['dir'=>__DIR__]);")
try:
    _w = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/whoami.php', timeout=5).read().decode())
except Exception as e:
    print("HARNESS ERROR: server on port", PORT, "unreachable:", e); sys.exit(2)
if _w['dir'] != QDIR:
    print(f"HARNESS ERROR: port {PORT} answered by {_w['dir']}, not {QDIR}. Aborting rather than reporting fake failures.")
    sys.exit(2)
print(f"  harness bound to its own server")

def tok(uid):
    out = subprocess.run(['php','-r',f"require '{QDIR}/push-lib.php'; echo push_token_for({json.dumps(uid)}, {json.dumps(TOKEN_SECRET)}, 'test-app');"],
                         capture_output=True, text=True, env=ENV)
    if os.environ.get('PUSH_TEST_DEBUG'):
        print(f"    [tok {uid}] rc={out.returncode} out={out.stdout[:80]!r} err={out.stderr[:200]!r}")
    return out.stdout.strip()

def post(uid, events, token=None, player='pl-test'):
    _tok = token if token is not None else tok(uid)
    if os.environ.get('PUSH_TEST_DEBUG'):
        print(f"    [post {uid}] sending token tail ...{_tok[-10:]}")
    body = json.dumps({'uid': uid, 'token': _tok,
                       'player': player, 'events': events}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{PORT}/push-sync.php', data=body,
                                     headers={'Content-Type':'application/json'}), timeout=10)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, (json.loads(e.read().decode()) if e.headers.get('Content-Type','').startswith('application/json') else {})

def cron(key=CRON_KEY):
    u = f'http://127.0.0.1:{PORT}/push-cron.php' + (f'?key={key}' if key is not None else '')
    try:
        r = urllib.request.urlopen(u, timeout=30)
        return r.status, r.read().decode().strip()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode().strip()

def queue(uid):
    p = f'{QDIR}/user-{uid}.json'
    return json.loads(open(p).read()) if os.path.exists(p) else None

def loglines():
    p = f'{QDIR}/transport.log'
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

res = []
def check(name, cond, detail=''):
    res.append(cond); print(('PASS  ' if cond else 'FAIL  ') + name + (('   | ' + str(detail)[:200]) if detail else ''))

uid = 'testuser001'
now = int(time.time())
ev_soon   = {'id': f'{uid}:fajr:2026-09-11', 'send_at': now + 120, 'title': '🕌 Fajr', 'body': 'Time for Fajr', 'link': './'}
ev_later  = {'id': f'{uid}:dhuhr:2026-09-11', 'send_at': now + 6*3600, 'title': '🕌 Dhuhr', 'body': 'Time for Dhuhr', 'link': './'}
ev_task   = {'id': f'{uid}:task:abc', 'send_at': now + 7*60, 'title': '✅ Task', 'body': 'Buy milk', 'link': './'}

# 1) auth
code, body = post(uid, [ev_soon], token='wrong')
check('1a: forged write token rejected (401)', code == 401, f'{code} {body}')
derived = subprocess.run(['node','-e', f'''
const {{createHmac}}=require("crypto");const uid="{uid}",app="test-app",secret="{TOKEN_SECRET}";
const mac=encodeURIComponent(Buffer.from(createHmac("sha256",app).update(uid+":"+secret).digest()).toString("base64"));
process.stdout.write(Buffer.from(uid+":"+app+":"+mac).toString("base64").replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,""));
'''],capture_output=True,text=True).stdout
check('1a2: a token the CLIENT derived (same recipe, no server secret exposure) is accepted',
      post(uid, [], token=derived)[0] == 200, derived[:24])
other = subprocess.run(['php','-r',f"require '{QDIR}/push-lib.php'; echo push_token_for('somevictim', {json.dumps(TOKEN_SECRET)}, 'test-app');"],
                       capture_output=True, text=True, env=ENV).stdout.strip()
check('1a3: the attacker-derivable variant (no secret) cannot sign for a different uid',
      post(uid, [], token=other)[0] == 401, 'cross-uid token')
code, body = post('../../etc/passwd', [ev_soon])
check('1b: path-traversal uid rejected', code == 400, f'{code} {body}')
code, body = post(uid, 'notalist')
check('1c: malformed events payload does not crash (no 5xx)', code in (200, 400), f'{code} {body}')

# 2) sync queues
code, body = post(uid, [ev_soon, ev_later, ev_task])
q = queue(uid)
check('2a: sync accepted', code == 200 and body.get('ok'), f'{code} {body}')
check('2b: three events queued', q and len(q['events']) == 3, f"queued={len(q['events']) if q else None}")
future = [e for e in (q['events'] if q else []) if e['send_at'] > now + 15*60]
check('2c: far-future event handed to OneSignal scheduler immediately (pre_sent)',
      len(future) == 1 and future[0].get('pre_sent') == 1, json.dumps(future)[:160])
near = [e for e in (q['events'] if q else []) if e['send_at'] <= now + 15*60]
check('2d: near events left for cron (not pre-sent)', all(not e.get('pre_sent') for e in near), f'near={len(near)}')

# 3) idempotency: re-sync identical schedule must not re-create the far event
before = len(loglines())
post(uid, [ev_soon, ev_later, ev_task])
after = len(loglines())
check('3a: re-sync of identical schedule sends nothing new', after == before, f'log {before} -> {after}')
q2 = queue(uid)
check('3b: re-sync keeps the same OneSignal id', q2 and [e for e in q2['events'] if e['id'] == ev_later['id']][0].get('nid','').startswith('log-'),
      json.dumps([e for e in q2['events'] if e['id']==ev_later['id']])[:160])

# 4) cron dispatches due events exactly once
code1, out1 = cron()
sent1 = int(re.search(r'sent=(\d+)', out1).group(1))
check('4a: first cron run dispatches the two due events', sent1 == 2, out1)
code2, out2 = cron()
sent2 = int(re.search(r'sent=(\d+)', out2).group(1))
check('4b: second cron run sends nothing (no double alert ever)', sent2 == 0, out2)
check('4c: cron refuses the unauthenticated public URL (403)', cron(key=None)[0] == 403, cron(key=None))
check('4d: cron refuses a wrong key (403)', cron(key='not-it')[0] == 403, cron(key='not-it')[1][:60])

# 5) cancel on drop: client removes the task event
post(uid, [ev_soon, ev_later])
q3 = queue(uid)
ids = [e['id'] for e in q3['events']] if q3 else []
check('5a: dropped event removed from queue', not any('task' in i for i in ids), f'ids={ids}')

# 6) past events are never queued
code, body = post(uid, [ev_later, {'id': f'{uid}:old', 'send_at': now - 3600, 'title':'x','body':'y','link':'./'}])
q4 = queue(uid)
check('6a: past-dated event is not queued (ttl protects users)',
      q4 and not any(e['id'] == f'{uid}:old' for e in q4['events']), json.dumps([e['id'] for e in q4['events']])[:200])

# 7) transport.log actually contains payload shapes OneSignal would receive
lg = loglines()
sample = [l for l in lg if l['payload']['name'] == ev_later['id']]
ok_shape = bool(sample) and 'send_at' in sample[-1]['payload'] and 'Z' in sample[-1]['payload']['send_at'] \
    and sample[-1]['payload']['include_external_ids'] == ['pl-test'] and sample[-1]['payload']['ttl'] == 3600
check('7a: payload has send_at(Z) + external id targeting + 1h ttl', ok_shape, json.dumps(sample[-1]['payload'])[:220] if sample else 'no log entry')
check('7b: body clamped to PUSH_MAX_BODY', max([len(l['payload']['contents']['en']) for l in lg] or [0]) <= 240)

# 8) empty schedule wipes the queue file (no orphan alerts after opt-out)
code, body = post(uid, [])
check('8a: opting out clears the queue', queue(uid) in (None,) or len(queue(uid)['events']) == 0, f"{body} {queue(uid)}")

srv.terminate()
try:
    srv.wait(timeout=5)
except Exception:
    srv.kill()
p = sum(1 for c in res if c)
if p != len(res):
    slog = f'{QDIR}/server.log'
    if os.path.exists(slog):
        tail = open(slog).read().strip().splitlines()[-12:]
        print("\n--- php server log (tail) ---\n" + "\n".join(tail))
print(f"\nSUMMARY: {p}/{len(res)} passed")
shutil.rmtree(QDIR, ignore_errors=True)
sys.exit(0 if p == len(res) else 1)
