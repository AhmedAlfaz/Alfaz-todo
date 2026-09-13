<?php
/**
 * ABDO push — environment check. Upload this alongside the other push/ files and open it
 * in a browser ONCE: https://YOUR-DOMAIN/push/push-check.php
 * It prints no secrets. Delete it when the deploy is done (it confirms the folder is web-readable).
 */
header('Content-Type: text/plain; charset=utf-8');
echo "ABDO push environment check\n";
echo "=============================\n\n";

// Read the transport first: curl is only unavoidable once real delivery is switched on.
$transport = 'log'; $haveCfg = is_readable(__DIR__ . '/push-config.php');
if ($haveCfg) {
    $t = @file_get_contents(__DIR__ . '/push-config.php');
    if ($t && preg_match("/define\('PUSH_TRANSPORT'\s*,\s*'([a-z]+)'/", $t, $m)) $transport = $m[1];
}
$live = ($transport === 'onesignal');
$must = [
    'hash_hmac'         => 'device write tokens',
    'json_encode'       => 'queue format',
    'preg_split'        => 'text clamping fallback',
    'file_put_contents' => 'queue writes',
    'glob'              => 'cron sweep',
    'curl_init'         => $live ? 'SENDING TO ONESIGNAL - install php-curl (or apt install php8.x-curl)'
                                 : 'not needed yet (dry run writes a log instead)',
];
$want = ['mb_substr' => 'multibyte trim (fallback exists without it)',
         'exec' => 'openssl signing (only needed if we ever drop OneSignal)',
         'shell_exec' => 'same as exec', 'proc_open' => 'same as exec'];

$fail = 0;
echo "Transport is: {$transport}" . ($live ? "  -> real delivery\n" : "  -> dry run, nothing reaches a phone yet\n");
echo "\nMUST have:\n";
foreach ($must as $fn => $why) {
    $ok = function_exists($fn);
    $optional = ($fn === 'curl_init' && !$live);
    if (!$ok && !$optional) $fail++;
    printf("  [%s] %-16s %s\n", $ok ? 'YES' : ($optional ? 'n/a' : 'NO '), $fn, $why);
}
echo "\nNice to have (we degrade without them):\n";
foreach ($want as $fn => $why) {
    printf("  [%s] %-18s %s\n", function_exists($fn) ? 'YES' : 'no ', $fn, $why);
}

echo "\nPHP: " . PHP_VERSION;
echo $fail ? "\n\nBLOCKED: {$fail} required function(s) are disabled. Tell me which and I will adapt.\n"
           : "\n\nFunctions look good.\n";

echo "Config: ";
$env = getenv('ABDO_PUSH_CONFIG');
$own = __DIR__ . '/push-config.php';
if (is_readable($own)) {
    echo basename($own), "\n";
    $c = (function () { include $own; return ['transport' => PUSH_TRANSPORT, 'dir' => PUSH_DIR,
        'appid' => ONESIGNAL_APP_ID, 'rest' => ONESIGNAL_REST_KEY !== '', 'secret' => PUSH_TOKEN_SECRET !== '']; })();
    echo "  PUSH_TRANSPORT : {$c['transport']}" . ($c['transport'] === 'log' ? "   (dry run, nothing is delivered yet)\n" : "\n");
    echo "  ONESIGNAL_APP_ID: " . ($c['appid'] === '' ? "EMPTY - fill it in\n" : "set\n");
    echo "  REST key set     : " . ($c['rest'] ? "yes\n" : "NO - needed for real delivery\n");
    echo "  Token secret set : " . ($c['secret'] ? "yes\n" : "NO - the sync endpoint will refuse everyone\n");
    $q = rtrim($c['dir'], '/');
    if (!is_dir($q)) @mkdir($q, 0750, true);
    echo "  Queue dir        : " . (is_writable($q) ? "writable ({$q})\n" : "NOT WRITABLE ({$q}) - fix perms or change PUSH_DIR\n");
} else {
    echo "push-config.php NOT FOUND - copy push-config.example.php to push-config.php\n";
}

echo "\nHow cron can reach us: ";
echo file_get_contents('php://input') !== false ? "php://input readable\n" : "php://input NOT readable\n";
echo "Web root: " . (isset($_SERVER['DOCUMENT_ROOT']) ? $_SERVER['DOCUMENT_ROOT'] : '(unknown)') . "\n";
echo "This file: " . __FILE__ . "\n";
echo "=> If 'This file' starts with the Web root, remember the queue dir is inside the web root\n";
echo "   and push/.htaccess must deny it. Prefer PUSH_DIR outside public_html when you can.\n";
