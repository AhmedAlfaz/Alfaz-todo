<?php
/**
 * ABDO push sender — shared config.
 *
 * INSTALL: copy this file to `push-config.php` on the Hostinger server and fill it in.
 * `push-config.php` must NOT be committed to git and must NOT be pasted into chat.
 * The client (index.html) never sees any of these values except ONESIGNAL_APP_ID.
 */

// ---- OneSignal (web push) ----
define('ONESIGNAL_APP_ID', '');      // public; index.html uses the same value
define('ONESIGNAL_REST_KEY', '');    // server-side only. Creating it = accepting that this file holds a send-to-everybody secret.

// ---- Transport ----
// 'onesignal' -> real delivery. 'log' -> writes payloads to queue/transport.log and
// marks them sent. 'log' exists so the queue mechanics can be tested without keys.
define('PUSH_TRANSPORT', 'log');

// ---- Storage ----
// Keep this OUTSIDE the web root: the queue holds your users' notification copy.
// Verified doc root on this host is
//   /home/u136736209/domains/firebrick-sardine-612688.hostingersite.com/public_html
// so a sibling directory is one ../ away and unreachable over HTTP:
define('PUSH_DIR', dirname(__DIR__, 2) . '/abdo-push/queue');
// dirname(__DIR__, 2) from public_html/push = the domain folder. If that ever resolves
// somewhere unwritable, push-check.php will say so; fall back to __DIR__ . '/queue'
// only if you must (push/.htaccess denies that path over HTTP as a second line).

// ---- Per-device write token ----
// The client proves it owns its schedule queue with a token issued once per device.
// Keep this secret stable across redeploys; rotating it invalidates every device's
// queue (they re-sync on next open, so it is survivable).
define('PUSH_TOKEN_SECRET', '');      // any long random string, e.g. 40 chars

// ---- Cron guard ----
// GitHub Pages serves .php as plain text, and a public host is a public host: without this,
// anyone can GET push-cron.php as fast as they like. Set this to any random string and give
// cron the URL with ?key=<that string>. Requests without it are refused before any work.
define('PUSH_CRON_KEY', '');

// ---- Behaviour ----
define('PUSH_WINDOW_MIN', 15);        // cron sends anything due in the next N minutes.
                                      // Must be >= your cron interval. 15 covers a 5- or 15-min cron.
define('PUSH_TZ', 'Africa/Cairo');     // used only for logging; send_at is sent as epoch seconds
define('PUSH_MAX_EVENTS_PER_USER', 120); // 7 days x 5 prayers + tasks; guards against a runaway client
define('PUSH_MAX_BODY', 240);          // chars; clamps user-titled task text into a notification
date_default_timezone_set(PUSH_TZ);
