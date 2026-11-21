# ABDO — Session Report & Plan

**Date:** 2026-11-21 · **Branch:** `arena/56b587ab-alfaz-todo` (base: `main` @ `9ece8ba`)
**Delivered:** v52 → v54, four commits · **Verified:** gates green, 44 jsdom checks, 321 time-logic assertions

---

## 1. The decision you made, and what it changed

You asked why a web host still needed Supabase. The answer was that it didn't — the app had always
been local-first, and Supabase was an optional extra that was also the source of both open bugs
(Google/Apple sign-in unconfigured, Groups tables missing). You chose **local-only**, and the whole
session follows from that.

**What that bought:** no dashboard configuration, no OAuth credentials, no SQL, no free-tier pause,
no server to maintain — and both bugs simply cease to exist rather than get fixed.

**What it cost:** the device became the only copy of the data. That is why the backup feature is not
a nice-to-have in this build; it is the recovery story.

---

## 2. What shipped

### v52 — remove the cloud layer, add real backups (`96de940`)

| Removed | Added |
|---|---|
| Supabase CDN loader + client (anon key out of the bundle) | **Backup & Restore**: `abdo-backup-YYYY-MM-DD.json`, versioned schema |
| Sign-in / sign-up / logout / session check | Import validation: refuses foreign files, allow-list only, replace-not-merge |
| Groups tab and its tables | **Local IDs** for tasks + plans (the DB used to assign them) |
| 19 `syncTask` call sites | Schema v4 migration clearing the dead Supabase session |
| — | Chosen azan sound now persists (it reset to Makkah every launch) |
| — | 22 i18n keys that rendered blank, Arabic plan actions, `data-i18n-aria-label` support |

Boot no longer waits on a CDN round-trip, so first paint is faster and cannot fail offline.

### v53 — the defects the plan review found (`4c3bd1d`)

Every one of these was live and silent before this commit.

| Defect | Was doing | Now |
|---|---|---|
| Monthly on the 31st | No occurrence in Feb/Apr/Jun/Sep/Nov | Clamps to the last existing day |
| Yearly on Feb 29 | No occurrence in 3 of 4 years | Same clamp, interval respected |
| 23:45 reminder | Never fired if app opened at 00:05 | 90-min overnight grace |
| "15 min before" | Fired from 08:45 **to 09:44** | Exact minute + 30-min grace |
| Snooze | Rewrote `due_time` — rescheduled the task | `snooze_until`; `due_time` untouched; push client honours it |
| Plan reminder, no time | Fired at a made-up 09:00 | Modal requires a time |
| Prayer times | No timezone → every line shifted after travel | Zone + coords stored, converted to device clock, re-fetch on >25 km move |
| Repeating plan marked done | Hid **every future occurrence** | Completion is per-occurrence |
| Editing a plan | Erased fields the form doesn't own | Merges instead of replacing |

### v54 — the last two plan items (`2adebdb`)

- **Cache split:** Quran ayah HTML, ayah timestamps and prayer entries moved from the 5 MB
  `localStorage` bucket into IndexedDB (`abdo-cache`). Synchronous in-memory mirror, automatic
  migration, prune rules (prayer entries >7 days, ayah cache capped at 80), and a working fallback
  in private mode. **User data never moved** — tasks, plans and settings are exactly where they were.
- **Multi-tab safety:** a `storage` listener adopts changes from other tabs; a resume handler
  re-syncs after the tab wakes; clearing site data shows one explanatory toast instead of a
  silently empty list.
- Backup & Restore now reports the cache (items, KB, where it lives) so "your data" and
  "regenerable" are visibly different.

### The safety net (what stops a repeat)

| Gate | Catches |
|---|---|
| `tools/test_planner_time.py` | 321 assertions, 7 runs, 5 timezones — recurrence, reminders, timezone, per-occurrence completion |
| `tools/gates.py` → i18n check | Any `data-i18n*` / `i18n[x].key` with no EN or AR string |
| `tools/gates.py` → time suite | Any regression in the above, as a build failure |
| jsdom suites (44 checks) | Boot with zero network, task/plan CRUD, backup round-trip, cache store, storage events |

---

## 3. Honest status

**Verified:** gates green; 28-check smoke suite; 16-check storage suite; time suite in 5 zones.
**Not verified:** the visual layout on a real phone. There is no Chromium in this sandbox, so
nothing has been seen rendered since v51. **That is the one check only you can do.**

**Also true:** the existing `tools/test_sw_atomic.py` needs Playwright + Chromium and was not run
here. `gh` can create issues on this repo but cannot comment on or edit them (token lacks
`issues: write`).

---

## 4. What is still open

| Item | Why it is open | Cost |
|---|---|---|
| **Visual check on a phone** | No browser in the sandbox | 10 min of your time |
| **Timeline (plan step 5)** | Waits on the §9 decisions below, not on code | 2–3 sessions |
| **`renderGroups` stub** | Groups were removed; nothing references it | 0 (dead code, harmless) |
| **Diff rendering in the timeline** | Arrives with step 5 | part of step 5 |

---

## 5. The plan from here

### Now — before anything else
1. **You check v54 on a phone** (top-level domain, not the preview iframe — file downloads are
   blocked in iframes, so Backup & Restore cannot be tested in the preview).
2. Merge the PR once you're happy; Hostinger auto-deploys `main` within ~30s.

### Next session — the timeline, if you approve the four decisions
The plan's §9 questions, with my recommendations:

| Question | My recommendation |
|---|---|
| Time model | Integer day numbers as canonical (`isoToDay` already landed in v53) — keep `Date` only at the edges |
| Month-end rule | Clamp (already shipped and tested) |
| Occurrence identity | `(plan_id, iso)` until snoozing an occurrence is requested; that is when materialised rows earn their cost |
| Task duration on the timeline | **Points, not blocks**, unless the user sets `estimate_min` — an honest dot beats a wrong block |

Once those are settled the build order is: `buildDayTimeline()` pure function → Day view → overlap
lanes → `estimate_min` editing. Each step is shippable and testable on its own.

### Deliberately not doing
Folders/subtasks, drag-to-reschedule, sync or sharing, splitting `index.html`, Dexie/Workbox. Each
would either break the "one folder, edit and upload" promise or reintroduce a server.

---

## 6. One-line summary

The app no longer needs a server, cannot silently forget a recurring plan or a late reminder,
knows which timezone its prayer times belong to, protects your data with a real backup file,
survives a browser clearing its cache, and fails the build if any of that breaks again.
