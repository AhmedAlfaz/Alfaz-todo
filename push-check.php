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
    echo "  parses          : ";
    $tmp = tempnam(sys_get_temp_dir(), 'chk') . '.php';
    file_put_contents($tmp, $src);
    exec('php -l ' . escapeshellarg($tmp) . ' 2>&1', $out, $rc);
    @unlink($tmp);
    echo ($rc === 0 ? "yes\n" : "NO -> " . htmlspecialchars(implode(' ', $out)) . "\n");
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
