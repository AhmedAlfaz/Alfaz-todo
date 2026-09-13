<?php
/**
 * ABDO push sender — transport layer.
 * Kept separate so the queue logic can be tested without touching OneSignal.
 */

function push_config() {
    static $cfg = null;
    if ($cfg !== null) return $cfg;
    // ABDO_PUSH_CONFIG lets a host (or a test harness) point at a config outside the web root.
    $env = getenv('ABDO_PUSH_CONFIG') ?: (dirname(__DIR__) === '/' ? __DIR__ . '/push/push-config.php' : __DIR__ . '/push/push-config.php');
    $candidates = array_values(array_filter([$env, __DIR__ . '/push-config.php', __DIR__ . '/push-config.example.php'], 'is_readable'));
    if (!$candidates) {
        throw new RuntimeException('ABDO push: no config found (copy push-config.example.php to push-config.php)');
    }
    require_once $candidates[0];
    $cfg = [
        'app_id'    => ONESIGNAL_APP_ID,
        'rest_key'  => ONESIGNAL_REST_KEY,
        'transport' => PUSH_TRANSPORT,
        'dir'       => PUSH_DIR,
        'secret'    => PUSH_TOKEN_SECRET,
        'window'    => (int)PUSH_WINDOW_MIN,
        'max_events'=> (int)PUSH_MAX_EVENTS_PER_USER,
        'max_body'  => (int)PUSH_MAX_BODY,
        'app_id'   => defined('ONESIGNAL_APP_ID') ? ONESIGNAL_APP_ID : '',
    ];
    if (!is_dir($cfg['dir'])) @mkdir($cfg['dir'], 0750, true);
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
