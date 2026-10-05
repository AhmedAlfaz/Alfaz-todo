# Lists you keep and update — plan

**Status:** awaiting CEO approval. No code until then.
**Written from the code as it is on `main` (v49), not from memory.**

## 1. What you asked for

> "a list I can create and keep updating and add tasks and reminders in it till I finish the
> thing I made it for, also to mark progress, and be able to have it always"

Five requirements, and they map onto the codebase unevenly:

| You said | Exists today |
|---|---|
| create a list | ❌ nothing — verified `list_id`, `project`, `folder`: **0 occurrences** in index.html |
| add tasks into it | ⚠️ tasks exist but are one flat array; no container |
| reminders in it | ✅ full task reminder engine (`reminder_minutes`, alarm, vibrate) |
| mark progress | ✅ **already built** — `target_count` / `current_count` tap counter (line ~1755) |
| keep it until finished | ⚠️ needs one flag — tasks carry `status: 'pending'`, lists need their own done-state |
| have it always | ❌ **the dangerous one** — see §5 |

So the honest read: this is **not** a new feature so much as a missing *container*. Three of
six needs already exist and just aren't groupable. That's the cheapest kind of upgrade.

## 2. Design: `alfaz_lists` header + existing tasks as items

Reuse the task engine rather than parallel-bookkeeping it. One new array, one new field:

```js
// localStorage['alfaz_lists']
{ id, title, note, color, icon, created,
  target: 'count' | 'percent' | 'none',   // how progress is measured
  status: 'active' | 'done',              // the "till I finish the thing" flag
  done_at }

// added to each existing task that belongs to a list
{ ..., list_id: 'l…', list_optional_date: true }
```

`list_id` on the *existing* task object is the whole trick: the item automatically inherits
due dates, reminders, recurrence, priority, the tap counter, `renderTaskRow`, `syncTask` and
every filter — **zero duplicated logic to drift**.

Progress is then never hand-written:
- `done/total` when `target === 'count'`
- the existing `current_count / target_count` tap counter when `'percent'`
- the list auto-flips `status: 'done'` at 100%, and can be reopened

## 3. Where it lives

A **5th bottom-nav tab** ("Lists", `fa-list-check`). Measured risk, stated plainly: at 390px
width five tabs are ~78px each and the Arabic labels are longer — so I'd ship it with
short labels (`Lists` / `قوائم`) and verify at 320px (iPhone SE) in the same headless harness
that caught the footer overlap. If five tabs don't hold up, the fallback is a segmented control
inside My Day. Your call, and I'll test either.

Screen: a list of cards (title, progress ring or `3/7`, colour dot) → tap → items, an
"add item" row, and a note that saves on blur. That "keep updating" part of your description is
the note field, and it's why each list carries one.

## 4. Deliberately *not* building

- No drag-to-reorder, no nesting, no subtasks.
- No per-item repeat rules — items inherit the task engine's existing recurrence if it's set.
- No sharing, no collab (that's Phase 3 Groups, still a stub: `renderGroups` = **0**).
- No new progress UI — reusing the tap counter is the point.

## 5. The problem this feature makes worse, and I won't hide it

**"Have it always" is currently unachievable, and the reason is a real gap in the app.**

Measured today:
- `alfatore_tasks` → `syncTask` 19 call sites, `from('tasks')` 4 → **tasks sync to Supabase**
- `alfaz_plans` → `syncPlan` **0**, `from('plans')` **0** → **Planner data never leaves the phone**

So your Planner — the thing we spent two tiers building — is one cleared browsing-data or one
phone swap away from nothing. iOS additionally evicts a little-used PWA's storage outright.
Lists would inherit that fate, or be worse, since a list is *by definition* something you keep
for months.

Two options, and this is the one decision I need from you beyond the shape above:

- **A (recommended): list items are tasks.** Free sync for the items; the list *headers* are the
  only local bit (~small, and reconstructible). Smallest change, most durable outcome.
- **B: separate storage like Plans.** Cleaner data model, but you'd ship a "keep forever"
  feature on storage that does not keep. I don't recommend it.

Separately and independently: **Planner sync** should get its own fix, because that's a bug
regardless of this feature. Not bundled in here, just flagged so it isn't forgotten.

## 6. How I'd build it, in order, each step verifiable

1. Data layer + pure logic (`listProgress`, `toggleListDone`, add/rename/note) with **unit tests
   first** — the recurrence work passed 16/16 that way, so this pattern is proven here.
2. Lists view + card rendering, i18n EN/AR, RTL check.
3. Item CRUD reusing `saveCurrentTask`/`renderTaskRow` paths (no new task form).
4. Progress + auto-complete + reopen.
5. Headless layout pass at 320/390/412px for the fifth tab, and a **hard check that a list item
   with no date never pollutes My Day**.
6. Migration guard: existing users have no `alfaz_lists`, so first run must render empty, not error.

## 7. Known cost, said out loud

`index.html` is **5,080 lines**, and the last several sessions were us fighting that rather than
the feature. This adds ~350-450 lines to the same file, plus a new array in localStorage.
It is doable — the Planner tiers fit — but the *right* move for the project, independent of
this feature, is splitting the app into a few real JS files with a trivial build-free loader.
If you'd rather I do that first, this feature gets easier and every later feature gets cheaper.
My recommendation: **do the split first, then lists** — and if you disagree I'll still build
lists, just with more care on the test gate.
