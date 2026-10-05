# Lists (Projects) inside the Planner — design + engineering plan

**Status:** for CEO approval. v2, rewritten after review feedback that v1 lacked research and
domain thinking. It did — v1 was a file-splitting note wearing a plan's clothes.
**Measured on `main`, `index.html` = 5,080 lines, app live at v49 on both origins.**

---

## 0. What your sentence actually contains

> "a list I can create and keep updating and add tasks and reminders in it **till I finish the
> thing I made it for**, also to **mark progress**, and be able to **have it always**"

That is not "a to-do list". It's four distinct product requirements, and they're the definition of a
**project list** in every mature task app:

| Phrase | Requirement | Category |
|---|---|---|
| "a list I can create" | a container entity | structure |
| "keep updating" | notes + incremental edits, not a one-shot | durability of *state* |
| "till I finish the thing I made it for" | a goal with an end condition | **progress** |
| "mark progress" | partial completion must be visible | **progress** |
| "have it always" | must survive device/cache/OS loss | **durability of *data*** |

v1 addressed the container and hand-waved the last two. They're the actual difficulty, and they're
what makes this worth building at all.

---

## 1. Domain research: how the category solves this

**TickTick** ships an explicit 5-level hierarchy — *Folder → List → Section → Task → Subtask* —
and markets Lists as the unit that unlocks kanban/timeline views
([TickTick help](https://help.ticktick.com/articles/7055782309420597248)).
**Todoist** users converge on the same shape without being told: a project per life area
("Umrah", "House", "Spirituality"), **sections as phases**, and the section header typed as
`Equipment:` at end of a task title ([Todoist guide](https://medium.com/ten-timezones/the-ultimate-guide-to-using-todoist-f8237f1f75ed)).
A documented pro trick: **prefix a task with `*` to make it permanently uncompletable** — used for
reference links pinned inside a project ([managers' guide](https://www.todoist.com/inspiration/todoist-guide-managers)).

Three things I take from this and one I reject:

1. **Sections are phase grouping, not hierarchy.** "Documents / Vaccinations / Travel / Packing".
   That's how a *long-running* list stays usable at 30 items. Cheap to build: a task with a title
   ending in `:` becomes a non-completable header — **exactly the Todoist `*`-pattern, and we can
   reuse the idea without inventing a second entity.**
2. **"Someday / maybe" is a universal user need**, and it is precisely what protects My Day from
   list noise. Not an extra feature — a parking state.
3. **Progress is `x of y`, not a percentage.** Users completing one item of a 40-item list at 2%
   feels bad; "3 of 40" is honest and motivating. This matches how the app *already* thinks — see §2.
4. **Rejected: folders and subtasks.** TickTick has 5 levels; we need 2 (list → items) plus
   cosmetic section headers. Adding real nesting is a data-model tax paid forever for a
   power-user minority, and it would triple the sync/migration surface.

---

## 2. The Islamic domain point that reframes "mark progress"

**You already built this, and my v1 plan missed it.** `index.html` has `target_count /
current_count` tap counters ("Tap to increment", line ~1755) and a full **Khatmah** modal:
30-day / 60-day / 7-day / custom pace, tracker selectable between **prayers** and **pages**
(lines 824–890).

That is the right mental model for a Muslim's list, and it is not "percentage complete". Real
examples from your own users' lives:

- *"Umrah before Ramadan"* → 12 items, progress = **7 done**
- *"Memorise Surah al-Mulk"* → progress = **14 of 30 ayahs**, tap to advance
- *"Fast the first 6 of Shawwal"* → progress = **3 of 6**
- *"Khatmah in my neighbourhood group"* → **pages / prayers**, exactly the existing khatmah dial

So the design decision is: **a list's progress is a counter with a denominator you choose** —
items-done by default, or explicit `n of m` when the thing is repetitive. One mechanism, already
in the codebase, already i18n'd, already understood by your users. I am not designing a progress
system; I'm generalising one that exists.

This is also what makes Lists *not* a Todoist clone. TickTick can do "3 of 40". It cannot do
"14 of 30 ayahs, Warsh riwayah, with a Fajr nudge".

---

## 3. The research invalidated part of my own plan

**3a. iOS deletes PWA storage at ~7 days of disuse** ([PWA integration mistakes, 2026](https://webscraft.org/blog/8-kritichnih-pomilok-pri-integratsiyi-pwa-stsenariyi-prichini-ta-rishennya-z-kodom?lang=en)).
v1 listed "export/import" as an optional extra and rated it "higher value than the Supabase path".
Understatement: **"have it always" is unachievable without it**, on the platform where your iOS
users live. It moves into the feature, not beside it. Given your stated direction away from
Supabase, a JSON file you keep in Drive/Files *is* the backup story — and it's ~80 lines, offline,
no account.

**3b. There is a live bug this plan must fix first, because the split would weaponise it.**
Our `sw.js` install handler, verbatim:

```js
for (const url of SHELL) { try { await cache.add(url); } catch (e) {} }
await self.skipWaiting();
```

Every failure is swallowed, then the worker activates **regardless**. The 2026 PWA write-up and a
real code review both name this exact pattern: a non-atomic install lets a worker go live with a
**partial cache**, and the fix is to cache critical assets atomically (`addAll`) so one failure
aborts install and the *old* worker keeps control
([atomic-install PR](https://github.com/Franky100-pig/Sand-and-Ink/pull/3)).

Today, with one `index.html`, a swallowed failure costs you a stale app. After splitting into
4 JS files, it costs a **blank white screen offline** — my own plan creating the outage. The fix
is small and must land **before** the split, not with it.

**3c. RTL: I would have guessed wrong twice.**
Material's bidirectionality spec is explicit that in RTL, **checkboxes sit to the right of the
label**, and **progress bars fill in the reading direction**
([Material](https://m2.material.io/design/usability/bidirectionality.html)). Separately, the
recommended technique is CSS **logical properties** (`margin-inline-start`, `padding-inline-end`)
rather than `[dir="rtl"]` overrides
([RTL testing](https://ubertesters.com/blog/best-localization-testing-practices-for-right-to-left-rtl-languages/)).

We currently use hardcoded `left/right` + `[dir="rtl"]` fixes at lines 103, 115, 141–142 — the
pattern that produces exactly the sidebar bug you caught months ago. So: new list UI ships with
logical properties from day one, and converting the four existing `left/right` rules is folded in
as a 15-line cleanup. Progress bar direction is not cosmetic — a bar that fills left-to-right in
Arabic reads as "in progress" when it means "remaining".

**3d. Workbox** is what the 2026 performance guide tells every production PWA to use instead of
handwritten SW logic ([PWA Performance Guide](https://www.digitalapplied.com/blog/progressive-web-apps-2026-pwa-performance-guide)).
**Deliberately not adopted:** it presumes a build step, which is the one architectural promise we
keep (single folder, edit and upload). I'm recording the rejection so it reads as a decision, not
an oversight. What we adopt from it instead: **version per file** in the manifest, so a changed
`js/quran.js` alone invalidates.

---

## 4. Data model

Two arrays, no schema surgery on tasks beyond one additive field:

```js
localStorage['alfaz_lists']
{ id:'l…', title, note, color, icon,
  target: 'items' | 'count',        // 'count' → progress is current/target, khatmah-style
  target_count, current_count,
  status:'active'|'parked'|'done',  // parked = Someday, hidden from My Day, kept forever
  created, updated, done_at }

// on existing tasks, additive only:
{ …, list_id:'l…', section:'Packing' }   // absent ⇒ unchanged behaviour everywhere
```

`section` is a **string, not an entity** — that's what keeps Todoist-style phase grouping to a
sort and a header render instead of a second table. Auto-complete at `items` mode; in `count` mode
the user closes it manually (you can finish 30 juz of a 60-juz family khatmah and it stays open).

## 5. Where it lives, in the UI

Inside **Planner**, as you said. The Planner already has chips `All / My Plans / Occasions`
(line 653) wired through `setPlannerFilter()`, so **Lists is a 4th chip** — zero new navigation,
no fifth bottom-nav tab, no 320px label fight.

Card row: colour dot, title, `3 of 12` + a bar (fills right in RTL), last-updated. Tap → items
grouped under section headers, an always-visible "add item" row, and the note field saving on blur
("keep updating"). One tap on a `count`-target list increments; long-press completes.
**My Day** gains a `From my lists` chip, and undated list items are excluded from `renderTodayView`'s
`noDate` bucket via `!t.list_id` — without that, a 12-item list floods My Day, which is the bug I
told you last round wouldn't happen. It would have.

## 6. Engineering: the split, gated

Cut (measured, not aesthetic): `js/core.js` (61 module-level lets, `currentLang` has **151**
refs), `js/quran.js` (42 funcs / 536 lines), `js/prayers.js` (24 / 249), `js/planner.js`
(planner + occasions + **tasks**, 73 / 1,022). **Tasks stay with planner** — `tasks` has 53 refs,
**4 of them in planner code** (the Tier 2 link). `index.html` → ~3,300 lines, zero logic duplicated.

Safe because of one verified property: every entry point is an HTML attribute (`onclick="…"`), so
there is no bundler, import, or closure to rewire. Order matters, that's all.

Gates (all mechanical, none optional):
1. **Byte-exact**: extracted `<script>` region must equal the concatenation of the new files, modulo
   whitespace. Any other diff ⇒ abort.
2. **Function count invariant**: 201 before, 201 after. Catches a swallowed nested definition — the
   failure mode that made me ship a duplicate `push_dir_probe` and take your sender down.
3. **Manifest comment** in `index.html` listing every `js/` file, and a CI check that each exists.
   A missing `js/core.js` is a blank screen, not a warning.
4. **Atomic install** (§3b) landed first: `addAll` for critical assets, optional assets best-effort,
   and no `skipWaiting()` unless the critical set succeeded.
5. **CI**: a GitHub Action running `node --check` on every JS file, the function-count gate, and the
   three existing suites (10 + 18 + 44 tests, all green today). Free on a public repo, and it's how
   "I verified it" stops depending on my diligence.

## 7. Rollout — each step independently shippable and reversible

1. Atomic-cache fix + CI gate. *(protects the app you already have)*
2. `listProgress()` / add / rename / park / reopen as pure functions, **unit tests first** — the
   recurrence work passed 16/16 this way, so it's a proven method here, not a hope.
3. Lists chip + card view + item CRUD, reusing `renderTaskRow`.
4. Section headers, `count`-target progress, auto-complete.
5. My-Day exclusion + `From my lists` chip.
6. Split (`core → quran → prayers → planner`), one file per commit, gates green each time.
7. Export/import JSON (the real answer to "always"), plus the `alfaz_lists` blob in it.
8. RTL pass: logical properties on new UI, convert the 4 legacy `left/right` rules.

Step 6 sits *after* the feature deliberately: shipping the feature inside a refactor means a
regression has two possible parents.

## 8. Out of scope

Folders, real subtasks, sharing/collab (Phase 3 Groups: `renderGroups` = **0**, still a stub),
drag-reorder, recurring list items, reminders on the list itself, kanban, sync.

## 9. Two open questions I won't answer for you

1. **Do lists get their own reminders, or only their items?** Only-items is smaller and matches how
   you described it; list-level "due by Umrah season" is a planner plan wearing a different hat.
   My recommendation: items only.
2. **Where does "have it always" land — after the feature or with it?** Export/import is 80 lines
   and unblocks the promise you actually made in that sentence. My recommendation: with it, as step
   7, before the RTL polish.
