<?php
/**
 * Public entry point for the ABDO push sender.
 *
 * It exists ONLY because this host refuses to execute PHP inside push/ (verified: the same file
 * returns 200 at the web root and 403 in that folder). All logic stays in push/push-sync.php,
 * and that folder is deny-all over HTTP, so no source or secret is exposed by this shim.
 * Do not add logic here - it defeats the .htaccess protection.
 */
require __DIR__ . '/push/push-sync.php';
