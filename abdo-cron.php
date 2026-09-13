<?php
/**
 * Cron trigger, web-root shim for the same reason as abdo-sync.php.
 * Prefer running push/push-cron.php from the shell (no HTTP surface at all):
 *   php -f $HOME/domains/<site>/public_html/push/push-cron.php
 * This file is the fallback when only wget-cron is available. It is key-gated by PUSH_CRON_KEY,
 * and refuses everything when that key is unset, so an unconfigured host cannot be driven by
 * strangers. Source stays private in push/.
 */
require __DIR__ . '/push/push-cron.php';
