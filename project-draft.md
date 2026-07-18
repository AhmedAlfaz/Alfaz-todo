# Project Draft — Alfaz todo Vision

> Living brainstorm. Thoughts, ideas, and directions that evolve as we learn and build.
> This file helps us find the final plan for v1.

## Where We Started
- Personal Islamic task/prayer/Qibla PWA
- Offline-first, single-file HTML app
- Working MVP hosted on GitHub Pages

## Where We're Going
- Secure team reminder and communication platform
- Start locally and offline → grow to cloudy and global
- Build, learn, improve, and design at the same time — not a fixed roadmap

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
- [ ] User accounts + authentication
- [ ] Cloud sync (tasks across devices)
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
- [ ] Multi-language support beyond EN/AR
- [ ] Premium features / monetization

### Dream Features (future)
- [ ] Custom branding for organizations
- [ ] API for third-party integrations
- [ ] Mobile app (native)
- [ ] Voice notes

## Technical Direction
- **Backend:** Supabase (auth + database + realtime + storage)
- **Frontend:** CDN-only, no build system (Tailwind, Font Awesome, Supabase JS SDK)
- **PWA:** installable on mobile, works offline after first load
- **Data:** Encrypted at rest (Supabase handles this)
- **Hosting:** GitHub Pages (frontend) + Supabase Cloud (backend)

## Offline Strategy

> **Offline-first reading, online-first writing.** App always works offline for cached data. Writes sync when connection is available.

### Works Offline (no internet needed)
- Personal tasks (localStorage)
- Prayer times (cached after first load)
- Qibla compass (pure math)
- App navigation and UI (service worker)
- Dark mode / language preferences

### Needs Internet (syncs when connected)
- Shared group tasks → Supabase, cached in localStorage
- Announcements → Supabase, cached in localStorage
- Chat messages → Supabase, cached in localStorage
- Login/signup → must be online to authenticate

### Offline UX
- Show "You're offline" banner when no connection
- Changes saved locally, auto-sync when back online
- Last-write-wins for conflicts (simplest for v1)

## Decisions Log

- [2026-07-17] Supabase confirmed as backend (over Hostinger — easier, faster, scales better)
- [2026-07-17] Cloud-first with offline caching (over local-only — app needs internet for team features)
- [2026-07-17] Working as CEO + PM pair — SKILL.md + AGENTS.md govern workflow
- [2026-07-17] Offline-first reading, online-first writing — app works without internet for cached data

## Competitive Landscape
- Todoist, Microsoft To-Do, Google Tasks — personal only, no team features
- Slack, Discord — communication but not task-focused
- Trello, Asana — project management, not personal/Islamic
- **Gap:** No app combines Islamic productivity + team tasks + secure communication

## What We're Learning
- (See SKILL.md Section 6 for technical lessons)

## Open Questions
- What's the minimum viable product that's unique enough to attract users?
- How do we balance features vs. simplicity?
- What's the go-to-market strategy for a community tool?
- Free forever, or freemium?
- Auth methods: Google only, or also email/password and phone?
- Group invite system: invite codes, links, or QR codes?
- How to handle data conflicts when two people edit offline?
