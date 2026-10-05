# Split `index.html`, and put Lists inside the Planner

**Status:** plan for approval. Nothing changed yet.
**Measured on `main` at `5,080` lines / v49.**

## 1. Two facts decided the design

**Easy:** every function in the app is invoked from HTML attributes (`onclick="…"`) — nothing is
called through a bundler, import, or closure. So extracting `function quranFoo()` into its own
file keeps working **provided the files load in order**. No module system, no build step, no
rewrite of call sites. That is why this can be done safely at all.

**Dangerous:** the state is genuinely shared, so a naive cut is not available. Counts of
cross-references, from the actual file:

| shared variable | references | spreads into |
|---|---|---|
| `currentLang` | **151** | every module |
| `tasks` | 53 | tasks 22, **planner 4**, quran 5 |
| `prayerTimings` | 22 | prayers 15, tasks 2 |
| `activeDhikrLibraryId` | 10 | quran 4, tasks 3 |
| `audioSettings` | 13 | planner 4, quran 3, tasks 2 |

Plus **201 functions** in one `<script>` block, and **61 module-level `let`s**.

`tasks` being referenced from the planner is the plan→My Day link we shipped in Tier 2. So:

> **Tasks and Planner must not be separated.** Splitting them would mean inventing a cross-file
> contract for the single most shared piece of state in the app, for zero benefit.

## 2. The cut

```
js/core.js      61 globals + currentLang/audioSettings accessors + toast/modal/switchView + i18n
js/quran.js     42 funcs, 536 lines   ← first extraction: best lines-per-coupling
js/prayers.js   24 funcs, 249 lines   ← prayerTimes is 15/22 self-contained
js/planner.js   73 funcs, 1,022 lines ← planner + occasions + tasks (do not split further)
```

`index.html` keeps markup, `<style>` (132 lines) and the `<script>` tags. Ends around **3,300
lines**, with **zero logic duplication**.

`i18n` (224 lines, 151 refs) stays with `core.js`. Extracting it into its own file means any
string edit needs a second file in the upload list — and if that upload is forgotten, every
`i18n[currentLang].foo` lookup throws. **The failure would be silent and total.** Not worth it.

## 3. Safety rules — because last time the tooling lied

The reason to trust this plan is not my confidence, it's these gates:

1. **Byte-exact proof.** Before/after, extract the `<script>` region and compare against the
   concatenation of the new `js/` files. The split must move text, never rewrite it. Any diff
   other than whitespace = abort.
2. **Function count must be invariant.** 201 before, 201 after. This catches the one silent
   killer: a function nested inside another block that my extractor swallows.
3. **Every `js/` file must exist.** A stale upload list otherwise fails as a quiet 404 — the same
   class as the v48/v49 mismatch where I reported success I hadn't verified. `index.html` will
   carry a 4-line manifest comment so the list is never remembered by hand.
4. **Deploy list becomes:** `index.html`, `sw.js`, `site-config.json`, `js/` (whole folder), `brand/`,
   `push/` — and `js/` is now **load-bearing**, not optional.
5. `tools/test_v40_stale.py` + `test_v42_push.py` keep running against the split layout, so the
   existing green suites are the regression net, not a new hope.

No build step. HTTP/2 serves 4 extra files in parallel; if first-load time ever matters, the same
gate produces one concatenated file in one command.

## 4. Lists — inside the Planner, as you said

No fifth nav tab (which would have cost a 320px layout fight for a word as long as
`القوائم`). Instead: the Planner already has filter chips **All / My Plans / Occasions**, so
**Lists is a fourth chip**, and **My Day keeps a "From my lists" filter** so active items surface
where work actually happens.

Data: `alfaz_lists` holds headers only —

```js
{ id, title, note, color, created, target: 'count'|'none', status: 'active'|'done', done_at }
```

Items are **ordinary tasks with `list_id`**, so they inherit reminders, recurrence, priority, the
existing `current_count / target_count` tap counter, and `renderTaskRow` — the progress marking
you asked for already exists in code and needs no new UI. A list auto-completes at 100% and can
be reopened, which is your "till I finish the thing I made it for".

### Correction found while writing this (my earlier statement was false)

I said a list item with no date would never pollute My Day. **It would.** `renderTodayView`
(line 1777) is:

```js
const noDate = tasks.filter(t => !t.done && t.status!=='cancelled' && t.due_date===null);
```

Undated tasks are *deliberately* shown in My Day. So a 12-item list would dump 12 rows into
everyone's My Day. Fix, one condition:

```js
&& !t.list_id     // undated list items live in their list, not in My Day
```

which also makes the semantics pleasant rather than merely correct: an item with **no date**
stays in the list; give it a **date** and it appears in My Day; give it a **reminder** and it
notifies. One field, no new machinery. The `noDate` filter and the list-item query are then
covered by a unit test, since this is exactly the class of bug I have been caught shipping.

## 5. Supabase, since you said you want out

Then the honest framing changes, and I want to flag it rather than quietly claim a win:

- My main argument for `list_id`-on-tasks was *"sync comes free."* With Supabase on the way out,
  that argument **evaporates**. The remaining reason stands, and it's the better one anyway: one
  set of item code instead of two, so nothing drifts.
- Nothing new should **increase** Supabase coupling. So: no `syncList`, no new tables, no
  `plans` table for the Planner's existing gap. Freeze it, keep guest mode as the default path.
- Removing it is a **separate pass**, not folded into this one — otherwise the split and a backend
  migration land together and neither is verifiable. Say the word and I'll plan it next.
- What "have it always" actually needs is not Supabase, it's **export/import** of one JSON blob.
  That is ~80 lines, works offline, suits a no-accounts product, and survives an iOS storage
  eviction that no sync can prevent if the user never signs in. I'd rate it higher-value than
  the entire Supabase path.

## 6. Order of work

1. Gates first (`verify-split.py`: byte-exact + function count + file-exists) — build the safety
   net before touching anything.
2. Split `quran.js`, run the gate and both suites.
3. Split `prayers.js`, same.
4. Split `core.js`, same. Leave planner+tasks+occasions as one file; it is one concern.
5. Lists: `listProgress`/add/rename/note/toggle as **pure functions with unit tests first** (the
   recurrence work passed 16/16 this way), then the chip, then the card view.
6. Export/import JSON backup — either now or as its own step. Small, and it is what actually
   answers "have it always".

Steps 2–4 are mechanical and reversible one file at a time. Step 5 is the feature.
