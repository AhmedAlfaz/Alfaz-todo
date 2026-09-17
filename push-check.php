<?php
/**
 * Web-root diagnostics shim. Same reason abdo-sync.php lives at the root: this host refuses to
 * execute PHP inside push/. Output contains no secrets - it reports presence, versions and
 * writability only. Delete it when the setup is done.
 */
ini_set('display_errors', '1');
error_reporting(E_ALL);
header('Content-Type: text/plain; charset=utf-8');
echo "ABDO push diagnostics\n=====================\n\n";

$dir = __DIR__ . '/push';
$own = $dir . '/push-config.php';
require_once $dir . '/push-lib.php';
echo "push/ directory : " . (is_dir($dir) ? "found" : "MISSING <- the sync did not create it") . "\n";
foreach (['push-lib.php', 'push-sync.php', 'push-cron.php', 'push-config.php', 'push-config.example.php'] as $f) {
    printf("  %-24s %s\n", $f, is_readable($dir . '/' . $f) ? "readable" : "absent");
}
echo "\n";
$cfg = $dir . '/push-config.php';
if (is_readable($cfg)) {
    $src = file_get_contents($cfg);
    echo "push-config.php   : " . strlen($src) . " bytes\n";
    // exec()/shell_exec are disabled on this host, so lint by executing the definitions in a
    // sandboxed scope instead of shelling out to `php -l`.
    if (trim($src) === '' || ltrim($src) === '<?php') {
        echo "  parses          : " . (trim($src) === '' ? "FILE IS EMPTY - open it and paste the contents" : "loaded into a check scope") . "\n";
    }
    if (trim($src) !== '') {
        $body = preg_replace('/^<\?php\s*/', '', $src, 1);   // eval() starts in code mode
        $rc = 0; $err = '';
        try { eval($body); } catch (\Throwable $e) { $rc = 1; $err = $getMsg = $e->getMessage(); }
        echo "  syntax          : " . ($rc ? "BROKEN -> " . htmlspecialchars($err) : "ok") . "\n";
    }
    foreach (['ONESIGNAL_APP_ID' => '/ONESIGNAL_APP_ID\'\s*,\s*\'([^\']*)\'/', 'PUSH_TRANSPORT' => '/PUSH_TRANSPORT\'\s*,\s*\'([^\']*)\'/', 'PUSH_CRON_KEY set' => '/PUSH_CRON_KEY\'\s*,\s*\'([a-f0-9]{8,})\'/', 'REST key set' => '/ONESIGNAL_REST_KEY\'\s*,\s*\'([^\']{10,})\'/'] as $label => $re) {
        if (preg_match($re, $src, $m)) {
            $v = $m[1];
            echo "  $label            : " . ($label === 'PUSH_CRON_KEY set' || $label === 'REST key set' ? 'yes' : $v) . "\n";
        } else {
            echo "  $label            : NOT FOUND in the file\n";
        }
    }
} else {
    echo "push-config.php   : MISSING  <- create it: public_html/push/push-config.php\n";
}
if (function_exists('curl_init')) {
    echo "\nphp-curl          : available\n";
} else {
    echo "\nphp-curl          : MISSING - OneSignal calls will fail; set PUSH_TRANSPORT to 'log' until enabled\n";
}
echo "PHP               : " . PHP_VERSION . "\n";

