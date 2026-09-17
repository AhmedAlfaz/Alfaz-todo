import io, sys

LIB = '/home/user/Alfaz-todo/push/push-lib.php'
CRON = '/home/user/Alfaz-todo/push/push-cron.php'

s = io.open(LIB, encoding='utf-8').read()
old = """        'name'        => (string)($ev['id'] ?? ''),          // lets us cancel by name later
        'include_external_ids' => [(string)$external_id],"""
new = """        'name'        => substr(preg_replace('/[^A-Za-z0-9_.:-]/', '', (string)($ev['id'] ?? '')), 0, 50),
        // include_external_user_ids is the real v1 field. 'include_external_ids' does not exist,
        // so the call addressed nobody and was rejected - while a minimal auth probe still
        // returned 200, which is why 'key ACCEPTED' and 'failed=1' appeared together.
        'include_external_user_ids' => [(string)$external_id],"""
if s.count(old) != 1:
    print('LIB anchor miss:', s.count(old)); sys.exit(1)
s = s.replace(old, new)

old2 = """        'ttl'         => 3600,                                // never deliver a prayer alert late by an hour
        'priority'    => 10,"""
new2 = """        'ttl'         => 3600,                                // never deliver a prayer alert late by an hour"""
if s.count(old2) != 1:
    print('priority anchor miss:', s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

# keep the reason on the queue entry so the cron line can echo it
old3 = """        if ($r['ok']) { $sent++; $e['sent'] = $now; $e['nid'] = $r['id']; }"""
io.open(LIB, 'w', encoding='utf-8').write(s)
print('LIB patched')

c = io.open(CRON, encoding='utf-8').read()
old4 = """$keep[] = $e; // kept one extra cycle for the delivery log, then pruned"""
new4 = """$keep[] = $e; // kept one extra cycle so the reason survives to the next report"""
if c.count(old4) == 1:
    c = c.replace(old4, new4)
# append a one-line reason to the summary so the failure is self-describing
old5 = """. transport=" . $cfg['transport'] . "\\n";"""
new5 = """. transport=" . $cfg['transport']
    . ($lasterr ? "  last_error=" . substr(preg_replace('/\\s+/', ' ', $lasterr), 0, 160) : '') . "\\n";"""
if c.count(old5) != 1:
    print('CRON summary anchor miss:', c.count(old5)); sys.exit(1)
c = c.replace(old5, new5)
# track it
old6 = "$sent = $skipped = $failed = $pruned = 0;"
new6 = "$sent = $skipped = $failed = $pruned = 0;\n$lasterr = '';"
if c.count(old6) != 1:
    print('CRON counters anchor miss:', c.count(old6)); sys.exit(1)
c = c.replace(old6, new6)
old7 = """else { $failed++; $e['error'] = substr((string)($r['error'] ?? '?'), 0, 200); }"""
new7 = """else { $failed++; $e['error'] = substr((string)($r['error'] ?? '?'), 0, 200); $lasterr = $e['error']; }"""
if c.count(old7) != 1:
    print('CRON fail anchor miss:', c.count(old7)); sys.exit(1)
c = c.replace(old7, new7)
# keep failed events instead of pruning them at once, so the reason is readable after one run
old8 = """        if ((int)($e['attempts'] ?? 0) >= 2) { $pruned++; $changed = true; continue; } // gave up, logged"""
new8 = """        if ((int)($e['attempts'] ?? 0) >= 3) {            // three cycles, so a human can read why
            @file_put_contents($cfg['dir'] . '/delivery.log', date('c') . ' dropped '
                . substr((string)($e['id'] ?? '?'), 0, 24) . ' error='
                . substr((string)($e['error'] ?? 'none'), 0, 220) . "\\n", FILE_APPEND);
            $pruned++; $changed = true; continue;
        }"""
if c.count(old8) == 1:
    c = c.replace(old8, new8)
else:
    print('  (cron already has the logged-prune variant, leaving it)')
io.open(CRON, 'w', encoding='utf-8').write(c)
print('CRON patched')

for f in (LIB, CRON):
    t = io.open(f, encoding='utf-8').read()
    d = 0
    for ch in t:
        d += (ch == '{') - (ch == '}')
    print(' ', f.split('/')[-1], 'brace depth', d)
