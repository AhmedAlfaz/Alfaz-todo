# Phase 3 — IndexedDB + the unified Planner timeline

**Status:** for approval. Nothing built yet.
**Branch:** `arena/56b587ab-alfaz-todo` · **Baseline:** v52 (`index.html` 4,7xx lines, local-only, no Supabase).
**Companion decision:** the account/cloud layer was removed on 2026-11-21. This plan assumes **no server** — see §1.1 for why that makes the storage question more important, not less.

---

## 0. What "Phase 3" is actually two problems

> "migrating the data structure to IndexedDB and building the unified Planner dynamic timeline"

Those are different risks and should not ship in the same step.

| | IndexedDB migration | Planner timeline |
|---|---|---|
| Kind of work | plumbing — swap a storage layer under 20+ call sites | product + UI — a new way to see the day |
| Risk if wrong | **data loss** (the only copy) | wasted screen space, an unusable phone layout |
| Verifiable mechanically | yes — counts, round-trips, byte-compare | only by looking at it on a 360px screen |
| Depends on the other | no | no (it can read `tasks`/`userPlans` as they are) |

**Recommendation: timeline first (small, visible), IndexedDB second (invisible, dangerous).** The
timeline is what the user asked to *see*; the storage swap is what they asked to be *safer*. Shipping
the visible thing first means the storage work can be verified against a feature that is already
stable, and a regression during the swap has exactly one possible parent.

The rest of this document is written in that order.

---

## 1. The uncomfortable facts this plan has to respect

### 1.1 IndexedDB does not solve the problem the user thinks it solves

The request is usually stated as "localStorage is small, move to IndexedDB so I can keep more".
Two corrections, both measured:

1. **Size is not the current constraint.** Today the app writes ~15 keys; the only fast-growing one
   is the per-surah Quran text cache (`alfaz_quran_cache_ayah_*`). A heavy user with 300 tasks, 50
   plans and a dozen cached surahs is still well under 1 MB. `localStorage` allows ~5 MB. We are not
   near the ceiling; we are near the *point where the ceiling matters*, which is different.