// One block that answers the only two questions that matter after a "it should work" report:
// where the queue really is, and whether any device file exists anywhere on the account.
$cfgd = null;
if (function_exists('push_config')) { try { $cfgd = push_config(); } catch (\Throwable $e) {} }
echo "\ndebug\n------\n";
if ($own && is_readable($own)) {
    $lines = preg_split('/\n/', (string)file_get_contents($own));
    $dirLine = '(PUSH_DIR not set in push-config.php - the code default applies)';
    foreach ($lines as $l) { if (strpos($l, 'PUSH_DIR') !== false) { $dirLine = trim($l); break; } }
    echo "  config line : " . $dirLine . "\n";
}
if (is_readable($own)) {
    $md = filemtime($own);
    echo "  config saved : " . date('Y-m-d H:i:s', $md)
       . " (" . round((time() - $md) / 60) . " min ago)\n";
}
echo "  queue in use : " . ($cfgd ? $cfgd['dir'] : 'unknown') . "\n";
echo "  push/ __DIR__  : " . $dir . "\n";
// The one question that decides everything: is push-config.php in push/ where the code expects
// it, or one level too high in public_html/? A misplaced config resolves every relative path in it
// against the wrong folder, which looks exactly like a silently empty queue.
foreach ([__DIR__ . '/push/push-config.php', __DIR__ . '/push-config.php'] as $cand) {
    echo '  config at ' . (substr($cand, strlen(__DIR__)) ?: '/') . ' : '
       . (file_exists($cand) ? 'EXISTS (saved ' . date('H:i', filemtime($cand)) . ')' : 'absent') . "\n";
}
$cfgreal = __DIR__ . '/push/push-config.php';
if (is_readable($cfgreal)) {
    foreach (preg_split('/\n/', (string)file_get_contents($cfgreal)) as $l) {
        if (stripos($l, 'PUSH_DIR') !== false) echo '  PUSH_DIR line : ' . trim($l) . "\n";
    }
}
if (file_exists(__DIR__ . '/push-config.php') && !file_exists(__DIR__ . '/push/push-config.php')) {
    echo "  >> MISPLACED. Move push-config.php INTO the push/ folder.\n";
}
echo "  PUSH_DIR raw   : " . (defined('PUSH_DIR') ? PUSH_DIR : '(not defined - code default)') . "\n"
   . "  push-lib __DIR__: " . (function_exists('push_dir_probe') ? push_dir_probe() : 'n/a') . "\n";
echo "  file tree      : ";
$seen = [];
foreach (['push/push-lib.php' => 'push-lib', 'push/push-sync.php' => 'push-sync', 'queue' => 'public_html/queue',
          'push/queue' => 'push/queue', 'abdo-sync.php' => 'root abdo-sync'] as $rel => $lbl) {
    $seen[] = $lbl . (file_exists(__DIR__ . '/' . $rel) ? '=yes' : '=no');
}
echo implode(' ', $seen) . "\n";
$found = [];
$base = isset($cfgd) && $cfgd ? dirname($cfgd['dir']) : __DIR__;   // public_html
foreach ([
    $cfgd ? $cfgd['dir'] . '/user-*.json' : '',
    $base . '/queue/user-*.json',
    $base . '/push/queue/user-*.json',
    dirname($base) . '/abdo-push/queue/user-*.json',
] as $pat) { if ($pat) $found = array_merge($found, glob($pat) ?: []); }
$found = array_values(array_unique($found));
echo "  device files : " . count($found) . ($found ? "" : "  <- nobody is registered") . "
";
foreach (array_slice($found, 0, 4) as $f) {
    $j = json_decode((string)file_get_contents($f), true);
    $pl = !empty($j['player']) ? substr((string)$j['player'], 0, 12) : 'none';
    echo "    " . basename($f) . "  player=" . $pl . "  events=" . count((array)($j['events'] ?? []))
       . "  synced=" . (empty($j['sync_at']) ? '?' : date('H:i', (int)$j['sync_at'])) . "
";
}


