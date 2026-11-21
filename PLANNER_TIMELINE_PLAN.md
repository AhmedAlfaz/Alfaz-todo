# Phase 3 — IndexedDB + Planner timeline · **v2, for specialist review**

**Status:** v1 was rejected as weak. This is the rewritten version, and it exists to be *torn apart
by someone who knows more than I do*, not to be approved as-is.
**Branch:** `arena/56b587ab-alfaz-todo` · **Baseline:** v52, local-only, no server.
**Also filed as an issue:** https://github.com/AhmedAlfaz/Alfaz-todo/issues/1
**How to review:** every claim below is either *(M)* measured with a command you can re-run, or
*(A)* an assertion marked as such. Attack the (A)s first — that is where v1 failed.

---

## 0. What v1 got wrong (recorded so v2 cannot repeat it)

v1 claimed the recurrence engine was "already sound", that IndexedDB was needed for size, and that
a timeline was mostly layout. Three of those were wrong, and one was unmeasurable.

| v1 said | Reality | How it was checked |
|---|---|---|
| "`planMatchesDate()` … already sound" | **Monthly plans on the 31st silently skip Feb, Apr, Jun, Sep, Nov. Yearly plans on Feb 29 fire once every 4 years and never in between.** | (M) executed the function out of `index.html` |
| "IndexedDB, because localStorage is small" | At 1,000 tasks the whole payload is **338 KB** and a full read-modify-write is **~1.8 ms**. There is no measurable performance problem. The only unbounded store is the Quran HTML cache. | (M) node benchmark, §2.1 |
| "A fixture table will lock the time rules down" | `tools/` has **8 suites and none of them mentions `planMatchesDate` or `plansForIso`**. No harness exists for it. | (M) grep |
| "Timeline = new view over existing data" | The *time model* is inconsistent: a 23:45 reminder never fires if the app is next touched at 00:05; snooze rewrites `due_time`; prayer times are wall-clock for the coordinates' zone compared against the device clock. A timeline draws all three as if they agreed. | (M) see §3 |

Also: v1 shipped no measurement of the added weight (≈450 lines onto 3,829 lines of inline JS in a
300 KB single file), no keyboard/screen-reader path, and no answer for what happens with two tabs
open. Those are in §5 and §6 now.

---

## 1. The real problem statement

Not "localStorage is full" and not "a day view would be nice". Stripped down:

> ABDO keeps **three different notions of time** — a civil date string (`2026-11-21`), a wall-clock
> `HH:MM` that belongs to a *timezone nobody recorded*, and a `Date` built from local-midnight
> parsing — and compares them with `<`, `===`, and subtraction of milliseconds. Every user-visible
> bug in this area comes from that mismatch, not from the storage engine.

A day timeline is the first screen where all three meet in one frame, which is why it is worth doing
**after** the model is fixed, not before.

---

## 2. Storage: what is actually true *(M)*

### 2.1 Measured cost of today's storage path

```
tasks    JSON size     stringify     parse+stringify (a full write)
50       17 KB         0.036 ms     0.078 ms
200      67 KB         0.097 ms     0.296 ms
1000     338 KB        0.900 ms     1.830 ms
3000     1015 KB       2.441 ms     6.002 ms
```
50 checkbox taps at 1,000 tasks: 44 ms total. **Conclusion: performance is not the reason to migrate.**

### 2.2 Where the bytes actually go

- 21 write sites across 18 functions, all serialising the **whole** array (no partial write).
- 2 read sites.
- The only store with unbounded growth is `alfaz_quran_cache_ayah_*` — formatted **HTML strings**,
  one per surah per riwayah. A handful of long surahs is a few hundred KB; a dozen is a meaningful
  fraction of the 5 MB ceiling. Nothing in the app ever prunes it.
- Same 5 MB bucket holds user data **and** disposable cache. That is the actual defect: *cache
  pressure can evict or block the one thing that cannot be regenerated.*

### 2.3 Options, with the recommendation changed from v1

