# ABDO push sender — Hostinger side

Small PHP queue + cron worker that delivers scheduled prayer / task / plan alerts through
OneSignal web push. It exists because a browser cannot sign a push (the VAPID private key
would ship inside `index.html` and anyone could broadcast to every install).

**Nothing here runs today.** Tier 1 needs a OneSignal app (see `../WEB_PUSH_PLAN.md` §Tier 0)
before any client code is wired to it.

## Files

| File | Role |
|---|---|
| `push-lib.php` | config load, per-device token sign/verify, queue paths, transport, cancel |
| `push-sync.php` | one POST per device: replace that device's whole schedule (idempotent) |
| `push-cron.php` | cron worker: dispatches anything due inside the window, prunes what is done |
| `push-config.example.php` | template. Copy to `push-config.php`, never commit it |
| `queue/` | created at runtime: `user-<uid>.json` + `transport.log`. Deny-served via `.htaccess` |

## Deploy

1. Upload the whole `push/` dir to Hostinger. **Preferred:** put `queue/` outside `public_html`
   (`/home/uXXXX/abdo-push/queue`) and set `PUSH_DIR` to that path — the queue holds your users'
   notification copy, and the `.htaccess` deny rule is only insurance against a LiteSpeed quirk.
2. `cp push-config.example.php push-config.php` and fill:
   - `ONESIGNAL_APP_ID` (same public value the client uses)
   - `ONESIGNAL_REST_KEY` — **server-side only.** Never in chat, never in `index.html`, never committed.
   - `PUSH_TOKEN_SECRET` — any long random string. This is what makes `/push/push-sync.php`
     unwritable by strangers, so treat it as a real secret.
   - `PUSH_TRANSPORT` → `'log'` first, `'onesignal'` only after a green dry run.
3. hPanel → Cron Jobs (every 5 or 15 min, must be ≤ `PUSH_WINDOW_MIN`):
   ```
   wget -q -O - "https://YOUR-DOMAIN/push/push-cron.php" >/dev/null 2>&1
   ```
4. Smoke test in order — and note what each answer *means*, because the previous version of this
   file hid a real failure behind a "looks protected" 403:
   - `curl -I https://YOUR-DOMAIN/push/onesignal/OneSignalSDKWorker.js` → **must be 200**. OneSignal's
     browser code fetches this; if it 403s, web push cannot register and every user silently keeps
     no reminders. (A blanket `Require all denied` in `push/.htaccess` caused exactly that.)
   - `curl https://YOUR-DOMAIN/push/push-lib.php` → must be **403** (source must not be downloadable)
   - `curl -d '{}' https://YOUR-DOMAIN/push/push-sync.php` → must be **403 from Apache** (blocked path)
     or `bad token` if you un-block it; either way strangers cannot write.
   - `curl 'https://YOUR-DOMAIN/push/push-cron.php?key=YOUR_KEY'` → prints `abdo-push-cron … sent=0`.

## Design rules this code enforces (each has a test)

- **A device can only rewrite its own queue.** HMAC token derived from `uid` + secret (§1a).
- **Never queue the past.** Client clock drift can't produce a surprise at 3am (§6a).
- **Re-sync is idempotent.** Same schedule → same OneSignal `name`, no second copy (§3a/3b).
  This is the bug that would have made every daily open send two Fajr alerts.
- **Cron sends once.** A retry never duplicates an alert; a permanently failing event dies after
  2 attempts and is logged (§4b).
- **`ttl: 3600`.** If cron is down, an alert is dropped, not delivered six hours late. For prayer
  times a late alert is worse than none.
- **Cancel on drop.** Unchecking a reminder removes it from the queue (§5a); opting out empties it (§8a).

## Verify before deploying (no OneSignal account needed)

```bash
python3 tools/test_push_php.py     # 16 checks: auth, idempotency, cancel, retry-once, traversal, opt-out
python3 tools/test_v40_stale.py    # 10 checks: app-side prayer-times staleness + legacy cache shape
```

Requires `php` (any 8.x) and Chromium + `playwright` for the second one. The PHP test starts its
own throwaway server on a random port and refuses to run if it is not talking to the server it
started — it once reported 5 fake failures because a leftover server answered instead.

## Not done on purpose

- **Client wiring** (`index.html`, `sw.js` import, soft-ask UI): blocked on Tier 0. Writing it
  against a placeholder appId would be untestable code.
- **Real OneSignal transport**: unverified until a live `send_at` notification proves the free
  plan allows per-player scheduling. Flagged in `WEB_PUSH_PLAN.md` §7 as a build-time unknown.
- **Supabase RLS tables**: the queue is file-based for the MVP; per-plan §Tier 3 that is
  acceptable because it holds no account data, only copy for the next 7 days.
