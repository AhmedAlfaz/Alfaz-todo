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
} elseif (is_dir($dir . '/queue') || is_dir(dirname($dir) . '/abdo-push/queue')) {
    echo "\nqueue present : yes (use ?queue=1 to read it)\n";
} else {
    echo "\nqueue present : not created yet\n";

// Ask the SAME endpoint the sender uses, the SAME way. GET /apps/{id} is app-management and
// does not authenticate like create-notification, so testing there produced a false 401.
// This POST is deliberately undeliverable (unknown external id): it can only fail on auth or
// payload, never on sending, so a 200 proves the key with no notification going anywhere.
if (function_exists('curl_init') && isset($_GET['auth'])) {
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
    } else {
        echo "key ACCEPTED enough to be checked, but the call failed (HTTP $code)\n";
        $err = is_array($j) ? json_encode($j) : substr($body, 0, 160);
        echo "  " . substr(preg_replace('/[\r\n\t]+/', ' ', (string)$err), 0, 160) . "\n";
        if ($curlerr !== '') echo "  curl: " . substr($curlerr, 0, 120) . "\n";
    }
} elseif (isset($_GET['auth'])) {
    echo "\nOneSignal auth  : cannot check, curl extension unavailable\n";
}
}
