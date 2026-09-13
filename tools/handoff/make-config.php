<?php
/**
 * Generates tools/handoff/push-config.php with a FRESH cron key, on your machine.
 *
 * Why this exists instead of committing the file: the repo is public AND your host auto-syncs
 * the whole tree to the web root. Committed secrets get published twice over. (This actually
 * happened on 2026-09-10: a handoff config with a live PUSH_CRON_KEY landed on raw.githubusercontent.)
 *
 *   php tools/handoff/make-config.php            # writes the file, prints nothing secret
 *   rm tools/handoff/push-config.php             # after you finish the setup
 */
$key = bin2hex(random_bytes(16));
$tpl   = __DIR__ . '/push-config.template.php';
$out   = __DIR__ . '/push-config.php';
if (!is_readable($tpl)) { fwrite(STDERR, "template missing: $tpl\n"); exit(1); }
if (file_exists($out)) { fwrite(STDERR, "already exists (delete it first): $out\n"); exit(1); }
$s = file_get_contents($tpl);
$s = str_replace('__CRON_KEY__', $key, $s);
file_put_contents($out, $s);
echo "wrote $out\n";
echo "cron key: $key   <- paste into your hPanel cron URL only; this file is untracked\n";
