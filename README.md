# ABDO (عبده) — Islamic Tasks & Reminders

**ABDO** is a free, offline-capable **Progressive Web App (PWA)** that helps Muslims manage daily tasks, prayer times, Quran reading, dhikr, Qibla direction, a planner calendar, and Islamic occasions — all in one place, in English and Arabic.

> 🌙 تطبيق عبده — مهامك وأذكارك الإسلامية: مواقيت الصلاة، القرآن، القبلة، المخطط، والمهام. مجاني ويعمل بدون إنترنت.

---

## ✨ Features

- 🕌 **Prayer times** (5 daily, location-based) + azan audio alerts + vibration + notifications
- 📖 **Quran reader** with real **Hafs / Warsh / Qalun** text + audio recitation with per-ayah highlighting + resume where you stopped
- 📿 **Library** of authentic adhkar & duas, with "Read & Complete" tasks
- 🧭 **Qibla compass** (merged into the Prayers page)
- 🗓️ **Planner calendar** — personal plans (with daily/weekly/monthly/yearly repeats) + Islamic occasions & Egypt holidays
- ✅ **Task manager** — smart lists (My Day / Upcoming / Overdue / High), reminders with snooze, voice input, natural-language dates
- 📱 **Installable PWA** — works offline, updates via in-app Refresh
- 🌙 **English + Arabic**, RTL-aware, dark mode

---

## 🧱 Tech Stack

| Thing | What we use |
|---|---|
| App | **One static HTML file** (`index.html` — all HTML/CSS/JS inline) |
| Styling | Tailwind CSS (CDN) |
| Icons | Font Awesome (CDN) |
| Auth & sync (optional) | Supabase (anon key is public by design) |
| Offline + updates | Service worker (`sw.js`) |
| Build tools | **None** — no bundler, no package manager, no framework |

---

## 🚀 Run locally

```bash
# serve this folder with any static file server:
python3 -m http.server 8080
# then open http://localhost:8080
```

## 🚀 Deploy

- **GitHub Pages:** push to `main` → site auto-builds at
  `https://ahmedalfaz.github.io/Alfaz-todo/`
- **Hostinger:** upload `index.html`, `manifest.json`, `sw.js`, `brand/`, `audio/` into `public_html` — see **[DEPLOYMENT.md](DEPLOYMENT.md)** for the quick re-deploy checklist.

---

## 📁 Project structure

```
├── index.html        ← the whole app (HTML + CSS + JS)
├── sw.js             ← service worker (offline cache, notifications, updates)
├── manifest.json     ← PWA manifest (installable app)
├── brand/            ← app icons (192/512 + maskable)
├── audio/            ← azan MP3 files
├── AGENTS.md         ← project rules & conventions
├── DEPLOYMENT.md     ← Hostinger deployment guide
└── ALERTS_AND_AUDIO_PLAN.md ← alerts/sound design notes
```

---

## 🤝 Contributing

We're a small project and happy to accept help! Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** first — it has the few simple rules that keep this app working (single-file, i18n, cache protocol).

- 🐛 Found a bug? Open an **[Issue](https://github.com/AhmedAlfaz/Alfaz-todo/issues)**
- 💡 Want to contribute code? Open a **[Pull Request](https://github.com/AhmedAlfaz/Alfaz-todo/pulls)**

---

## 📄 License

© 2026 Ahmed Al-Faz. License to be defined — ask before commercial reuse.
