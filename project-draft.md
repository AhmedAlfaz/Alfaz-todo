# Project Draft — Alfaz todo Vision

> Living brainstorm. Thoughts, ideas, and directions that evolve as we learn and build.
> This file helps us find the final plan for v1.

## Where We Started
- Personal Islamic task/prayer/Qibla PWA
- Offline-first, single-file HTML app
- Working MVP hosted on GitHub Pages

## Where We're Going
- Minimalize first — match project to current knowledge + database limits
- Start with limited users, test with real people
- Target specific user groups with features they genuinely need daily
- Our focus: infrastructure and innovative features that solve real daily problems
- Grow into a globally competitive model when resources allow

## The Problem We're Solving
- Many apps do the same core: tasks, prayer times, reminders
- What's missing: secure communication + task management in one place
- People need tools for groups, teams, organizations — not just individuals

## What Makes Us Different
- Communication tools (public + private chat)
- Sharing tools (shared tasks, announcements)
- Very secure database and encryption
- Islamic productivity tools built in (prayer, Qibla, azan)
- Community groups with invite system

## Core Feature Ideas (unsorted, evolving)

### Must Have (v1 candidates)
- [x] User accounts + authentication ✓
- [x] Cloud sync (tasks across devices) ✓
- [ ] Groups / organizations
- [ ] Shared task lists
- [ ] Announcements

### Should Have (v1.1+)
- [ ] Public chat
- [ ] Private chat
- [ ] Real-time messaging
- [ ] File/image sharing

### Could Have (v2+)
- [ ] Admin dashboard
- [ ] Role-based permissions
- [ ] Audit logs
- [x] Multi-language support beyond EN/AR ✓
- [ ] Premium features / monetization

### Dream Features (future)
- [ ] Custom branding for organizations
- [ ] API for third-party integrations
- [ ] Mobile app (native)
- [x] Voice notes (researched — Web Speech API viable)

## Technical Direction
- **Backend:** Supabase (auth + database + realtime + storage) ✓
- **Frontend:** CDN-only, no build system (Tailwind, Font Awesome, Supabase JS SDK) ✓
- **PWA:** installable on mobile, works offline after first load ✓
- **Data:** Encrypted at rest (Supabase handles this)
- **Hosting:** GitHub Pages (frontend) + Supabase Cloud (backend)

## Offline Strategy

> **Offline-first reading, online-first writing.** App always works offline for cached data. Writes sync when connection is available.

### Works Offline (no internet needed)
- Personal tasks (localStorage) ✓
- Prayer times (cached after first load) ✓
- Qibla compass (pure math) ✓
- App navigation and UI (service worker) ✓
- Dark mode / language preferences ✓

### Needs Internet (syncs when connected)
- Shared group tasks → Supabase, cached in localStorage
- Announcements → Supabase, cached in localStorage
- Chat messages → Supabase, cached in localStorage
- Login/signup → must be online to authenticate ✓

### Offline UX
- Show "You're offline" banner when no connection
- Changes saved locally, auto-sync when back online
- Last-write-wins for conflicts (simplest for v1)

## Decisions Log

- [2026-07-17] Supabase confirmed as backend (over Hostinger — easier, faster, scales better)
- [2026-07-17] Cloud-first with offline caching (over local-only — app needs internet for team features)
- [2026-07-17] Working as CEO + PM pair — SKILL.md + AGENTS.md govern workflow
- [2026-07-17] Offline-first reading, online-first writing — app works without internet for cached data
- [2026-07-18] Minimalize first — match project to current knowledge + database limits
- [2026-07-18] Target specific user groups with features they genuinely need daily
- [2026-07-18] Start small, learn by building, validate with limited real users, then grow
- [2026-07-18] Azan audio fixed — replaced broken CDN links with real Azan MP3s from Kiwifu/adhan-mp3, stored locally
- [2026-07-18] Supabase key format corrected — was using invalid `sb_publishable_...` format, now using correct JWT
- [2026-07-19] Phase 0 complete — all bugs fixed, auth working, cloud sync verified
- [2026-07-19] Phase 1 complete — Supabase auth + cloud tasks working end-to-end
- [2026-07-19] TickTick research complete — 8 key features identified for inspiration
- [2026-07-19] Voice input researched — Web Speech API viable on Chrome/Edge/Android, limited on iOS
- [2026-07-19] Alert options researched — Notification API + Service Worker viable for reminders
- [2026-07-29] Phase 2 audit complete — 5 of 6 features built (smart lists, recurring tasks, voice input, reminders). Implementing natural language date/time parsing (EN/AR).
- [2026-07-29] Phase 2 COMPLETE — Implemented offline-first natural language date & time parsing for both English and Arabic (RTL-aware, zero external dependencies).
- [2026-07-29] Phase 2.5 defined — Approved 3-Pillar Islamic Library & Audio Architecture: Dedicated Library tab, Golden 20 catalog + Custom Duas Creator, Smart Habit Cards with Tap Counters, and 3-Tier Audio Engine with spoken Adhkar reminder tones.
- [2026-07-29] Phase 2.5 Pillar 1 & 2 complete — Built dedicated Library tab with Golden 20 essential catalog, Custom Duas Creator modal, One-Tap scheduling to My Day, and interactive Tap Counter Badges on task cards.
- [2026-07-29] Phase 2.5 Quran Khatmah Complete — Added 3 Quran Riwayat (Hafs, Warsh, Qalun) and Khatmah setup modal with Classic/Custom plans (30-day, 60-day, 7-day, Custom) and choice of daily tracking (by 5 Prayers or by Page Count).
- [2026-07-29] Phase 2.5 Quran Reader & Bookmark Complete — Built full 114-Surah Quran Reader inside Library with 3 Riwayat (Hafs, Warsh, Qalun), offline static caching, and persistent Bookmark/Resume banner (🔖 mark a pause to resume reading).

