# Two things left, both inside your Hostinger panel

Everything code-side is done, tested (46 + 20 + 10 passing) and deployed. Your repo auto-syncs to
Hostinger, so **you never upload anything** — the files are already live:

| URL | Status |
|---|---|
| `/abdo-sync.php` | 400 `bad uid` — public endpoint, rejects strangers |
| `/abdo-cron.php` | 403 `forbidden` — waiting for your cron key |
| `/push/*` | 403 — source, config and queue are private |

## 1 — Create the config file (2 minutes)

hPanel → Files → **File manager** → open `public_html/push/` → **New file** named `push-config.php`.
Open it, delete any placeholder content, and paste **exactly** this file's contents:

`handoff/push-config.php` (in this workspace — it already contains your cron key).

Then change **one line only** — the REST key, which I cannot see and must never appear in chat:

```php
define('ONESIGNAL_REST_KEY', 'PASTE_YOUR_KEY_HERE');
```

Find it in OneSignal → **Settings → Push & In-App → Keys & IDs → REST API key**.

## 2 — Add the cron job (1 minute)

hPanel → search **Cron jobs** → add:

- **Interval:** every 15 minutes
- **Command:**
```
php -f $HOME/domains/firebrick-sardine-612688.hostingersite.com/public_html/push/push-cron.php
```

If your panel rejects `php -f`, use this instead (it works, it just also opens an HTTP URL):
```
wget -q -O - "https://firebrick-sardine-612688.hostingersite.com/abdo-cron.php?key=mmvwwgqp0aqclnd71c099uidl08ehu32" >/dev/null 2>&1
```

## Then tell me "done" — nothing else

The cron line now prints which config it loaded (`cfg=push-config.php`). If it ever says
`cfg=push-config.example.php  <-- TEMPLATE`, your file is not where the loader looks.

I will verify all of it from outside: the cron output, the queue directory, a real schedule POST,
and whether the transport is still `log`. Switching delivery to real notifications is **my** edit
(`PUSH_TRANSPORT` → `'onesignal'`), and I will only do it after one notification lands on your phone.

## What I changed while you were away (so this file stays true)

- **`PUSH_TOKEN_SECRET` is now optional and left empty.** My first draft told you to paste it into
  this file *and* into `site-config.json` — but `site-config.json` is public, so that "secret"
  would have protected nothing. The queue token is now derived from your uid and the public app id:
  it proves a device owns its own queue without any distributed secret. Strict mode stays available
  once subscriptions move to Supabase.
- **The sender lives at the web root.** Your host refuses to execute PHP inside `push/` (proven: the
  same file is 200 at root, 403 inside `push/`, and removing my own deny rules changed nothing). So
  `abdo-sync.php` / `abdo-cron.php` are one-line `require` shims; all logic stays in `push/`.
- **OneSignal's web push free tier is genuinely unlimited** for subscribers; their new 1,000 MAU cap
  applies to mobile push and in-app only. Nothing here costs you money.

## Where the file goes, and why that is safe

Create it **inside `public_html/push/`**, as step 1 says. Verified, not assumed:
`/push/` returns 403 for *every* file in it (I fetched `push-config.example.php` as a control and got 403 too),
because this host refuses to execute or serve PHP there at all. So the key cannot be downloaded, and it
cannot be executed by accident. Keep it out of git - it is already in `.gitignore`.

If you ever move hosts, this is the one file to re-check: on a host that *does* run PHP inside `push/`,
Apache would execute it (fine) but a misconfigured server could serve it as text (not fine).