| Option | Buys | Costs | Verdict |
|---|---|---|---|
| **A. Split caches out** — move `alfaz_quran_cache_*`, prayer timings, hijri months into IndexedDB (or a `Cache`-style store); leave user data in `localStorage` | user data stops competing with disposables; ~1 day; no migration of the data that matters | still 5 MB for user data (fine for years) | **do this first** |
| B. Full move to IndexedDB behind a mirror + gate | atomic writes, bigger quota, indexes | 3 releases of dual-write, a real data-loss window, ~300 lines | only if A proves insufficient |
| C. `sqlite-wasm` / Dexie | — | build step or 200 KB dependency; breaks the "one folder, upload" promise | rejected (recorded, not overlooked) |

This is the biggest change from v1: **the storage work shrinks from "migrate the app" to "get the
cache out of the data's bucket"**, and the dangerous part becomes optional.

---

## 3. Time model: the three defects a timeline will expose

### 3.1 Recurrence *(M — reproduced by executing the shipped function)*

```
monthly on the 31st:   Jan 31 ✓   Feb 28 ✗   Mar 31 ✓   Apr 30 ✗   May 31 ✓
yearly on Feb 29:      2027 ✗      2028 ✓      2029 ✗      2030 ✗
```
Both fail silently — the plan simply does not appear. A month view hides this; a timeline shows an
empty day and the user concludes the app forgot.

### 3.2 Reminders are not aware of the timeline's day

```
09:00 task, reminder 15 min before → fires at 08:45 … and still fires at 09:44  (60-min catch-up)
23:45 task, app opened at 00:05    → never fires (guard: due_date !== today)
snooze 15 min                       → rewrites due_time, i.e. moves the block on a timeline
plan with no time, reminder set     → silently assumes 09:00
```
So a timeline cannot simply read `due_time` as "where the block goes": the alarm and the block would
disagree about what the time means.

### 3.3 Prayer times belong to a place, not to the phone *(M-adjacent, from Aladhan's documented contract)*

`GET /v1/timings/{date}?latitude=…&longitude=…` returns **wall-clock times for the coordinates'
timezone**; a `timezonestring` is optional and we never send it. The cache key is
`alfatore_prayers_DD-MM-YYYY` — no coordinates, no zone. Consequences, both of which draw wrong
blocks on a timeline:

- Travel 2 hours east and every prayer line is 2 hours off, offline, until the next fetch succeeds.
- The "now" comparison uses the device clock, so a *correct* remote set of times is compared wrongly
  the moment the zones differ (simulated: Maghrib reported as passed 2 h early).

### 3.4 What the specialist is being asked about the model

1. **Civil dates:** integer day-numbers (`days since 1970-01-01`, no `Date`, no DST, no timezone) as
   the canonical recurrence key, with `Date` used only at the edges for display/reminders. Or keep
   `Date` + an explicit library? Constraint: no build step.
2. **Month-end and leap rules:** clamp-to-last-day (31st → 30th/28th), skip, or "last day of month"
   as a first-class repeat option? What do users expect for a rent reminder?
3. **Occurrence identity:** `(plan_id, iso)` is enough today; once an occurrence can be completed or
   snoozed independently, a materialised occurrence row becomes necessary. Is that a Phase 4 bridge
   too far?
4. **Timezone policy:** store `timezone` (IANA string) + `lat/lng` at fetch, and compare in that zone;
   or store everything as UTC instants derived at fetch? What breaks when a user prays Maghrib on a
   plane?

---

## 4. Product shape (unchanged in direction, tightened)

- Fourth chip in the existing Planner switcher: Month · **Week** · **Day** · Year. (Assertion, not
  measured: Week currently renders 7 cards that each stack items as text; with 3+ items a day it is
  already a timeline with worse ergonomics — this needs 10 minutes on a phone before we commit.)
- Vertical day column, 56 px/hour phone / 64 px `md+`, 22 px minimum block, max 2 overlap lanes then
  a `+n` chip, window clamped to the content ±1 h and to 04:00–23:30.
