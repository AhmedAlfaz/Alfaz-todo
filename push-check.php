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

// One read-only call, and the only thing we print is the verdict - never the key.
if (function_exists('curl_init') && isset($_GET['auth'])) {
    $cfgx = push_config();
    $ch = curl_init('https://onesignal.com/api/v1/apps/' . rawurlencode((string)$cfgx['app_id']));
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 12,
        CURLOPT_HTTPHEADER => ['Authorization: Basic ' . (string)$cfgx['rest_key']]]);
    $body = (string)curl_exec($ch); $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    echo "\nOneSignal auth  : ";
    if ($cfgx['rest_key'] === '') echo "NO REST KEY SET (line is empty in push-config.php)\n";
    elseif ($code === 200) echo "REST key is VALID (HTTP 200)\n";
    else echo "REJECTED (HTTP $code) - " . (strpos($body, 'Access denied') !== false ? 'wrong or truncated key'
        : substr(preg_replace('/[^A-Za-z0-9 .]/', '', (string)json_decode($body, true)['errors'][0] ?? $body), 0, 90)) . "\n";
} elseif (isset($_GET['auth'])) {
    echo "\nOneSignal auth  : cannot check, curl extension unavailable\n";
}
}
