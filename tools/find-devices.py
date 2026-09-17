import io, sys

C = '/home/user/Alfaz-todo/push-check.php'
s = io.open(C, encoding='utf-8').read()
anchor = "echo \"PHP               : \" . PHP_VERSION . \"\\n\";"
assert s.count(anchor) == 1, 'anchor'

add = anchor + """

// One block that answers the only two questions that matter after a "it should work" report:
// where the queue really is, and whether any device file exists anywhere on the account.
$cfgd = null;
if (function_exists('push_config')) { try { $cfgd = push_config(); } catch (\\Throwable $e) {} }
echo "\\ndebug\\n------\\n";
if ($own && is_readable($own)) {
    $lines = preg_split('/\\n/', (string)file_get_contents($own));
    $dirLine = '(PUSH_DIR not set in push-config.php - the code default applies)';
    foreach ($lines as $l) { if (strpos($l, 'PUSH_DIR') !== false) { $dirLine = trim($l); break; } }
    echo "  config line : " . $dirLine . "\\n";
}
if (is_readable($own)) {
    $md = filemtime($own);
    echo "  config saved : " . date('Y-m-d H:i:s', $md)
       . " (" . round((time() - $md) / 60) . " min ago)\\n";
}
echo "  queue in use : " . ($cfgd ? $cfgd['dir'] : 'unknown') . "\\n";
$found = [];
$base = isset($cfgd) && $cfgd ? dirname($cfgd['dir']) : __DIR__;   // public_html
foreach ([
    $cfgd ? $cfgd['dir'] . '/user-*.json' : '',
    $base . '/queue/user-*.json',
    $base . '/push/queue/user-*.json',
    dirname($base) . '/abdo-push/queue/user-*.json',
] as $pat) { if ($pat) $found = array_merge($found, glob($pat) ?: []); }
$found = array_values(array_unique($found));
echo "  device files : " . count($found) . ($found ? "" : "  <- nobody is registered") . "\n";
foreach (array_slice($found, 0, 4) as $f) {
    $j = json_decode((string)file_get_contents($f), true);
    $pl = !empty($j['player']) ? substr((string)$j['player'], 0, 12) : 'none';
    echo "    " . basename($f) . "  player=" . $pl . "  events=" . count((array)($j['events'] ?? []))
       . "  synced=" . (empty($j['sync_at']) ? '?' : date('H:i', (int)$j['sync_at'])) . "\n";
}
"""
s = s.replace(anchor, add)

# the device count in cron was globbing two guessed paths; make it reuse the same helper idea
K = '/home/user/Alfaz-todo/push/push-cron.php'
k = io.open(K, encoding='utf-8').read()
old = "(count(array_unique(array_merge(glob($cfg['dir'] . '/user-*.json') ?: [], glob(dirname($cfg['dir']) . '/user-*.json') ?: []))))"
if k.count(old) == 1:
    print('  (cron devices glob already broad)')
else:
    o2 = "(count(glob(dirname($cfg['dir']) . '/user-*.json') ?: []))"
    assert k.count(o2) == 1, 'cron devices anchor: %d' % k.count(o2)
    k = k.replace(o2, "(count(glob($cfg['dir'] . '/user-*.json') ?: []))")
    io.open(K, 'w', encoding='utf-8').write(k)
    print('cron devices now reads the loader-resolved dir')

io.open(C, 'w', encoding='utf-8').write(s)
for f in (C, K):
    t = io.open(f, encoding='utf-8').read()
    d = 0
    for ch in t: d += (ch == '{') - (ch == '}')
    if d: print('  !! unbalanced', f, d); sys.exit(1)
print('balanced')
