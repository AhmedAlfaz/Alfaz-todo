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
- [2026-07-18] Minimalize first — match project to current knowledge + database limits
- [2026-07-18] Target specific user groups with features they genuinely need daily
- [2026-07-18] Start small, learn by building, validate with limited real users, then grow

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

### Phase 0 (Current) — Fix Bugs + Learn
- Fix all existing bugs (7 fixed, azan audio pending)
- Learn Supabase basics
- Define first user group

### Phase 1 — Foundation
- Supabase project setup
- Auth (email + password)
- Database schema (users, tasks)
- Basic cloud sync (personal tasks)

### Phase 2 — Team Features
- Groups / organizations
- Shared task lists
- Announcements

### Phase 3 — Communication
- Chat (text-only for v1)
- Real-time updates

### Phase 4+ — Scale
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