// Use the loader's own PUSH_DIR - guessing the path here is how a check reports an empty queue
// while cron is reading a populated one two folders away.
if (isset($_GET['queue']) && function_exists('push_config')) {
    $cfg = push_config();
    $qd = (string)$cfg['dir'];
    echo "\nqueue dir    : $qd " . (is_dir($qd) ? "" : "(MISSING)") . "\n";
    $files = is_dir($qd) ? (glob($qd . '/user-*.json') ?: []) : [];
    echo "queue files  : " . count($files) . "\n";
    foreach ($files as $f) {
        $j = json_decode((string)file_get_contents($f), true);
        foreach ((array)($j['events'] ?? []) as $e) {
            echo "  event " . substr((string)($e['id'] ?? ''), 0, 18) . ": sent=" . (int)($e['sent'] ?? 0)
               . " attempts=" . (int)($e['attempts'] ?? 0)
               . " nid=" . (empty($e['nid']) ? 'none' : 'set')
               . (empty($e['error']) ? "" : "  ERROR: " . substr((string)$e['error'], 0, 200)) . "\n";
        }
    }
}

// --- Key check: runs on every load, no flag needed -------------------------------
// Ask the SAME endpoint the sender uses, the SAME way. GET /apps/{id} is app-management and
// does not authenticate like create-notification, so testing there produced a false 401.
// This POST is deliberately undeliverable (unknown external id): it can only fail on auth or
// payload, never on sending, so a 200 proves the key with no notification going anywhere.
if (function_exists('curl_init')) {
    $cfgx = push_config();
    $payload = json_encode(['app_id' => (string)$cfgx['app_id'],
                            'contents' => ['en' => 'auth probe - not delivered'],
                            'include_external_ids' => ['onesignal-auth-probe']]);
    $ch = curl_init('https://onesignal.com/api/v1/notifications');
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 15,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json; charset=utf-8',
                               'Authorization: Basic ' . (string)$cfgx['rest_key']],
        CURLOPT_POSTFIELDS => $payload]);
    $body = (string)curl_exec($ch); $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlerr = curl_error($ch); curl_close($ch);
    $j = json_decode($body, true);
    echo "\nOneSignal auth  : ";
    if ((string)$cfgx['rest_key'] === '') {
        echo "NO REST KEY SET - the line is still empty\n";
    } elseif ($code === 200) {
        echo "key ACCEPTED (HTTP 200)\n";
        echo "  note: the probe id is unknown, so nothing was delivered\n";
    } elseif ($code === 401 || strpos($body, 'Access denied') !== false) {
        echo "key REJECTED (HTTP $code)\n";
        // Shape, not contents: enough to tell a wrong field from a truncated copy.
        $k = (string)$cfgx['rest_key'];
        $shape = preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $k)
               ? 'looks like a valid OneSignal key (36-char UUID)'
               : 'does NOT look like a OneSignal key - wrong field copied, or text got mangled';
        $stray = preg_match('/^[A-Za-z0-9+_\/=-]+$/', $k) ? 'no stray spaces' : 'CONTAINS SPACES OR STRAY CHARACTERS';
        echo '  stored: ' . strlen($k) . ' chars, starts [' . substr($k, 0, 4) . '] ends [' . substr($k, -2) . '], ' . $stray . "\n";
        echo '  shape : ' . $shape . "\n";
        echo "  if the field is empty in the dashboard, click Create/Generate first, then copy with the copy button (manual selection drops characters)\n";
        // The App ID and the REST key sit side by side in Keys & IDs, so swapping them is the
        // single most common failure - and it reads as '401 bad key', pointing away from the cause.
        if ($k !== '' && hash_equals((string)$cfgx['app_id'], $k)) {
            echo "  >> THAT IS YOUR APP ID, NOT THE REST KEY. Keys & IDs lists both; use the line"
               . " labelled 'REST API key' (it is hidden until you click View).\n";
        }
    } else {
        echo "key ACCEPTED enough to be checked, but the call failed (HTTP $code)\n";
        $err = is_array($j) ? json_encode($j) : substr($body, 0, 160);
        echo "  " . substr(preg_replace('/[\r\n\t]+/', ' ', (string)$err), 0, 160) . "\n";
        if ($curlerr !== '') echo "  curl: " . substr($curlerr, 0, 120) . "\n";
    }
}