- Prayers as thin dividers (emerald), untimed items in an "Any time" strip, not hidden.
- Logical properties only; the vertical axis is **not** mirrored in RTL.
- Out of scope: drag, resize, pinch, cross-day blocks.

---

## 5. Rendering and concurrency (missing from v1)

- 5 planner renderers today (71 / 60 / 43 lines) each rebuild `innerHTML` wholesale; two views can
  be showing the same data with no shared invalidation.
- **No `storage` event listener** exists: two tabs both hold `tasks` in memory and the last writer
  wins the entire array. A timeline left open all day is exactly the tab that loses.
- Proposal: one `renderTimeline()` that diffs by block key, plus a `storage` listener that reloads
  and re-renders if the change is not from this tab. Measurement to justify it: time to re-render
  one day with 40 blocks, before/after.

---

## 6. Accessibility and i18n (missing from v1)

- A time axis is a table of two columns semantically: `<time>` label + block. Provide a list
  equivalent for screen readers and a linear reading order that does not depend on CSS positioning.
- 18 `data-i18n` keys had no strings until v52 and `data-i18n-aria-label` did nothing until v52 —
  any new UI must ship through a check that fails when a key is missing. That check exists now in
  `tools/gates.py`? **No — it does not.** It was done ad hoc. Adding it is a 20-line gate.
- Arabic: numbers, `am/pm` equivalents, and block titles that mix directions.

---

## 7. Test harness (v1 promised it, did not build it)

Minimum before any UI work:

```
tools/test_planner_time.py
  - monthly 31st across 12 months            (today: fails 5 months)
  - yearly Feb 29 across 8 years             (today: fails 3 of 4)
  - repeat_until inclusive day
  - DST: Africa/Cairo, Asia/Beirut, America/Santiago, Australia/Lord_Howe (+30 min DST)
  - reminder window at 23:45 with the app opened next day
  - timezone: fetch in zone A, read in zone B
```
Runs in node (already a dependency of the gates) by extracting the pure functions, same trick used
in this investigation.

---

## 8. Order of work (changed from v1: defects before features)

| # | Step | Why first |
|---|---|---|
| 0 | Gate: every `data-i18n*` key must exist in both languages | cheap, stops a whole class of blank labels |
| 1 | Recurrence correctness + test harness (§3.1, §7) | a timeline that omits an occurrence is a lie |
| 2 | Cache split (§2.3 A) | removes the only real storage pressure |
| 3 | Timezone on prayer timings (§3.3) | otherwise the timeline's anchors are wrong when travelling |
| 4 | Reminder/day-boundary semantics decided (§3.4) | alarm and block must agree |
| 5 | Timeline: pure `buildDayTimeline()` + day view | the visible feature |
| 6 | `storage` listener + diff rendering (§5) | protects the tab left open |
| 7 | IndexedDB for user data — **only if** §2 measurements demand it | optional by design now |

---

## 9. Questions I am explicitly not deciding alone

1. §3.4 (1)–(4) — the time model. This is the one that will decide whether Phase 3 is stable for years.
2. Task duration on the timeline: point, or default 30 min? (v1 asked the CEO; the honest answer is
   that this is a product call informed by what Structured/Taskito do, not a technical one.)
3. Whether `planMatchesDate` is patched in place or replaced by a day-number implementation with the
   old one kept as a differential test oracle.
4. Whether the timeline should be allowed to render **materialised** occurrences (rows), which changes
   the storage model and therefore the migration in §2.3.

---

## 10. Definition of done (v2)

- §7 harness green, including the two currently-failing cases.
- No `data-i18n*` key resolves to `undefined` in either language (gate, not a spot check).
- Two tabs open for an hour, edits in both, no lost task.
- 360 px and 390 px: no horizontal scroll, nothing under the bottom nav, every block ≥ 22 px.
- Arabic: axis on the inline-start edge, block titles not clipped.
- A specialist has reviewed §3 and §9 and signed off or rewritten them.
