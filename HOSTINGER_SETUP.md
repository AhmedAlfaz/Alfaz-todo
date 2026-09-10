# Your Hostinger setup — one step at a time

Nothing here is config work. You open a page, you click a number, you copy a line, you paste me
the result. If a step looks different from what I wrote, stop and send me a screenshot — do not
guess, and do not let anyone "fix" it for you.

**Do not paste into chat:** your Hostinger password, and the OneSignal REST key. Everything else
in this document is safe to paste.

---

## STEP 0 — protect the work first (2 minutes, do this before anything else)

Download the zip I made you: `backups/ABDO-v40-cdc01a8-20260910.zip` (24 MB, 45 files, verified:
`index.html` and `push/*` inside it are byte-identical to the repo, all 13 azan files included).
Check it matches: `sha256 = ec0fff99b06a2bd41db385d8bcb528b7a452ad5bb077719ff6be8880a63ec59b`.

Put it somewhere that is not this computer — Google Drive, a USB stick, email it to yourself.
**That file is the whole project.** GitHub was never the backup, and it still isn't.

---

## STEP 1 — ship the v40 fix (your usual move, 5 minutes)

This is the one that makes the app *better for users today*: prayer times loaded offline on a new
day used to look like fresh ones. Now they say how old they are. Already built, 10/10 in a real browser.

1. Upload **two** files to Hostinger, replacing the current ones, in `public_html`:
   - `index.html`
   - `sw.js`
2. Open `https://firebrick-sardine-612688.hostingersite.com/sw.js` in your browser.
   You should see `CACHE_NAME = 'alfaz-todo-v40';`. That's the whole verification.
3. On your phone: open the app, go to Prayers, close it, reopen. Nothing should look broken.

Do **not** upload `manifest.json`, `brand/`, `audio/` — unchanged since your last upload.

---

## STEP 2 — ask your hosting one question, without guessing

1. hPanel → **Files** → **File manager** → open the `public_html` folder.
2. Make a folder inside it named `push`.
3. Put **these 6 files** inside `public_html/push/` (from the zip's `push/` folder):
   `push-lib.php`, `push-sync.php`, `push-cron.php`, `push-config.example.php`, `push-check.php`, `.htaccess`
4. Open `https://firebrick-sardine-612688.hostingersite.com/push/push-check.php`
5. **Copy the entire page and paste it to me.** No secrets on it — that's by design.

I need this page before you touch anything else, because shared hosting sometimes disables the PHP
functions this relies on, and I'd rather know now than after you've spent an hour.

---

## STEP 3 — one file, one edit (only after I read STEP 2)

1. In the same `push` folder: right-click `push-config.example.php` → **Copy** → rename the copy to
   `push-config.php`.
2. Right-click `push-config.php` → **Edit**, and change exactly three lines:

| Line | Change it to |
|---|---|
| `define('PUSH_TRANSPORT', 'log');` | leave as `'log'` for now (dry run, nothing reaches a phone) |
| `define('PUSH_TOKEN_SECRET', '');` | paste **this** string (already generated for you, safe to keep in the open — see note below):
     `7d8iyja11f12o3te7o6zsz69ky154d9luy6eywpqse9v` |
| `define('PUSH_DIR', __DIR__ . '/queue');` | leave as-is for now |

`PUSH_TOKEN_SECRET` = `7d8iyja11f12o3te7o6zsz69ky154d9luy6eywpqse9v`

It is a throwaway key that stops strangers writing to your queue. Paste it, do not invent one. It is
fine that this string is sitting in a document and in chat: it can only *append notifications to one
user's own queue*, and if it ever worried us I regenerate it in one line and every device re-syncs
itself on next open. It is not a password and it unlocks nothing on your account.

3. Save. Re-open `.../push/push-check.php`. It should now say `push-config.php found` and
   `dry run` and `Queue dir: writable`. Paste me that page again.

---

## STEP 4 — the schedule line (1 minute)

1. hPanel → search for **Cron Jobs** (it's under *Advanced* in most layouts).
2. Add a cron job:
   - **Interval:** every 15 minutes
   - **Command:**
     ```
     wget -q -O - "https://firebrick-sardine-612688.hostingersite.com/push/push-cron.php" >/dev/null 2>&1
     ```
3. Save, then open `https://firebrick-sardine-612688.hostingersite.com/push/push-cron.php` in your
   browser and tell me the single line it prints. It should look like:
   `abdo-push-cron 2026-09-10T… files=0 sent=0 failed=0 pruned=0 transport=log`

That line means the engine is alive and installed. **No user gets anything yet** — that is
deliberate; we only turn delivery on once the queue is proven.

---

## STEP 5 — what's left after that (and it's mine, not yours)

Only two things, and neither is fiddly:
1. **OneSignal account** → create a "Web Push" app → copy me the **appId** (public, safe to paste).
   That's the last account any part of this project needs.
2. I write the app side (the "want alerts?" prompt + subscribe), we test one real notification on
   your phone, and *then* you flip `PUSH_TRANSPORT` to `'onesignal'` and paste the REST key into
   the same file. That key is the only genuinely secret thing in this whole setup, and it never
   leaves that file.
3. Delete `push-check.php` when we're done.

---

## If you get stuck

Say which step number and send a screenshot. Don't do any of these:
- install a WordPress plugin to "help" (wrong system, will fight the service worker)
- let Hostinger support edit `index.html`
- paste the REST key, your hosting password, or a GitHub token into any chat, including ours
- upload anything into `2/` (that folder is deliberately out of scope)