## Supabase Free Tier Constraints

| Resource | Limit | Strategy |
|---|---|---|
| Database | 500 MB | Minimal schema, data retention policies |
| File storage | 1 GB | Limit images, text-only chat for v1 |
| Bandwidth | 5 GB/month | Cache aggressively, sync deltas |
| MAU | 50,000 | Generous for first users |
| Realtime | 200 peak | Small groups only for chat |
| Inactivity | 1 week pause | Need keepalive mechanism |
| Free projects | 2 max | Don't waste on experiments |
| Backups | None | We manage our own |

## Development Phases

### Phase 0 (COMPLETE ✓) — Fix Bugs + Learn
- Fix all existing bugs (7 fixed, azan audio FIXED ✓)
- Learn Supabase basics ✓
- Define first user group ✓

### Phase 1 (COMPLETE ✓) — Foundation
- Supabase project setup ✓
- Auth (email + password) ✓
- Database schema (users, tasks) ✓
- Basic cloud sync (personal tasks) ✓

### Phase 2 (COMPLETE ✓) — Personal Productivity
**Goal:** Make the personal experience excellent before adding team features

- [x] Task structure upgrade (due dates, priorities, status) ✓
- [x] Smart lists (Today, Upcoming, Overdue, High Priority) ✓
- [x] Recurring tasks (daily, weekly, monthly) ✓
- [x] Voice input (Web Speech API) ✓
- [x] Natural language parsing (auto-detect dates/times) ✓
- [x] Reminders & alerts (browser notifications) ✓

**Timeline:** ~6 weeks
**Status:** All 6 features built and tested (EN & AR)

### Phase 2.5 (IN PROGRESS) — Islamic Library & Audio Architecture
**Goal:** Provide an authentic, offline-first Islamic Library (`المكتبة`) and 3-Tier Audio Engine connected to daily tasks and habits.

- [x] **Pillar 1: Dedicated Library Tab (`المكتبة`) & Catalog** ✓
  - "Golden 20" Essential Catalog (5 Morning Adhkar, 5 Evening Adhkar, 5 Daily Duas, 5 Quran/Worship Goals).
  - **Custom Duas Creator:** Let users type and save personal Duas/Adhkar with custom tap counts, cached offline & synced via Supabase.
  - **3 Quran Riwayat & Khatmah Creator:** Choice of 3 Riwayat (*Hafs 'an 'Asim, Warsh 'an Nafi', Qalun 'an Nafi'*), Classic/Custom Pace Plans (30-day, 60-day, 7-day, Custom), and choice of daily tracking (*by 5 Prayers or by Page Count*).
  - **Built-In Quran Reader (`قارئ القرآن الكريم`):** Full 114 Surah reader with choice of 3 Riwayat (*Hafs, Warsh, Qalun*), offline caching for core Surahs, and persistent **🔖 Mark Pause / Resume Bookmark** banner.
- [x] **Pillar 2: Smart Habit Cards & One-Tap Scheduling** ✓
  - **`➕ Add to My Day` button** on every Library item.
  - Interactive **Smart Habit Cards** in My Day with built-in **Tap Counters (`0/33`, `0/3`)** and auto-recurring spiritual reminders.
- [ ] **Pillar 3: 3-Tier Audio Engine & Spoken Reminder Tones**
  - **Tier 1 (Prayer Azan):** Full Azan MP3s for the 5 daily prayers.
  - **Tier 2 (Spoken Adhkar & Spiritual Habits):** Gentle spoken Adhkar audio tones (*Bismillah*, *Alhamdulillah*, *Salawat on Prophet ﷺ*, *Takbeer*, *SubhanAllah*) and calm spiritual chimes.
  - **Tier 3 (Work & Personal Tasks):** Subtle, modern productivity chimes for regular tasks.

### Phase 3 — Team Features
- Groups / organizations
- Shared task lists
- Announcements

### Phase 4 — Communication
- Chat (text-only for v1)
- Real-time updates

### Phase 5+ — Scale
- Paid database when needed
- Advanced features
- Global expansion

## Competitive Landscape
- Todoist, Microsoft To-Do, Google Tasks — personal only, no team features
- Slack, Discord — communication but not task-focused
- Trello, Asana — project management, not personal/Islamic
- **Gap:** No app combines Islamic productivity + team tasks + secure communication

## What We're Learning
- (See SKILL.md Section 6 for technical lessons)

## Open Questions (Partially Answered)

- MVP scope: minimal — whatever the first user group needs daily, nothing more
- Features vs simplicity: simplicity wins. Every feature must prove daily value
- Go-to-market: test with specific community first, grow by word of mouth
- Monetization: decide later. Free for now, premium features when scaling
- Auth methods: start simple (email + password), add Google/phone later
- Group invites: start simple (invite codes), add links/QR later
- Offline conflicts: last-write-wins for v1, revisit when needed
