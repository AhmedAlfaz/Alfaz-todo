# ABDO — Web Push (VAPID) Plan

**Status:** awaiting CEO approval — no code written yet
**Author:** PM/implementation assistant · 2026-09-10
**Builds on:** v39 (live, phone-verified by Ahmed)
**Goal:** make the word *reminder* in our app name true. Today an alarm only fires if the page is open.

---

## 1. The problem, measured — not remembered

Verified in `sw.js` and `index.html` at v39:

| Check | Result | Meaning |
|---|---|---|
| `addEventListener('push'` in sw.js | **0** | nothing wakes the app from a push |
| `pushManager` / `subscribe(` / `vapid` | **0** | we never create a push subscription |
| `registration.showNotification` | **0** | notifications come from the *page*, not the worker |
| `requestPermission` in index.html | 4 | we ask permission, then use it only while open |
| Alarm engine | 3 × `setInterval` in page | **dies when the tab/app dies** |

**Consequence:** if a user swipes ABDO away at 23:00, Fajr never calls them. Every
competitor's headline feature is precisely this one. Our rating gap in one line:
notifications score 1.5/5 vs their 5/5.

The fixable part: **Android delivers real Web Push to installed PWAs even when the app is
closed** — no app store, no Firebase, no APK. Per a March 2026 field report, fixing VAPID
configuration + payload encryption took one team's delivery rate from **60% → 97%**
([edana.ch](https://edana.ch/en/2026-03-19/push-notifications-on-web-applications-pwa-is-it-really-reliable-on-ios-and-android/)).

## 2. The constraint nobody mentions in the pitch

Web Push is **server → endpoint**. ABDO has **no server**: GitHub Pages is static, Hostinger
is static file uploads. We cannot sign a push from inside a browser — the VAPID private key
would be public and anyone could spam our users.

So the plan is really: **how do we get a sender for ~0 EGP/month and ~0 extra maintenance?**

### Three architectures considered

| | A. OneSignal web push | B. Pure DIY VAPID | C. Firebase Web Push + FCM |
|---|---|---|---|
| Free for us | **Yes** — "unlimited web push subscribers"; the new 1,000 MAU cap hits *mobile* push/in-app only, web push explicitly unaffected ([OneSignal](https://onesignal.com/blog/which-onesignal-plan-is-best-for-you/)) | Yes | Yes |
| Encrypted payload (aes128gcm) | done for us | we implement HKDF/AES-GCM/p-256 in PHP — the exact thing that broke the 60% case above | done for us |
| Scheduling to an exact minute | `send_at` in the API | our own cron must fire at :00 | Cloud Tasks / cron |
| Delivery analytics | dashboard | none | console |
| iOS push | works via their relay | needs a relay of our own | native-ish |
| New secrets to guard | appId (public) + REST key (server) | VAPID keypair | service account JSON |
| Vendor risk | they change pricing | none | Google ToS, app-store-adjacent |
| Effort | **Low** | High | Medium |

**Recommendation: A (OneSignal web push) as the delivery pipe, with B kept as the escape
hatch.** Rationale: A costs nothing at our size, removes the crypto-failure class of bug,
gives us a delivery dashboard to prove it works, and we can leave it later by swapping one
endpoint. Choosing B first is where single-person projects die.

### The sender for per-user schedules

Push must arrive at *this user's* Fajr, which is a per-user time. One broadcast can't do it.
Two ways:

- **A1 (recommended): per-user `send_at` scheduling.** Client computes its own next-7-days
  schedule and pushes it to a tiny script. Script creates OneSignal notifications targeted at
  *that user's* subscription with exact `send_at`. OneSignal then delivers at the exact minute
  — our 5-minute cron granularity stops mattering.
- **A2 (simpler fallback): 5-minute cron sweep.** Script scans all due events each run and
  sends immediately. Delivery lands up to ~5 min late.

**Where the script lives:** the **Hostinger** PHP + cron we already own (hPanel → Cron Jobs
runs `wget -q -O - <url>`, standard on their shared plans). GitHub Pages **cannot** run
scripts — do not plan anything there. If the Hostinger plan has no cron/PHP, A1 degrades to
A2 with an OS-level cron, or we move the sender to a Cloudflare Worker (also free, 15-min
min). Needs a 2-minute check in hPanel before build.

**Where subscriptions/schedules live:** Supabase (already wired, already authed). New tables
`alfaz_push_subs`, `alfaz_push_queue`, RLS locked to `auth.uid()`.

## 3. Honest limits (read this before promising anyone anything)

1. **Must be installed.** Web Push only reaches installed PWAs. We have `beforeinstallprompt`
   for Android; iOS is manual Share → Add to Home Screen, no auto prompt
   ([deepclick](https://deepclick.com/resources/blog/progressive-web-apps-on-ios/)). We also
   currently have **zero** standalone detection (`display-mode: standalone` → 0 occurrences) —
   needed so we never nag a non-installable visitor.
2. **iOS in the EU is a dead end.** Since iOS 17.4, Apple removed standalone PWA mode for EU
   users → **no push, no standalone** ([zylos](https://zylos.ai/en/research/2026-02-04-progressive-web-apps/)).
   Egypt/US/Gulf users unaffected. EU users keep the current in-app path and must be told so,
   quietly, in settings — not surprised.
3. **No full-screen alarm from a push.** A push shows a notification. Our beautiful azan
   audio + alert modal still only runs when the page is open. Keep the in-app engine as the
   *premium* path; push is the safety net.
4. **Android OEM battery killers** (MIUI, Samsung aggressive standby, Huawei) throttle web
   apps hard. Needs a "don't optimize ABDO" one-tap deep link into battery settings.
5. **iOS evicts unused PWA storage** after extended disuse — data *and* the install
   ([deepclick](https://deepclick.com/resources/blog/progressive-web-apps-on-ios/)). Reinforces the
   case for Supabase sync of plans/tasks.
6. **Origin-scoped.** A subscription on `ahmedalfaz.github.io` does not work on
   `firebrick-sardine-…hostingersite.com`. Each origin needs its own OneSignal app config and
   its own key in the env. Test on GitHub Pages, ship on Hostinger, never assume one covers the other.
7. **Privacy trade-off.** OneSignal holds subscription endpoints. It's an unavoidable third
   party for free push. Mitigations: nothing but app-scoped data, no email/IP collection
   enabled, and a **kill switch** so a privacy-minded user can turn push off entirely (§6.6).

## 4. Tiers — each ships and is verifiable alone

### Tier 0 — Prereqs (Ahmed, ~20 min, no code)
- [ ] Create OneSignal account → new **Web Push** app (name: `ABDO-Hostinger`).
- [ ] Confirm in hPanel: **Cron Jobs** exists + PHP version ≥ 8.1 on your plan.
- [ ] Decision: keep the free Hostinger subdomain, or connect your own domain? (A real domain
      is more trustworthy to share and gives us a stable origin. Recommended, not required.)
- [ ] I need: `app_id` (public, safe to embed) only. **Never** the REST key in chat — it goes
      into a file you upload or a secret I write for you to paste into hPanel.

### Tier 1 — The pipe (make a push arrive while the app is closed)
- `onesignal/OneSignalSDKWorker.js` (their file, hosted by us — no CDN dependency) +
  `importScripts('onesignal/OneSignalSDKWorker.js')` **inside our `sw.js`**, so one worker owns
  both cache and push. OneSignal init uses explicit
  `serviceWorkerPath: 'onesignal/OneSignalSDKWorker.js'` / `serviceWorkerParam: { scope: 'onesignal/' }`
  — supported and documented for sites with an existing worker
  ([OneSignal docs](https://documentation.onesignal.com/docs/en/vue-js-setup)).
- `enablePush()` behind a user tap; store `external_id = user id | device token` in Supabase.
- `push` listener in `sw.js`: parse payload, decide **notify vs silent** (see 4.3), show with
  icon `brand/abdo-icon-192-wb.png`, `renotify`, `tag` for dedupe, deep link to `#/prayers`.
- Verification: send from the OneSignal dashboard → **app fully swiped away** → notification
  arrives on an Android phone. This is the demo that either works or the plan is dead.

### Tier 2 — Permission UX with zero annoyance
- Soft-ask banner (our `showToast`/modal style), **only after** the user creates their first
  reminder or enables an azan alert. Never on first launch.
- Two outcomes remembered: `granted`, or `dismissed-soft` → don't ask again for 30 days.
- Standalone gate: if not installed and platform can't push (iOS non-standalone, EU iOS ≥17.4),
  show an inline note in Settings, **no prompt at all**.
- Settings toggle `Push alerts: on/off` + "not working? fix battery optimization" link.
- i18n EN/AR for every string (our `i18n` object is small — it grows with these keys).

### Tier 3 — Prayer + occasion schedules (the headline)
- New `computePushSchedule()` next to existing `fetchPrayerTimes` / `prayerTimeHHMM`:
  7 days × 5 prayers, per user's lat/lng + method, minus prayers they muted, `+0 min` offset.
- `POST /push-sync.php` with the schedule; script upserts OneSignal `send_at` notifications
  (`existing_player_ids` = that user's `external_id`), idempotent key
  `push:<uid>:<date>:<prayer>` so re-syncs never double-send.
- Occasions: one "tomorrow is …" notice at 20:00 local, from `eventsForIso` — **off by default**
  (zero-annoyance rule).
- Daily re-sync is triggered lazily: on app open, and by the in-app `setInterval` if open.
  A user who opens ABDO once a day gets perfectly timed prayer pushes for a week.

### Tier 4 — Tasks + plans
- `checkTaskReminders` / `checkPlanReminders` already compute exact fire times and already
  guard per-day (`alfaz_plan_rem_<id>_<iso>`). On save, hand that fire time to the same
  `/push-sync.php`; on complete/delete/unlink, cancel it (`schedule_id` stored on the row).
- Repeating plans: `planOccursOnDate` + `planMatchesDate` (already unit-tested 16/16) generate
  occurrences client-side → no recurrence logic in PHP. Keeps the risky math where we have tests.

### Tier 5 — Don't double-notify (our edge over native apps)
- Silent push while the app is visible → page plays the real azan + modal (existing
  `triggerAzan` / `azan-alert-modal`), **no notification**.
- Push while hidden → notification, and `notificationclick` (already in `sw.js`) focuses +
  plays the audio on arrival.
- Same-minute guard reusing `wasAzanFired` + `localStorage['alfaz_prayer_…']`-style keys.
- Result: exactly one alert per event, and the *better* alert for the situation.

### Tier 6 — Prove it, then publish
- Delivery log table (`sent`, `delivered`, `failed_reason`) — OneSignal gives per-message stats;
  7 consecutive days of ≥95% delivered before we call it done.
- 3-device matrix: Samsung/Chrome Android, Pixel, iPhone on the latest iOS (non-EU Apple ID).
- Update `README.md` / `DEPLOYMENT.md`, add `PUSH_SETUP.md` for the one-time config so a future
  contributor isn't locked out.

**Order: 0 → 1 → 2 → 3 → 5 → 4 → 6.** Tier 5 before 4, because double-alerting users is the
one outcome worse than no alerts.

## 5. Effort & risk

| Tier | My build time | Risk | Rollback |
|---|---|---|---|
| 1 | 1 session | Med (origin/SW conflicts) | delete 2 files, revert `sw.js` |
| 2 | small | Low | flag off |
| 3 | 1–2 sessions | Med (PHP + cron + OneSignal API) | stop cron; in-app engine untouched |
| 5 | small | Low | revert |
| 4 | small | Low | revert |
| 6 | ongoing | — | — |

**Nothing here touches the working v39 behaviour.** Worst case (vendor, Hostinger, keys) we
leave exactly where we are today and keep the in-app alarms.

## 6. Decisions — 4 of 6 locked by CEO on 2026-09-10

| # | Question | Decision |
|---|---|---|
| 1 | Delivery | **OneSignal web push** (DIY VAPID kept as documented escape hatch) |
| 2 | Sender | **Hostinger PHP + Cron Jobs — CEO confirms both exist on the plan** |
| 4 | First events | **Prayers + tasks + plan reminders** (Tier 3 + Tier 4). Occasions/“tomorrow is…” and daily digest **deferred** to a later tier, opt-in |
| 5 | Consent | **Soft-ask banner, native prompt only after the user taps it** |
| 6 | Kill switch | **Push OFF by default** until the user opts in; visible toggle in Settings |

**Still open (does not block Tier 1/2):**

3. **Domain:** keep the free `…hostingersite.com` subdomain or connect your own domain before
   we ship push? OneSignal's own web-push guidance is to **use your own domain** — free
   shared subdomains are where web push gets flaky (verification, shared-IP sender reputation,
   and any other tenant on that subdomain). Affects Tier 3+ rollout, not the pipe.

### Build order now that scope is decided
**Tier 0 (you) → 1 → 2 → 3 → 4 → 5 → 6** — Tier 4 moved ahead of 5 only because you asked for
task/plan reminders in the first batch; Tier 5 (no double-notify) still lands **before** we tell
anyone it's done.

### What Tier 0 needs from you, concretely
1. OneSignal → **Create Web Push app** → name it `ABDO-Hostinger` → note the **appId**
   (public, safe in `index.html`).
2. Settings for that app: *Service Worker* → path `onesignal/OneSignalSDKWorker.js`,
   scope `/Alfaz-todo/` on Pages, `/` on Hostinger. Site URL: the exact origin.
3. From **Credentials & Keys**: the **REST API key** → paste it into the Hostinger file
   `push-config.php` (chmod 640). **Not into chat** — same reason as the GitHub token; a REST
   key can send to every subscriber we have.
4. Tell me the **minimum cron interval** hPanel offers you (commonly 5 or 15 min) — decides
   whether Tier 3 uses exact `send_at` scheduling (preferred) or a sweep.

## 6b. Status — 2026-09-10, after "why don't you just do the move?"

| Item | State |
|---|---|
| Hostinger storefront on v39 | **verified live** (`sw.js` → `CACHE_NAME = 'alfaz-todo-v39'`, 200) — no manual redeploy was needed, my earlier assumption was stale |
| Stale prayer-times fix + dead `alfaz-prayer-v1` cleanup | **built as v40**, `tools/test_v40_stale.py` 10/10 in real Chromium (EN + AR + RTL + legacy-cache + online paths) |
| Sender: `push/push-lib.php`, `push-sync.php`, `push-cron.php`, `push-config.example.php`, `.htaccess`, `README.md` | **built and tested**, `tools/test_push_php.py` 16/16 against the real PHP endpoints (auth, idempotency, cancel-on-drop, retry-once, path traversal, opt-out) |
| Tier 1 client wiring (`index.html`, `sw.js`, soft-ask UI) | **not written on purpose** — needs a real OneSignal `appId` + their SDK worker; anything else is untestable code that looks finished |

Two things that came out of building rather than planning:
- `mb_substr()` **fatals** when PHP lacks mbstring, which would have taken the whole endpoint
  down on a shared host. Now `push_cut()` with a `preg_split('//u')` fallback.
- Re-syncing the same schedule must reuse OneSignal's `name` (idempotency key) or every daily
  app open would create a **second** Fajr alert. Covered by test 3a/3b.

## 7. Open questions I will verify during build, not assume

- OneSignal `send_at` + per-player targeting from the REST API on the **free** web plan (docs
  say yes; will prove with a 2-minute-later test notification before writing the sync logic).
- Minimum cron interval on your Hostinger plan, and whether `file_get_contents`/curl outbound
  from PHP is allowed (some plans disable it; `allow_url_fopen` check first).
- Whether `importScripts` of their worker inside ours survives our `activate` cache-cleanup
  filter (`sw.js` currently keeps `alfaz-todo-*` + `alfaz-prayer-v1`).
- Exact iOS standalone/EU detection we can rely on in WebKit (`display-mode` query + UA).
- Supabase RLS policy for `alfaz_push_subs` for **guest** users (device-token keyed, not uid).

---

### Note for the record
`sw.js` references a cache `alfaz-prayer-v1` it protects from deletion, but no code in
`index.html` ever writes it (prayer times live in `localStorage['alfatore_prayers_<date>']`).
Dead reference — worth deleting in the same pass. Separately, prayer times are cached
**per-day only**, so opening the app offline on a new day silently shows **yesterday's** times;
recommended follow-up (any tier, ~15 lines): label stale times visibly. Silent staleness in a
religious obligation is our worst failure mode.
