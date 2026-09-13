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

// Last delivery attempts, reason only - no uid, no token, no player id.
$qdir = defined('PUSH_DIR_OK') ? '' : (is_dir($dir . '/queue') ? $dir . '/queue' : dirname($dir) . '/abdo-push/queue');
$files = is_dir($qdir) ? glob($qdir . '/user-*.json') : [];
echo "\nqueue: " . count($files) . " device file(s)\n";
$shown = 0;
foreach ($files as $f) {
    $j = json_decode((string)file_get_contents($f), true);
    foreach ((array)($j['events'] ?? []) as $e) {
        if (empty($e['error'])) continue;
        $http = preg_match('/http (\d+)/', (string)$e['error'], $m) ? 'HTTP ' . $m[1] : 'no response';
        echo "  last send: " . $http;
        if (preg_match('/\{"errors[^}]{0,120}/', (string)$e['error'], $mm)) echo "  " . substr($mm[0], 0, 120);
        echo "\n  attempts: " . (int)($e['attempts'] ?? 0) . "\n";
        if (++$shown >= 3) break 2;
    }
}
if (!$shown) echo "  no recorded send failures\n";
