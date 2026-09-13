<?php
// ABDO push sender config. Save as: public_html/push/push-config.php
// Only ONE line needs your input: the REST key (line 8).

define('ONESIGNAL_APP_ID',  '1d96cd6b-a496-4572-adfa-e3e35fde235b');
define('ONESIGNAL_REST_KEY', '');            // <-- PASTE YOUR REST KEY BETWEEN THE QUOTES

define('PUSH_TRANSPORT', 'onesignal');       // 'log' = dry run, nothing is delivered
define('PUSH_CRON_KEY',  '__CRON_KEY__');    // must equal the ?key= in your cron command

define('PUSH_TOKEN_SECRET', '');             // leave empty (intended default)
define('PUSH_WINDOW_MIN', 15);
define('PUSH_TZ', 'Africa/Cairo');
define('PUSH_MAX_EVENTS_PER_USER', 120);
define('PUSH_MAX_BODY', 240);

// Keep the queue inside push/, which this host already refuses to serve or execute over HTTP.
// An out-of-root path is nicer in theory, but dirname() levels here are host-specific and
// guessing them silently lands the queue somewhere unwritable - i.e. no reminders, no error.
// If you want it out of the web root, read the absolute path from push-check.php and paste it.
$_q = __DIR__ . '/queue';
if (!is_dir($_q)) { @mkdir($_q, 0750, true); }
define('PUSH_DIR', $_q);

date_default_timezone_set(PUSH_TZ);
