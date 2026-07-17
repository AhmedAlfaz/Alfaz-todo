# AGENTS.md

## Project

Static single-page PWA: **Alfaz todo** — Islamic tasks, prayer reminders, and Qibla compass. No build system, no bundler, no package manager. Plain HTML/CSS/JS served directly.

## Structure

- `index.html` — main app (all HTML, CSS, JS in one file)
- `manifest.json` — PWA manifest (app name, icons, theme)
- `sw.js` — service worker (caching, offline, notifications)
- `ALFA LOGO icon.jpg` — app logo used for favicon and PWA icon
- `2/index2.html` — alternate/backup version of the same app

## Tech Stack

- **Tailwind CSS** via CDN (`cdn.tailwindcss.com`) with inline config — no local Tailwind install
- **Font Awesome 6.4** via CDN for icons
- **Aladhan API** (`api.aladhan.com`) for prayer times — requires internet
- **localStorage** for tasks, language, dark mode, and prayer time caching
- No framework, no npm, no build step

## Conventions

- i18n keys use `data-i18n` and `data-i18n-placeholder` attributes; translations are in the `i18n` JS object (en/ar only)
- RTL support: `dir` attribute toggled on `<html>` based on language
- Dark mode: Tailwind `darkMode: 'class'`, toggled via `document.documentElement.classList`
- All JS is inline in a `<script>` tag at the bottom of the HTML file
- CSS is inline in a `<style>` tag in `<head>`

## Editing

- Open `index.html` directly in a browser to preview — no dev server needed
- CDN dependencies mean changes require internet to render correctly
- Prayer times use calculation method 5 (Umm al-Qura) — don't change without reason
- Azan audio sources are CDN-hosted Quran recitations from `cdn.islamic.network`

## Agent Rules

- **One file at a time.** Never touch `2/index2.html` unless the user explicitly asks.
- **Verify after every edit.** Open the browser and visually confirm the change before marking it done. Look for broken layout, JS errors in console, missing translations.
- **RTL-aware.** When editing markup, check that your changes work with `dir="rtl"` (Arabic). Use logical CSS properties (`ms-`, `me-`, `ps-`, `pe-`, `start`, `end`) not physical left/right where possible.
- **Dark mode.** Always add `dark:` variants alongside light-mode Tailwind classes. Missing dark variants are a common visual bug.
- **i18n completeness.** If you add a user-visible string, add both `en` and `ar` entries in the `i18n` object and set the correct `data-i18n` / `data-i18n-placeholder` attribute.
- **No external dependencies.** Don't add npm packages, build tools, or server-side code. Everything must work as plain HTML served from a file or static host.
