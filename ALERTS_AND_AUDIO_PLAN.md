# 📋 Executive Blueprint: Modern Unified Alert, Notification & Sound System
**Project:** Alfaz-todo  
**Philosophy:** *"Zero Annoyance — Help and Make Life Easier (بدون إزعاج، تسهيل الحياة)"*

---

## 1. Core Guiding Philosophy: Calm by Default

Most productivity and prayer apps become annoying by constantly bombarding the user with loud alarms, aggressive popups, and nagging confirmations for every action. 

**Alfaz-todo operates on three rules:**
1. **Never Annoy the User (بدون إزعاج):** No spammy popups, no nagging dialogs, no harsh buzzer sounds.
2. **Make Life Easier (تسهيل الحياة):** Reminders are soft, peaceful, and actionable with a single tap.
3. **Respect Quiet & Work Hours (ساعات الهدوء):** If a user is in a meeting or sleeping, non-prayer reminders stay quiet and never scream.

---

## 2. The 3 Alert Types (Tailored Experiences)

Instead of one generic popup for everything, we distinguish between three types of daily events:

### **A. Prayer Times — Full Azan Prayer Experience (أذان الصلاة)**
* **When it fires:** At the 5 daily prayer times (*Fajr, Dhuhr, Asr, Maghrib, Isha*).
* **What the user sees:**
  * **Screen ON:** A serene, full-screen **Azan Prayer Modal (`#azan-alert-modal`)** showing a glowing mosque illustration, the prayer name, and exact time (*e.g., `🕌 صلاة المغرب — Maghrib 18:45`*).
  * **Screen OFF / Locked:** A system lock-screen notification wakes up the display: `🕌 أذان المغرب — حان الآن موعد الصلاة`. Tapping it opens the Full-Screen Azan Modal.
* **What the user hears:** The full, authentic Azan MP3 they selected (*Makkah, Madinah, Al-Aqsa, Egypt, Turkey, Alafasy, etc.*).
* **One-Tap Controls:**
  * `🔊 Listen to Azan` (if OS blocked autoplay)
  * `⏹ Silence Azan` (mutes audio instantly)
  * `✅ I Have Prayed (أتممت الصلاة)` (logs the prayer and closes the screen peacefully)

### **B. Adhkar, Quran & Worship Goals (أوراد العبادة والأذكار)**
* **When it fires:** When a scheduled Library habit or Dhikr reminder occurs (*e.g., Morning Adhkar, Surah Al-Kahf on Friday*).
* **What the user sees:** A calm, unobtrusive **Spiritual Banner Card** that slides down from the top of the app (it does *not* block your screen with a popup modal).
* **What the user hears:** 
  * Default: A serene, gentle **Oud/Harp Harmonic Chime** (Web Audio API).
  * Optional: **Spoken Arabic Dhikr Name (`Web Speech API`)** — e.g. soft voice saying *"حان موعد أذكار الصباح"*.
* **One-Tap Controls:**
  * `📖 Read Now (قراءة الآن)` → Opens the Quran Reader or full-text Dhikr Reader Modal.
  * `✅ Complete (إتمام)` → Marks the habit completed without opening a dialog.

### **C. Work & Personal Tasks (مهام العمل والحياة)**
* **When it fires:** At the exact due time or reminder time of a work/home task.
* **What the user sees:** A crisp, modern **Task Alert Banner** at the top of the screen: `⏰ Reminder: [Task Name]`.
* **What the user hears:** A subtle, modern **Crystal Productivity Chime** (like Apple Reminders — clean and professional).
* **One-Tap Controls:**
  * `✅ Complete (إنجاز)` → Marks the task done.
  * `💤 Snooze 15m (تأجيل ١٥ دقيقة)` → Delays the reminder peacefully.

---

## 3. The Sound Engine & Audio Unlocker (استوديو التنبيهات والأصوات)

