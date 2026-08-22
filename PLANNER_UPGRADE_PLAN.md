# 🗓️ Planner Upgrade — Tier 1 + Yearly (v2.8 plan)

**Date:** 2026-08-19 · **Status:** Approved scope — building next

---

## What we're adding

### 1. Upcoming list (top of Planner page)
- The next **10** plans + occasions (from today), in date order.
- Each row: date, name, type icon (plan dot / occasion). Tap → jump to that day in the month view.
- Shows "Nothing coming up" if empty. This is the "at a glance" that makes the planner feel alive.

### 2. Plan status — Done / Undone
- Each plan can be marked **Done ✓**.
- Done plans: strike-through title, dimmed, shown at the bottom of the day panel, and a small green check.
- Toggle via a ✓ button next to each plan. Also counts "done today" for a tiny sense of progress.

### 3. Categories + icons
- Replaces the bare color dot with a **category** (icon + color):
  🎯 Goal · 💊 Health · 💼 Work · 👨‍👩‍👧 Family · ✈️ Travel · 🕌 Worship · 🎂 Special · 📌 Other
- Stored as `category` on the plan; falls back to a plain dot for old plans.

### 4. Filter chips on the Planner page
- **All · My Plans · Occasions**
- "My Plans": shows only personal plans (grid dots + day panel + upcoming).
- "Occasions": shows only occasions.
- "All" (default): everything.

### 5. Yearly overview (yearly showing)
- A **Year strip** above the month grid: 12 mini month-boxes for the selected year.
- Each mini-box: month name + small dots count (plans/occasions).
- Current month highlighted. Tap any month → jump the main grid to it.
- Helps "map out your year" (TickTick-style) without a heavy separate screen.

---

## Files touched
- `index.html` only (plus `sw.js` cache bump → v31, and `?v=31`).
- New storage: plans gain optional `status` ('done'|'') and `category`.
- Old plans keep working (default category, not done).

## i18n
- New EN + AR keys: `upcomingPlans`, `nothingUpcoming`, `done`, `all`, `myPlans`, `occasions`, `year`, `category`, each category name, `yearlyOverview`.

## Verify
- `</html>` == 1, `node --check` on inline JS, unit-test `planMatchesDate` + upcoming sort.
- Push → preview on GitHub Pages → you review on phone → redeploy Hostinger.
