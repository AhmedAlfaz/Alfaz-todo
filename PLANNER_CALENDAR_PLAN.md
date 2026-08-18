# 🗓️ ABDO Planner Calendar — Phase 2.6 Plan (draft for approval)

**Date:** 2026-08-19 · **Status:** Proposal — nothing built yet

---

## 1. Why we're doing this

- The sidebar is getting busy (My Day, Prayers, Qibla, Library, Occasions, Groups + buttons).
- The calendar is currently a standalone screen only for **occasions** (Islamic + Egypt holidays).
- Goal: make it a real **planner** — users add their own **plans** to any day, view by year, and it lives on the **Home page footer** instead of the sidebar.

---

## 2. What similar apps do (research summary)

| App | Calendar / planning ideas worth copying |
|---|---|
| **TickTick** | Year → Month → Week → Day → Agenda views. *"Yearly View helps map out your year with clarity."* Dots/badges on days with events. |
| **Any.do** | "My Day" home focus + simple week view + morning "Plan Your Day" ritual. Keep it minimal, no overwhelm. |
| **Todoist** | Natural-language dates + recurrence ("every Friday at 3pm", "every 14 Jan"). |
| **Structured** | Visual day timeline (blocks). Maybe later — not in this phase. |
| **Muslim Pro / Athan Pro** | Hijri calendar with Islamic dates pre-marked, Ramadan timetables, date converter (Gregorian ↔ Hijri). |

**Common pattern:** month grid → tap a day → day panel with details → add/edit/delete events → recurring options → a **year view** for the big picture. Occasions are a read-only layer; personal plans are the editable layer.

---

## 3. What I propose for ABDO (v2.6)

### A. Declutter the sidebar
- Remove the **"Occasions"** nav item from the sidebar.
- The calendar becomes the **Planner**, living on the **Home (My Day) footer**.

### B. Home footer — compact Planner card
- At the bottom of My Day: a small card showing:
  - **This month** mini month-grid (compact, ~7×6)
  - Days with events/plans show a **dot**
  - "Up next" line (next occasion or next plan)
  - Tap "Open Planner" → full-screen planner
- Zero-annoyance: it's a passive card, not a popup.

### C. Full Planner screen (upgraded calendar)
Keeps everything we already built (Hijri month mapping, Islamic + Egypt occasions, add-occasion-to-my-day) and adds:

1. **Month view** (existing grid) — now with two layers:
   - Occasion dots (Islamic 🟢 / National 🔵 / Festival 🟣)
   - **Personal plan dots** (your own color)
2. **Day panel** — tap any day:
   - Shows that day's occasion(s) + your plans
   - **Add Plan** / **Edit** / **Delete**
3. **Year view** — a 12-month mini-grid to "map out your year" (TickTick-style). Tap any month → jump to that month.
4. **Plan fields** (keep simple):
   - Title (required) · optional time · optional note
   - **Repeat:** none / daily / weekly / monthly / **yearly** (e.g. birthday, anniversary, "every Ramadan 1")
   - Color dot for visual grouping

### D. Storage — two options (need your choice)
- **Option 1 (recommended first):** plans saved on the phone (localStorage), like guest tasks. Works offline, no account, zero setup. Matches our guest-first philosophy.
- **Option 2:** also sync to Supabase (`plans` table) so plans follow the user across devices — requires you to paste **one small SQL block** into Supabase SQL editor once (I'll write it for you).

### E. Keep consistent
- English + Arabic (عبده), RTL-aware, dark-mode-aware, no new build tools, all in `index.html` + cache bump.

---

## 4. What I will NOT do in this phase
- No drag-and-drop time blocks (Structured-style) — overkill for now.
- No reminders on plans yet (tasks already have reminders; plans are calendar entries). *Could add later if you want.*
- No Phase 3 (Groups) — untouched until you approve it later.

---

## 5. Build steps (after you approve)
1. Move `#calendar-view` markup → renamed `#planner-view`, reuse existing occasion logic.
2. Add compact planner card at the bottom of `#tasks-view` (My Day footer).
3. Add plan data model + localStorage (and optional Supabase SQL).
4. Add Year view + day-panel editing + repeat options.
5. i18n EN/AR keys, RTL checks, cache bump v29, push → you preview on GitHub Pages → redeploy to Hostinger.

**Estimated:** one focused build session, then your review on phone.
