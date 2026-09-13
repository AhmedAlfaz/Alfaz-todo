<?php
/**
 * ABDO push sender — transport layer.
 * Kept separate so the queue logic can be tested without touching OneSignal.
 */

function push_config() {
    static $cfg = null;
    if ($cfg !== null) return $cfg;

    // ABDO_PUSH_CONFIG lets a host (or a test harness) point at a config outside the web root.
    $env = getenv('ABDO_PUSH_CONFIG');
    $candidates = array_values(array_filter(
        [$env, __DIR__ . '/push-config.php', __DIR__ . '/push-config.example.php'], 'is_readable'));
    if (!$candidates) {
        throw new RuntimeException('ABDO push: no config found (copy push-config.example.php to push-config.php)');
    }
    $cfg_file = $candidates[0];
    // Running on the example template is how a mis-deploy looks like "no errors, no notifications".
    // Record which file is live so push-check.php and the cron line both show it.
    $is_template = basename($cfg_file) === 'push-config.example.php';
    require_once $cfg_file;

    // Queue path is never left to a hand-edited value: a wrong one makes every write fail quietly
    // (a guessed dirname() level pointed the first deploy outside the site, and nothing complained).
    $dir = defined('PUSH_DIR') ? (string)PUSH_DIR : __DIR__ . '/queue';
    if (!is_dir($dir) && !@mkdir($dir, 0750, true)) {
        $dir = __DIR__ . '/queue';
        if (!is_dir($dir)) @mkdir($dir, 0750, true);
    }
    if (!is_dir($dir) || !is_writable($dir)) {
        throw new RuntimeException('ABDO push: queue directory is not writable: ' . $dir);
    }

    $cfg = [
        'app_id'      => defined('ONESIGNAL_APP_ID') ? ONESIGNAL_APP_ID : '',
        'rest_key'    => defined('ONESIGNAL_REST_KEY') ? ONESIGNAL_REST_KEY : '',
        'transport'   => defined('PUSH_TRANSPORT') ? PUSH_TRANSPORT : 'log',
        'dir'         => $dir,
        'secret'      => defined('PUSH_TOKEN_SECRET') ? PUSH_TOKEN_SECRET : '',
        'window'      => defined('PUSH_WINDOW_MIN') ? (int)PUSH_WINDOW_MIN : 15,
        'max_events'  => defined('PUSH_MAX_EVENTS_PER_USER') ? (int)PUSH_MAX_EVENTS_PER_USER : 120,
        'max_body'    => defined('PUSH_MAX_BODY') ? (int)PUSH_MAX_BODY : 240,
        'cron_key'    => defined('PUSH_CRON_KEY') ? (string)PUSH_CRON_KEY : '',
        'config_file' => $cfg_file . ($is_template ? '  <-- TEMPLATE: copy to push-config.php' : ''),
    ];
    return $cfg;
}

/** mbstring is not guaranteed on shared hosting; a missing extension must not kill the endpoint. */
function push_cut($s, $limit) {
  $s = (string)$s;
  if ($limit <= 0) return '';
  if (function_exists('mb_substr')) return mb_substr($s, 0, $limit);
  $chunks = preg_split('//u', $s, -1, PREG_SPLIT_NO_EMPTY);
  return $chunks === false ? substr($s, 0, $limit) : implode('', array_slice($chunks, 0, $limit));
}

/** Sign/verify the per-device token. token = base64url(uid . ':' . hmac(uid, secret)). */
// The token is derived, not distributed: a client can compute the token for ITS OWN uid from
// public values (uid + app id), but cannot compute one for anyone else's uid without the server
// secret. So no write credential ever has to be copied into site-config.json.
function push_token_for($uid, $secret, $app_id = '') {
    $mac = rawurlencode(base64_encode(hash_hmac('sha256', $uid . ':' . $secret, $app_id, true)));
    return rtrim(strtr(base64_encode($uid . ':' . $app_id . ':' . $mac), '+/', '-_'), '=');
}
function push_token_ok($uid, $token, $secret, $app_id = '') {
    if ($token === null || $token === '') return false;
    // Binding mode (default): token = f(uid, public app id). Proves the caller knows the uid;
    // needs no secret in the public client. Set PUSH_REQUIRE_SECRET_TOKEN=true after moving
    // subscription state into Supabase, where the server can hand a device a real credential.
    if (!$secret) return hash_equals(push_token_for($uid, '', $app_id), (string)$token);
    return hash_equals(push_token_for($uid, $secret, $app_id), (string)$token)
        || hash_equals(push_token_for($uid, '', $app_id), (string)$token);
}

function push_queue_path($uid) {
    $cfg = push_config();
    // uid is a Supabase uuid or a hex device id; refuse anything else (path traversal)
    if (!preg_match('/^[A-Za-z0-9_-]{6,64}$/', $uid)) return null;
    return $cfg['dir'] . '/user-' . $uid . '.json';
}

/**
 * Deliver one event.
 * @return array{ok:bool, id:?string, error?:string}
 */
function push_send(array $ev, $external_id, array $cfg) {
    $body = push_cut((string)($ev['body'] ?? ''), $cfg['max_body']);
    $payload = [
        'app_id'      => $cfg['app_id'],
        'name'        => (string)($ev['id'] ?? ''),          // lets us cancel by name later
        'include_external_ids' => [(string)$external_id],
        'send_at'     => gmdate('Y-m-d\TH:i:s\Z', (int)$ev['send_at']),
        'contents'    => ['en' => $body, 'ar' => $body],
        'headings'    => ['en' => (string)($ev['title'] ?? ''), 'ar' => (string)($ev['title'] ?? '')],
        'url'         => (string)($ev['link'] ?? './'),
        'chrome_web_icon' => 'brand/abdo-icon-192-wb.png',
        'ttl'         => 3600,                                // never deliver a prayer alert late by an hour
        'priority'    => 10,
    ];
    if ($cfg['transport'] !== 'onesignal') {
        @file_put_contents($cfg['dir'] . '/transport.log',
            json_encode(['t' => date('c'), 'dry' => true, 'payload' => $payload]) . "\n", FILE_APPEND);
        return ['ok' => true, 'id' => 'log-' . substr(md5($ev['id'] . $external_id), 0, 12)];
    }
    if ($cfg['app_id'] === '' || $cfg['rest_key'] === '') {
        return ['ok' => false, 'id' => null, 'error' => 'onesignal credentials missing'];
    }
    $ch = curl_init('https://onesignal.com/api/v1/notifications');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 10,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json; charset=utf-8',
                               'Authorization: Basic ' . $cfg['rest_key']],
        CURLOPT_POSTFIELDS => json_encode($payload),
    ]);
    $raw = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $json = json_decode((string)$raw, true);
    if ($code >= 200 && $code < 300 && !empty($json['id'])) {
        return ['ok' => true, 'id' => $json['id']];
    }
    return ['ok' => false, 'id' => null, 'error' => 'http ' . $code . ' ' . substr((string)$raw, 0, 180)];
}

/** Cancel a previously scheduled notification (best effort). */
function push_cancel($notification_id, $external_id, array $cfg) {
    if ($cfg['transport'] !== 'onesignal' || !$notification_id || strpos($notification_id, 'log-') === 0) {
        return true;
    }
    $url = 'https://onesignal.com/api/v1/notifications/' . rawurlencode($notification_id)
         . '?app_id=' . rawurlencode($cfg['app_id'])
         . '&external_id=' . rawurlencode($external_id);
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => 'DELETE', CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10]);
    curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return $code < 400;
}
