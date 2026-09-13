<?php
/**
 * ABDO push sender — shared config.
 *
 * INSTALL: copy this file to `push-config.php` on the Hostinger server and fill it in.
 * `push-config.php` must NOT be committed to git and must NOT be pasted into chat.
 * The client (index.html) never sees any of these values except ONESIGNAL_APP_ID.
 */

// ---- OneSignal (web push) ----
define('ONESIGNAL_APP_ID', '1d96cd6b-a496-4572-adfa-e3e35fde235b');   // public id, already inside your site-config.json
define('ONESIGNAL_REST_KEY', '');   // THE ONE LINE TO FILL. OneSignal > Settings > Keys & IDs > REST API key.
    // Server-side only: never commit it, never paste it into a chat.
    // It can send to every subscriber you have.

// ---- Transport ----
// 'onesignal' -> real delivery. 'log' -> writes payloads to queue/transport.log and
// marks them sent. 'log' exists so the queue mechanics can be tested without keys.
define('PUSH_TRANSPORT', 'log');   // -> 'onesignal' only after a real notification is confirmed on a phone

// ---- Storage ----
// Keep this OUTSIDE the web root: the queue holds your users' notification copy.
// Verified doc root on this host is
//   /home/u136736209/domains/firebrick-sardine-612688.hostingersite.com/public_html
// so a sibling directory is one ../ away and unreachable over HTTP:
// Two levels up from public_html/push is the domain folder - outside the web root, so the
// queue holding users' notification copy is unreachable over HTTP even if .htaccess is ignored.
// (dirname(x,2) is PHP 7+; this host reports 8.3. If it ever resolves somewhere unwritable,
// push-check.php says so and the fallback below keeps the sender working inside push/.)
$_abdo_q = dirname(__DIR__, 2) . '/abdo-push/queue';
if (!@mkdir($_abdo_q, 0750, true) && !is_dir($_abdo_q)) { $_abdo_q = __DIR__ . '/queue'; @mkdir($_abdo_q, 0750, true); }
define('PUSH_DIR', $_abdo_q);
// dirname(__DIR__, 2) from public_html/push = the domain folder. If that ever resolves
// somewhere unwritable, push-check.php will say so; fall back to __DIR__ . '/queue'
// only if you must (push/.htaccess denies that path over HTTP as a second line).

// ---- Per-device write token ----
// The client proves it owns its schedule queue with a token issued once per device.
// Keep this secret stable across redeploys; rotating it invalidates every device's
// queue (they re-sync on next open, so it is survivable).
define('PUSH_TOKEN_SECRET', '');   // OPTIONAL strict mode. Empty = the default, and it is
    // NOT a mistake: the queue token is derived from uid + public app id, so a secret here would
    // have to be duplicated into the PUBLIC site-config.json and would protect nothing.

// ---- Cron guard ----
// GitHub Pages serves .php as plain text, and a public host is a public host: without this,
// anyone can GET push-cron.php as fast as they like. Set this to any random string and give
// cron the URL with ?key=<that string>. Requests without it are refused before any work.
define('PUSH_CRON_KEY', '__CRON_KEY__');   // replaced by make-config.php with a fresh key

// ---- Behaviour ----
define('PUSH_WINDOW_MIN', 15);        // cron sends anything due in the next N minutes.
                                      // Must be >= your cron interval. 15 covers a 5- or 15-min cron.
define('PUSH_TZ', 'Africa/Cairo');     // used only for logging; send_at is sent as epoch seconds
define('PUSH_MAX_EVENTS_PER_USER', 120); // 7 days x 5 prayers + tasks; guards against a runaway client
define('PUSH_MAX_BODY', 240);          // chars; clamps user-titled task text into a notification
date_default_timezone_set(PUSH_TZ);
