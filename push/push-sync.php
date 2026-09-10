<?php
/**
 * ABDO push — client sync endpoint.
 * POST JSON: { uid, token, player?, events: [{id, send_at, title, body, link}] }
 * Replaces that device's whole schedule (idempotent: events not in the payload are cancelled).
 * Called from index.html after prayer times / tasks / plans change. No secrets return to the client.
 */
require_once __DIR__ . '/push-lib.php';
header('Content-Type: application/json; charset=utf-8');
$cfg = push_config();

$in = json_decode(file_get_contents('php://input'), true);
if (!is_array($in)) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'bad json']); exit; }

$uid = (string)($in['uid'] ?? '');
if (!preg_match('/^[A-Za-z0-9_-]{6,64}$/', $uid)) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'bad uid']); exit; }
if (!push_token_ok($uid, $in['token'] ?? null, $cfg['secret'])) { http_response_code(401); echo json_encode(['ok'=>false,'error'=>'bad token']); exit; }

$path = push_queue_path($uid);
if (!$path) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'bad path']); exit; }

$old = is_readable($path) ? (json_decode((string)file_get_contents($path), true) ?: []) : [];
$oldEvents = $old['events'] ?? [];

$incoming = [];
foreach ((array)($in['events'] ?? []) as $ev) {
    if (!is_array($ev) || empty($ev['id']) || empty($ev['send_at'])) continue;
    $id = (string)$ev['id'];
    $sendAt = (int)$ev['send_at'];
    if (preg_match('/^\d{13}$/', (string)$ev['send_at'])) $sendAt = (int)($sendAt / 1000); // client sent ms
    if ($sendAt < time() - 60) continue;                       // never queue the past
    $incoming[$id] = [
        'id'       => substr($id, 0, 96),
        'send_at'  => $sendAt,
        'title'    => push_cut((string)($ev['title'] ?? ''), 60),
        'body'     => push_cut((string)($ev['body'] ?? ''), 300),
        'link'     => substr((string)($ev['link'] ?? './'), 0, 200),
    ];
    if (count($incoming) >= $cfg['max_events']) break;
}

// cancel what the client dropped, keep one-shots already sent
$now = time();
$still = [];
foreach ($oldEvents as $e) {
    $id = $e['id'] ?? null;
    if ($id === null) continue;
    if (isset($incoming[$id])) { $still[$id] = $e; continue; }
    if (!empty($e['nid'])) push_cancel($e['nid'], $e['ext'] ?? $uid, $cfg);
}
foreach ($incoming as $id => $ev) {
    $prev = null;
    foreach ($oldEvents as $o) { if (($o['id'] ?? null) === $id) { $prev = $o; break; } }
    $ext = (string)($in['player'] ?? $uid);
    $row = $ev + ['ext' => $ext, 'attempts' => 0];
    if ($prev !== null && (int)$prev['send_at'] === $ev['send_at'] && !empty($prev['nid'])) {
        // identical schedule re-synced: keep OneSignal's scheduled copy, never re-create it
        $row['nid'] = $prev['nid'];
        $row['pre_sent'] = 1;
        $row['sent'] = $prev['sent'] ?? 0;
    } else {
        if ($prev !== null && !empty($prev['nid'])) push_cancel($prev['nid'], $prev['ext'] ?? $uid, $cfg);
        if ($ev['send_at'] > $now + $cfg['window'] * 60) {
            // Tier 3 exact-time path: hand it to OneSignal's scheduler (send_at) instead of
            // waiting for cron. If cron is 5-min capable this is unnecessary but harmless.
            $r = push_send($ev, $ext, $cfg);
            if ($r['ok']) { $row['nid'] = $r['id']; $row['pre_sent'] = 1; $row['pre_at'] = $now; }
        }
    }
    $still[$id] = $row;
}

$snapshot = [
    'uid'     => $uid,
    'player'  => (string)($in['player'] ?? ''),
    'sync_at' => $now,
    'events'  => array_values($still),
];
if (@file_put_contents($path, json_encode($snapshot), LOCK_EX) === false) {
    http_response_code(500); echo json_encode(['ok'=>false,'error'=>'write failed']); exit;
}
echo json_encode(['ok'=>true, 'queued'=>count($still), 'transport'=>$cfg['transport']]);
