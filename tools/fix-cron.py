import io, sys

CRON = '/home/user/Alfaz-todo/push/push-cron.php'
c = io.open(CRON, encoding='utf-8').read()

edits = [
    ("$sent = $skipped = $failed = $pruned = 0;",
     "$sent = $skipped = $failed = $pruned = 0;\n$lasterr = '';"),

    ("        if ((int)($e['attempts'] ?? 0) >= 2) { $pruned++; $changed = true; continue; } // gave up, logged",
     "        if ((int)($e['attempts'] ?? 0) >= 3) {          // three cycles, so the reason outlives the run\n"
     "            @file_put_contents($cfg['dir'] . '/delivery.log', date('c') . ' dropped '\n"
     "                . substr((string)($e['id'] ?? '?'), 0, 24) . ' error='\n"
     "                . substr((string)($e['error'] ?? 'none'), 0, 220) . \"\\n\", FILE_APPEND);\n"
     "            $pruned++; $changed = true; continue;\n"
     "        }"),

    ("        else { $failed++; $e['error'] = substr((string)($r['error'] ?? '?'), 0, 200); }",
     "        else { $failed++; $e['error'] = substr((string)($r['error'] ?? '?'), 0, 200); $lasterr = $e['error']; }"),

    (""" . $cfg['transport'] . "\\n";""",
     """ . $cfg['transport']
    . ($lasterr ? "  last_error=" . substr(preg_replace('/\\s+/', ' ', $lasterr), 0, 170) : '') . "\\n";"""),
]

for old, new in edits:
    n = c.count(old)
    if n != 1:
        print('ANCHOR MISS (%d): %r' % (n, old[:60])); sys.exit(1)
    c = c.replace(old, new)

io.open(CRON, 'w', encoding='utf-8').write(c)
d = 0
for ch in c:
    d += (ch == '{') - (ch == '}')
print('CRON patched, brace depth', d)
