import io, sys

p = '/home/user/Alfaz-todo/push/push-lib.php'
s = io.open(p, encoding='utf-8').read()

old = """    if ($code >= 200 && $code < 300 && !empty($json['id'])) {
        return ['ok' => true, 'id' => $json['id']];
    }
    return ['ok' => false, 'id' => null, 'error' => 'http ' . $code . ' ' . substr((string)$raw, 0, 180)];"""
new = """    if ($code >= 200 && $code < 300 && !empty($json['id'])) {
        return ['ok' => true, 'id' => $json['id']];
    }
    // An empty audience is a SUCCESS with nothing to do, not a failure: a brand-new install has
    // no subscribers yet, and reporting it as failed makes a healthy setup look broken and
    // burns a retry cycle per event. Counted separately so cron can say "noaudience".
    $msg = (string)$raw;
    if ($code >= 200 && $code < 300 && strpos($msg, 'not subscribed') !== false) {
        return ['ok' => true, 'id' => null, 'noop' => 'noaudience'];
    }
    return ['ok' => false, 'id' => null, 'error' => 'http ' . $code . ' ' . substr($msg, 0, 180)];"""
if s.count(old) != 1:
    print('anchor miss', s.count(old)); sys.exit(1)
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8').write(s)
print('lib: empty audience is no longer a failure')

c = '/home/user/Alfaz-todo/push/push-cron.php'
t = io.open(c, encoding='utf-8').read()
o2 = "        if ($r['ok']) { $sent++; $e['sent'] = $now; $e['nid'] = $r['id']; }"
n2 = """        if ($r['ok']) {
            $e['sent'] = $now;
            if (!empty($r['noop'])) { $noop++; } else { $sent++; $e['nid'] = $r['id']; }
        }"""
if t.count(o2) != 1:
    print('cron ok anchor miss', t.count(o2)); sys.exit(1)
t = t.replace(o2, n2)
t = t.replace("$sent = $skipped = $failed = $pruned = 0;", "$sent = $skipped = $failed = $pruned = $noop = 0;")
t = t.replace(' sent=$sent failed=$failed', ' sent=$sent delivered=($noop) failed=$failed'.replace('($noop)', '$noop'))
io.open(c, 'w', encoding='utf-8').write(t)
for f in (p, c):
    x = io.open(f, encoding='utf-8').read()
    d = 0
    for ch in x:
        d += (ch == '{') - (ch == '}')
    print(' ', f.split('/')[-1], 'depth', d)
