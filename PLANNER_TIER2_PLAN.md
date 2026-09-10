# 📅 Planner Tier 2 — Plan (v2.9) · for approval

**Date:** 2026-08-19 · **Status:** Proposal — nothing built yet

---

## Scope proposed (5 features)

### 1. 🗓️ View switcher: Month · Week · Year
- Small segmented control at the top of the Planner: **Month | Week | Year**
- **Month** = what we have now (grid + day panel + month list)
- **Week** = mobile-friendly: a 7-day strip for the current week, then a vertical list of that week's days with their plans/occasions. (A cramped 7-column grid is bad on a phone, so week = "week agenda".)
- **Year** = the existing 12-month strip expands into a fuller year overview (tap a month → jump to Month view)
- Remembers your last used view.

### 2. 🔔 Reminders on plans (reuses the task reminder engine)
- In the plan modal, add **"Remind me"**: None · At time · 15 min before · 1 hour before · 1 day before
- Fires the same full-screen alert + vibration + browser notification we already use for tasks
- If a plan has no time set, "At time" defaults to **09:00** (and the modal says so)
- Per-plan `reminder_fired` guard so it never repeats the same day
- ⚠️ **Honest limitation (same as tasks):** a fully-closed PWA cannot wake itself on Android/iOS. The alert fires while the app is open or recently used. Repeat this to users — no false promises.

### 3. 🔗 "Also add to My Day as a task" (opt-in per plan)
- A checkbox in the plan modal: *"Also add to My Day as a task"*
- When ticked, saving the plan also creates a linked task (stored with `plan_id`) so it shows in your task list + gets task reminders
- **Default OFF** — keeps your earlier decision that plans and tasks stay separate unless *you* choose to link them
- Editing/deleting the plan offers to update/remove the linked task

### 4. 🔁 Repeat: "ends on" date + every-N intervals
- Extend repeat: **Every 1 / 2 / 3 weeks**, **Every 1 / 2 / 3 months**
- Optional **"Ends on"** date — after that date the plan stops repeating (stored as `repeat_until`)
- Existing plans keep working (treated as interval 1, no end)

### 5. 📆 Hijri date in the plan modal + quick "Move" 
- Under the date picker, show the **Hijri equivalent** (e.g. "12 Rabi al-Awwal 1448") using the Hijri map we already fetch
- A **"Move to…"** button on an existing plan to quickly reschedule it to another date

---

## Files & data
- `index.html` only + `sw.js` cache bump → **v35**
- Plan fields added (all optional, old plans unaffected):
  `reminder_minutes`, `reminder_fired`, `repeat_interval`, `repeat_until`, `hijri_label` (display only), `linked_task_id`
- New i18n keys EN + AR for every new label

## Verification protocol (what I learned the hard way)
1. `</html>` == 1, `node --check` on inline JS
2. Unit-test `planMatchesDate` with intervals + `repeat_until` (I'll write the test table)
3. **Measure in headless Chromium** (iPhone 390×844 + small Android 360×640) that:
   - Week/Year views don't put content under the bottom nav
   - the plan modal fits and scrolls on a small screen
4. Push → you preview live on GitHub Pages → then Hostinger

---

## Order of work (if you approve all 5)
1. View switcher + week agenda (biggest visual win)
2. Reminders on plans (reuse engine, low risk)
3. Repeat intervals + ends-on
4. Hijri label + Move
5. Link plan → task (most delicate, touches tasks — do last)

---

## Not in this tier (keep for later)
- Drag-and-drop rescheduling
- Plan sharing with groups (Phase 3)
- Sync plans to Supabase across devices