2. **Nothing about the browser's eviction policy improves.** Chrome may evict best-effort storage
   under disk pressure; Safari deletes script-writable storage after **7 days of no interaction**
   unless the site is installed to the home screen ([storage limits](https://signaldb.js.org/browser-storage/),
   [Safari ITP notes](https://www.testmuai.com/learning-hub/indexeddb-browser-support/)). IndexedDB
   has a *bigger* quota (Chromium: up to 60% of disk — [IndexedDB vs localStorage](https://we.inc/guides/indexeddb-vs-localstorage)),
   but the same eviction risk unless we call `navigator.storage.persist()` and the browser grants it.

So the honest scope of step 2 is: **more room and transactional writes, not durability.** Durability
is still the backup file (§1.2) plus `persist()`.

### 1.2 With no server, the backup file is the entire recovery story

`index.html` now has **Backup & Restore** (v52) — a JSON file with `schema`, all data keys, and
round-trip validation. This plan must not weaken it:

- Every new store added later must be added to `BACKUP_KEYS`, or the backup silently misses it.
- The export format is versioned, so an IndexedDB-backed build in v6x can still read a v52 file.
- The IndexedDB migration is the **first** change in this project that can lose data without the
  user doing anything wrong. The rollback rule in §4 exists for that reason.

### 1.3 The Planner already has the parts of a timeline, scattered

Verified in the current file:

| Piece | Where it lives today | What it is missing for a timeline |
|---|---|---|
| Fixed points in the day | `prayerTimings` (Fajr…Isha) + `getAzanFiredKey()` | nothing — these are the anchors a Muslim's day actually hangs on |
| Items with a time | `tasks[]` with `due_date` + `due_time` | a duration; today a task is a *point* |
| Items with a time and a repeat | `userPlans[]` with `date`, `time`, `repeat`, `repeat_until` | already sound: `planMatchesDate()` handles daily/weekly/monthly/yearly + interval + end |
| Occasions / holidays | `eventsForIso()` + `ISLAMIC_OCCASIONS`, `EGYPT_NATIONAL` | they render as a list, not positioned in the day |
| An agenda view | `renderPlannerWeek()` — 7 day-cards, each a stacked list | times are printed as text inside rows, never positioned |

`renderPlannerWeek()` is already 80% of an agenda. The timeline is the step that turns
"09:00 — Dentist" into a block you can see at a glance, between Fajr and Dhuhr.

---

## 2. What the timeline is (and is not)

**It is:** a vertical, scrollable day column — clock time on one edge, blocks placed by time,
with the five prayers drawn as quiet dividers and the current moment marked by a moving line.
The same data the Planner already shows, arranged by *when*, for one day at a time.

**It is not:** a calendar grid (we have Month), a drag-and-drop schedule editor (that is a separate,
much larger feature — deliberately out, see §6), or a new data model.

### 2.1 Why prayer lines, and not just events

This is the one design decision that makes the timeline *ABDO's* rather than a generic agenda.
The day already has five fixed, meaningful boundaries that the user cares about more than any
meeting. Drawing them:

- gives the empty timeline a shape (so 06:00–12:00 is not a blank column),
- answers the question this app exists to answer — *"what is left before Maghrib?"*,
- and costs nothing: `prayerTimings` is already computed and cached.

Full azan-grade styling would be noise. They are thin lines with a small label, in the same emerald
used by the prayer cards.

### 2.2 Sizing rules (the part that decides whether it is pleasant or useless)

Timeline UIs live or die on two numbers: block minimum height and overflow behaviour.

- **Hour height:** 56 px on phones, 64 px from `md` up. (A 24h day then scrolls rather than squeezes;
  1,344 px is a comfortable scroll, not a wall.)
- **Minimum block:** 22 px so a 5-minute reminder is still tappable, with its time label moved inline
  beside the title when the block is under ~40 px.
- **Collision:** side-by-side split, max 2 columns; a 3rd overlapping item becomes a `+2` chip on the
  second column that expands. Never stack-overlap (the classic agenda bug where the later block
  hides the earlier one).
- **The window is not 00:00–24:00.** It opens at the earliest of (first item − 1 h, Fajr − 1 h) and
  closes at the latest of (last item + 1 h, Isha + 1 h), clamped to 04:00–23:30. An empty night
  should not be 8 screens of void.
- **RTL:** the time gutter flips to the inline-start edge via logical properties, and the "now"
  line is symmetric. Do **not** mirror the vertical axis (Material is explicit that time flows
  downward in both directions — [bidirectionality](https://m2.material.io/design/usability/bidirectionality.html)).

### 2.3 Untimed items

The single largest category in real task data is "no time". They cannot be positioned, and hiding
them makes the timeline a liar. So they live in a pinned strip above the grid (**"Any time"**),
grouped by nothing, sorted by priority then created. Anything unfinished from earlier days that has
no date joins that strip as an overdue chip, because "what is still hanging" belongs at the top of
the day view.

---

## 3. Timeline — engineering

### 3.1 Placement

Fourth button in the existing Planner switcher: **Month · Week · Day · Year**
(`setPlannerView('day')`, `pv-day`). The Week view stays; Day is what Week's day-cards become when
opened. No new nav item, no fifth bottom-nav tab (the nav is already at 4/5 comfortable slots).

### 3.2 Data: three additive fields, nothing else

```js
// tasks[] — additive, ignored everywhere the timeline is not used
{ …, plan_start: '2026-11-21T09:00', estimate_min: 45 }   // absent ⇒ point at due_time, 30 min default

// userPlans[] — already has date/time/repeat/repeat_until; one additive field
{ …, estimate_min: 60 }                                   // absent ⇒ 60 min default
```

No new collection, no change to `planMatchesDate()`, no change to recurrence. A timeline entry is
either *(a)* a task with `due_date`/`due_time`, *(b)* a plan occurrence from `plansForIso(iso)`,
*(c)* an occasion from `eventsForIso(iso, hijriMap)` (all-day, drawn as a banner at the top), or
*(d)* a prayer from `prayerTimings`. Composite key for identity: `kind + id + iso`.

### 3.3 One pure function, tested

```js
buildDayTimeline(iso, { tasks, plans, occasions, prayers, now })
  → { blocks: [{kind, id, start, end, lane, title, color, done}],
      untimed: [...], window: {startMin, endMin}, nowLine }
```

Pure, no DOM, no `localStorage`, no `await`. The lane assignment, the window clamp and the
minimum-height rules in §2.2 are all decided here so they can be unit-tested with a table of
fixtures (overlaps, a plan at 23:50 with a 60 min estimate, a task with no date, an empty day,
RTL-agnostic). This mirrors the `planMatchesDate` test table that caught real bugs during Tier 2.

Rendering is then a dumb loop over `blocks` — the part that is hard to test is made as small as
possible.

### 3.4 Now-line and the "current block"

A 30-second `setInterval` moves the line and re-highlights the current block. It pauses on
`visibilitychange` (same lesson as the reminders: timer throttling in background tabs).

### 3.5 Explicitly out

Drag to reschedule, resize blocks, pinch-zoom the hour scale, cross-day blocks (a 23:30 → 00:30 plan
is clipped and marked with an arrow), and calendar import. Drag-to-reschedule is the single feature
that turns this into a 3-week project; it is Tier 4, if ever.

---

## 4. IndexedDB — engineering

### 4.1 Why not a library

`Dexie`/`idb` are excellent and would save ~150 lines. They are also a build-time dependency in a
project whose deliberate architectural promise is *"one folder, edit and upload, no bundler"*
(AGENTS.md: no npm packages). A tiny promise wrapper (~60 lines) around the six operations we need
(`open`, `get`, `getAll`, `put`, `delete`, `clear`) keeps that promise. Recorded as a decision, not
an oversight.

### 4.2 Shape

DB `abdo`, version 1. One store per entity **plus one blob store for things we cannot model**:

```
tasks        keyPath 'id'    indexes: due_date, status, plan_id
plans        keyPath 'id'    indexes: date
library      keyPath 'id'    indexes: kind        // custom adhkar only; built-ins stay in code
settings     keyPath 'key'                       // everything currently in localStorage that is a preference
cache        keyPath 'key'   indexes: saved_at    // prayer timings, hijri months, quran ayah text
```

`cache` is the only store allowed to be cleared silently (it is re-fetchable); it is also what
`alfaz_quran_cache_ayah_*` moves into, which solves the one realistic growth problem.

### 4.3 The migration that must not lose data

Six hard rules, all mechanical:

1. **Read-only first.** Ship a build that *mirrors* every write into IndexedDB while still reading
   from `localStorage`. Verify for a week of real use that the mirror matches (`count` + a per-store
   hash shown behind a long-press on the version label).
2. **Migrate on an explicit version gate**, not on every boot: `abdo_idb_migrated = 1` only after
   the full copy verified row-by-row.
3. **Never delete `localStorage` in the same release** that switches reads. One release later, and
   only after the gate is green for real users.
4. **Boot must not depend on IndexedDB.** `open()` is async and can be blocked (private mode,
   corrupted profile). The app must render from `localStorage` inside the first frame and *upgrade*
   when the DB opens. A blank screen on an old phone is not an acceptable failure mode for a prayer
   app.
5. **`navigator.storage.persist()`** is requested once, explained in Backup & Restore ("keep my data
   from being cleared by the browser"), and the answer is remembered — Firefox may prompt, Chrome
   grants silently based on engagement.
6. **Backup & Restore reads from the source of truth**, and after the switch it exports from
   IndexedDB. A backup taken on the wrong side of the migration is worse than no backup.

### 4.4 Rollback

`abdo_storage = 'idb' | 'ls'` in `settings`. Flipping it back to `ls` restores reads from the
(never-deleted, rule 3) `localStorage` copy. This is the only reason rule 3 exists.

---

## 5. Order of work — each step shippable alone

| # | Step | Files | Size | Verifiable by |
|---|---|---|---|---|
| 1 | `buildDayTimeline()` as a pure function + fixture table | `index.html` | ~120 lines | unit table, no UI |
| 2 | Day view: switcher button, window sizing, prayer lines, now-line, "Any time" strip | `index.html` | ~220 lines | screenshot at 360px + 390px, RTL |
| 3 | Overlap lanes + min-height/inline-label rules | `index.html` | ~60 lines | fixtures + screenshots |
| 4 | `estimate_min` editing in task + plan modals (additive fields) | `index.html` | ~40 lines | manual |
| 5 | IndexedDB wrapper + **mirror writes** (no read switch) | `index.html` | ~90 lines | mirror hash on the version label |
| 6 | Migrate + verify gate; reads still from `localStorage` | `index.html` | ~80 lines | gate green |
| 7 | Switch reads to IndexedDB behind `abdo_storage`; extend Backup & Restore | `index.html` | ~70 lines | export/import after switch |
| 8 | Remove the `localStorage` mirror one release later | `index.html` | −60 lines | cold start on a phone |

Version bumps follow the existing rule: `sw.js` `VERSION` and the `?v=` refresh query move together,
and `tools/gates.py` fails the build if they drift.

---

## 6. What stays out

- Drag-to-reschedule, resize, pinch-zoom (§3.5).
- Sync, sharing, groups — removed with Supabase in v52; reintroducing any of them is a product
  decision, not an engineering step.
- Splitting `index.html` into modules. The Lists plan proposed it as a prerequisite for the split;
  the timeline adds ~450 lines, which does not change that calculus. Do the split *after* this, with
  its own gates (byte-exact extraction, function-count invariant).
- Lists/folders (`PLANNER_LISTS_PLAN.md`). The timeline can render list items the day Lists ships,
  because both read `tasks[]`.

---

## 7. Two questions I will not answer for you

1. **Does a task on the timeline get a duration?** Default-on (30 min) makes the day look planned
   without asking the user anything, but it also invents facts. My recommendation: **no default
   duration — points unless the user sets `estimate_min`**, because a wrong block is more confusing
   than an honest dot, and the prayer lines already give the day structure. This is the single
   biggest UX fork in the plan.
2. **Is Day a peer of Week, or does Week become a strip that opens Day?** Four equal buttons is the
   least surprising thing and the least code. The nicer product is Week-as-strip + Day-as-detail
   (one less button, one more tap saved). My recommendation: **four buttons now**, revisit after
   you have used it for a week.

---

## 8. Definition of done

- `tools/gates.py` passes with the version pair bumped.
- `buildDayTimeline()` fixture table passes, including the 23:50 overflow and 3-item overlap cases.
- A 390 px iPhone and a 360 px Android show: no content under the bottom nav, no horizontal scroll,
  every block ≥ 22 px and tappable.
- Arabic (`dir="rtl"`): time gutter on the inline-start edge, labels not clipped, now-line symmetric.
- Empty day and a day with 30 items both look intentional (no giant blank column, no 400-px scroll
  of identical dots).
- After step 7: Backup & Restore exports IndexedDB content, and a restore from a v52 file still works.
