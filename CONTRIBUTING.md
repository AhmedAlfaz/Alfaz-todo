# Contributing to ABDO (عبده)

Thanks for helping make ABDO better! 🙏 This file is short on purpose — the project has a few **important constraints** that keep it working on phones. Please read them before touching code.

---

## ⚠️ Ground rules (please read carefully)

### 1. Single-file app — no build system
- `index.html` is a **single self-contained file** (HTML + CSS + JS all inline).
- **No** build tools, bundlers, package managers, or frameworks. Don't add them.
- New external dependencies are only OK if approved (we already use Tailwind CDN, Font Awesome CDN, and the Supabase JS SDK via CDN).

### 2. i18n — every visible string in EN **and** AR
- Every user-visible string must be added to **both** the `en` and `ar` blocks in the `i18n` object inside `index.html`.
- The app is **RTL-aware**: test your changes in Arabic (`dir="rtl"`) and dark mode.

### 3. Cache protocol (critical — phones keep stale copies)
- Any change to `index.html` or `sw.js` **must** bump **both**:
  1. `CACHE_NAME` in `sw.js` (e.g. `alfaz-todo-v30` → `alfaz-todo-v31`)
  2. The `?v=NN` query in `checkForAppUpdate()` inside `index.html`
- This is how existing installed users get updates without reinstalling.

### 4. Verify before you push
- The file must contain **exactly one** `</html>` (duplicate tails break mobile launch).
- Extract inline `<script>` blocks and run `node --check` on them.
- If possible, test on a real phone (GitHub Pages preview works for this).

### 5. Never rename user-data keys
- `localStorage` keys like `alfatore_tasks`, `alfaz_plans`, `alfaz_quran_audio_pos`, etc. are **user data**.
- Renaming them logs people out or silently loses their data. Keep keys stable.

### 6. Don't touch `2/index2.html`
- That's a backup copy. Leave it alone.

### 7. Keep the planner/calendar and alerts code intact
- `index.html` has sensitive alert logic (azan at prayer time, task reminders, wake lock, vibration). Change it carefully — the owner tests these on real devices.

---

## 🐛 Reporting a bug (Issues)

When opening an issue, include:
- **Device** (iPhone / Android model) and **browser** (Safari / Chrome / version)
- **What you did** (steps)
- **What happened** vs **what you expected**
- Screenshot if possible

---

## 🧑‍💻 Contributing code (Pull Requests)

1. **Fork** the repo and create a branch (`git checkout -b fix/description`).
2. Make **small, focused** changes — one PR per concern.
3. Follow the ground rules above (i18n, cache bump, verify).
4. Open a **Pull Request** with a clear description of what and why.
5. The maintainer reviews and merges. Be patient — changes are tested on real phones before release.

---

**TL;DR:** single file, add both languages, bump the cache, don't rename storage keys, verify before pushing. That's it. 😊
