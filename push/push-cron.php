<?php
/**
 * ABDO push — cron worker.
 * hPanel -> Cron Jobs -> wget -q -O - "https://YOUR-DOMAIN/push/push-cron.php" >/dev/null 2>&1
 * Every run: send anything due within PUSH_WINDOW_MIN minutes, then forget it.
 * A missed cron run only costs the events inside the window; it never double-sends,
 * because `sent` is recorded before the request is made.
 */
require_once __DIR__ . '/push-lib.php';
@set_time_limit(50);
header('Content-Type: text/plain; charset=utf-8');

$cfg = push_config();

// Refuse strangers. No key configured -> only the CLI (php push-cron.php) may run, which is
// the safer default: a forgotten PUSH_CRON_KEY must not silently leave a public trigger.
// NOTE: push_config() must run first - it is what defines PUSH_CRON_KEY.
$key = defined('PUSH_CRON_KEY') ? (string)PUSH_CRON_KEY : '';
if (PHP_SAPI !== 'cli') {
    $given = isset($_GET['key']) ? (string)$_GET['key'] : '';
    if ($key === '' || !hash_equals($key, $given)) {
        http_response_code(403);
        echo "forbidden\n";
        exit;
    }
}

$glob = glob($cfg['dir'] . '/user-*.json') ?: [];
$now = time();
$horizon = $now + $cfg['window'] * 60;
$sent = $skipped = $failed = $pruned = $noop = 0;
$lasterr = '';

foreach ($glob as $file) {
    $snap = json_decode((string)file_get_contents($file), true);
    if (!is_array($snap) || empty($snap['events'])) { continue; }
    $changed = false; $keep = []; $has_future = false;
    foreach ($snap['events'] as $e) {
        $due = (int)($e['send_at'] ?? 0) <= $horizon;
        if (!$due) { $keep[] = $e; $has_future = true; continue; }
        if (!empty($e['sent'])) { $pruned++; $changed = true; continue; }          // delivered
        if (!empty($e['pre_sent'])) {                                            // scheduled by OneSignal already
            if ((int)($e['send_at'] ?? 0) <= $now) { $pruned++; $changed = true; continue; }
            $keep[] = $e; continue;                                              // leave it alone, it is in flight
        }
        if ((int)($e['attempts'] ?? 0) >= 3) {          // three cycles, so the reason outlives the run
            @file_put_contents($cfg['dir'] . '/delivery.log', date('c') . ' dropped '
                . substr((string)($e['id'] ?? '?'), 0, 24) . ' error='
                . substr((string)($e['error'] ?? 'none'), 0, 220) . "\n", FILE_APPEND);
            $pruned++; $changed = true; continue;
        }
        // `sent` is only set on success; a failed attempt retries once, then gives up.
        // OneSignal's own ttl drops anything older than an hour, so we can never deliver
        // a stale prayer alert late — worst case is no alert, which the log records.
        $e['attempts'] = (int)($e['attempts'] ?? 0) + 1; $changed = true;
        $r = push_send($e, $e['ext'] ?? $snap['uid'], $cfg);
        if ($r['ok']) {
            $e['sent'] = $now;
            if (!empty($r['noop'])) { $noop++; } else { $sent++; $e['nid'] = $r['id']; }
        }
        else { $failed++; $e['error'] = substr((string)($r['error'] ?? '?'), 0, 200); $lasterr = $e['error']; }
        $keep[] = $e; // kept one extra cycle for the delivery log, then pruned
    }
    if ($keep === []) { @unlink($file); continue; }        // empty or all-past schedule: forget the device
    if ($changed) {
        $snap['events'] = array_values($keep);
        @file_put_contents($file, json_encode($snap), LOCK_EX);
    }
}
echo "abdo-push-cron " . date('c') . " cfg=" . basename((string)($cfg["config_file"] ?? "?")) . " files=" . count($glob) . " sent=$sent delivered=$noop failed=$failed pruned=$pruned skipped=$skipped transport=" . $cfg['transport']
    . ($lasterr ? "  last_error=" . substr(preg_replace('/\s+/', ' ', $lasterr), 0, 170) : '')
    . (isset($_GET['devices']) ? '  devices=' . (count(glob($cfg['dir'] . '/user-*.json') ?: [])) : '')
    . "\n";
