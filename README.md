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

## 🚀 One app, one link

**Canonical (the only link to share):** `https://firebrick-sardine-612688.hostingersite.com/`

There used to be two live copies — this repo's GitHub Pages build and the Hostinger site. That was a
mistake, not a feature: a PWA is defined by its **origin**, so two links meant two separate installed
apps, two offline caches, two sets of user data, and only one of them able to do push (OneSignal binds
an app id to a single origin, and only Hostinger can run the PHP sender). Users installing from the
"same" app were not getting the same app.

**The GitHub Pages URL is a workshop copy, not a product.** Any copy served from a non-canonical
origin labels itself on every load ("Workshop copy — not the real app"), so nobody mistakes it, and it
hides the Share button because sharing a copy is how we got here in the first place. Use it to check
work on a phone before it ships; never send it as the install link.

| | Hostinger | GitHub Pages |
|---|---|---|
| Purpose | the app users install | preview/testing only |
| Push reminders | yes | no (needs the PHP sender, which Pages cannot run) |
| Update path | upload to `public_html` | automatic on push to `main` |

Deploy to production = upload these to `public_html`: `index.html`, `sw.js`, `manifest.json`,
`site-config.json`, `brand/`, `push/`. See **[DEPLOYMENT.md](DEPLOYMENT.md)**.
`site-config.json` is the only file whose contents differ per host, and it is not edited per host:
it names the canonical link and the OneSignal app id, and is simply inert where that id does not belong.

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