### **A. How We Guarantee Sound Plays on Mobile (Android Chrome & iOS Safari)**
* **The Problem:** Mobile operating systems block audio autoplay (`audio.play()`) unless the user has interacted with the page, OR unless triggered by a native notification.
* **Our Solution (The Audio Unlocker):**
  1. On the user's very first touch/tap anywhere in the app, a silent 0.1s buffer unlocks our Web Audio Context and a permanent HTML `<audio id="azan-player">` element.
  2. For screen-off alerts, our Service Worker (`sw.js`) fires a system Web Notification that wakes the screen and plays the system chime/vibrate.

### **B. In-App Audio Studio Modal (`#audio-studio-modal`)**
Users can customize and test their sounds at any time without cluttering the UI:
* **Prayer Azan:** Choose from 13 MP3s + `▶️ Test`.
* **Adhkar Tone:** Choose between *Spiritual Harmonic Chime*, *Spoken Arabic Voice*, or *Silent* + `▶️ Test`.
* **Task Tone:** Choose between *Modern Productivity Chime*, *Spoken Reminder*, or *Silent* + `▶️ Test`.

### **C. The In-App Sound Reader (`مشغل التلاوة والأذكار الصوتي في المكتبة والقارئ`)**
To make the Quran, Adhkar, and Duas truly accessible and interactive for users who want to listen or repeat along:
* **Quran Reader Audio (`مشغل تلاوة القرآن الكريم`):**
  * Includes a **`▶️ Play Surah (`تشغيل السورة صوتياً`)` / `⏸ Pause` / `⏹ Stop`** audio player bar inside `#quran-reader-modal`.
  * Streams high-quality MP3 recitations by famous reciters (*e.g., Mishary Alafasy — `مشاري راشد العفاسي`*).
  * **Synchronized Verse-by-Verse Audio Highlighting (`تظليل الآية مع التلاوة`):** As the reciter reads each verse, the reader automatically highlights the current verse in golden amber and scrolls smoothly to follow along!
* **Dhikr & Dua Audio Reader (`استماع للأذكار والأدعية`):**
  * Includes an **`🔊 Listen / Play (`استماع`)`** button inside `#dhikr-reader-modal`.
  * Plays authentic recitations for Quranic Adhkar (*Ayat al-Kursi, Al-Ikhlas, Al-Falaq, An-Nas*) and clear spoken Arabic pronunciation for Prophetic Duas (*Sayyid al-Istighfar, Ya Hayyu Ya Qayyum, etc.*) so users can listen and repeat along (`الاستماع والترديد مع الذكر`).

---

## 4. Missed Reminders Catch-Up Engine (تنبيهات فائتة)

* **When it fires:** When a user opens the app after their phone was off, in silent mode, or asleep for hours.
* **How it works:**
  * Instead of bombarding the user with 5 delayed popups all at once, the app checks if any prayer or habit passed while asleep.
  * Displays **one clean summary banner**: `⏰ Missed While Away: Maghrib Prayer, Evening Adhkar`.
  * Allows the user to catch up with a single tap without any annoyance.

---

## 5. Implementation Roadmap & Verification Checklist

1. [x] **Step 1:** Add permanent `<audio id="azan-player">` and `unlockMobileAudio()` handler in `index.html`. ✓
2. [x] **Step 2:** Build Full-Screen Azan Prayer Modal (`#azan-alert-modal`) with `I Have Prayed` & `Silence` buttons. ✓
3. [x] **Step 3:** Implement Task Reminder Alert Modal (`#task-alarm-modal`), Snooze 15m, and Quran/Dhikr Sound Readers (`#quran-audio-bar` & `Listen & Repeat`) with verse-by-verse highlighting. ✓
4. [x] **Step 4:** Implement Missed Reminders Catch-Up Engine on `visibilitychange`. ✓
5. [ ] **Step 5:** Test and verify on mobile (screen ON and screen OFF).
