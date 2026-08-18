# 🚀 Hostinger Deployment Guide — ABDO (عبده)

**App Name:** ABDO (عبده) — Islamic Tasks & Reminders
**Deploy Target:** Hostinger Free Hosting
**Date:** 2026-08-18

---

## ⚡ Quick Re-Deploy Checklist (every time we push an update)

1. Open hPanel → **Files → File Manager** → your site → `public_html/`
2. Upload these (overwrite existing):
   - `index.html`  ← almost always
   - `sw.js`       ← almost always
   - `manifest.json` ← only if changed
   - `brand/` folder (3 icons) ← only if changed
   - `audio/` folder ← only if you changed azan sounds (rare)
3. Done. Users just tap **Refresh / Update App (🔄)** inside the app to get the new version.

> Tip: You never need to touch `audio/` unless we specifically say so.

---

## 📋 Pre-Deployment Checklist

- [x] Mobile Alert System working (Prayer Azan, Task Reminders, Audio Playback)
- [x] Screen Wake Lock API enabled
- [x] Vibration feedback active
- [x] Service Worker with badge & notification support
- [x] All files optimized and tested
- [ ] Hostinger FTP/File Manager credentials ready
- [ ] Custom domain or Hostinger subdomain chosen
- [ ] Supabase keys verified and active

---

## 📦 Files to Deploy

Upload these files to your Hostinger root folder:

```
/
├── index.html              ← Main app (all HTML/CSS/JS in one file)
├── manifest.json           ← PWA manifest (installable app)
├── sw.js                   ← Service Worker (offline, caching, notifications)
├── brand/                  ← ABDO app icons (favicon, PWA, notifications)
    ├── abdo-icon-192-wb.png
    ├── abdo-icon-512-wb.png
    └── abdo-icon-512-maskable-wb.png
└── audio/                  ← Azan MP3 audio files
    ├── makkah.mp3
    ├── madinah.mp3
    ├── alaqsa.mp3
    ├── egypt.mp3
    ├── turkey.mp3
    ├── alafasy.mp3
    ├── ... (other Azan files)
```

---

## 🔧 Hostinger Deployment Steps

### **Option 1: File Manager (Easiest for Beginners)**

1. **Log into Hostinger Control Panel**
   - Go to https://hpanel.hostinger.com
   - Enter your Hostinger credentials

2. **Navigate to File Manager**
   - Click **Files** → **File Manager**
   - You should see `public_html/` folder

3. **Upload All Files**
   - Right-click in `public_html/` → **Upload Files**
   - Select all files from `/workspaces/Alfaz-todo/`:
     - `index.html`
     - `manifest.json`
     - `sw.js`
   - Upload the `brand/` folder (contains the ABDO app icons)
   - Create an `audio/` folder inside `public_html/` and upload all MP3s there

4. **Verify Upload**
   - Refresh the File Manager
   - Confirm you see all files in `public_html/`

5. **Test the App**
   - Open your Hostinger domain in a browser:
     - If you have a custom domain: `https://your-domain.com`
     - If using Hostinger subdomain: `https://abdo.hostinger.com` (or your assigned subdomain)
   - The app should load immediately

---

### **Option 2: FTP (If You Prefer)**

1. **Get FTP Credentials**
   - Log into Hostinger Control Panel
   - Click **Files** → **FTP Accounts**
   - Copy the FTP host, username, and password

2. **Connect via FTP Client**
   - Download **FileZilla** (free) or use any FTP client
   - Connect to your FTP server using the Hostinger credentials
   - Navigate to `public_html/`

3. **Upload Files**
   - Drag-and-drop all files into `public_html/`
   - Create `audio/` folder
   - Upload all MP3s into the `audio/` folder

4. **Disconnect & Test**
   - Close the FTP connection
   - Open your domain in a browser to verify

---

## 🔗 Critical URLs to Verify

After deployment, test these:

✅ **Main App:** `https://your-domain.com/index.html` (or just `https://your-domain.com/`)  
✅ **Manifest:** `https://your-domain.com/manifest.json`  
✅ **Service Worker:** `https://your-domain.com/sw.js`  
✅ **Icon:** `https://your-domain.com/brand/abdo-icon-192-wb.png`  
✅ **Audio:** `https://your-domain.com/audio/makkah.mp3`  

---

## 🔑 Supabase Setup (Required for Cloud Features)

The app needs your Supabase credentials to work:

1. **Open the app in your browser**
2. **Navigate to:** Settings → (scroll to Auth section)
3. **Enter your Supabase credentials:**
   - Supabase URL
   - Supabase Public Key (Anon Key)
4. **Log in or Sign Up to verify connection**

---

## 📱 Mobile Testing Checklist

After deployment, test on a real mobile device:

### **Prayer Azan Alerts**
- [ ] Prayer time arrives → Azan modal appears
- [ ] Azan audio plays automatically (no manual click needed)
- [ ] Screen wakes up (even if phone is locked)
- [ ] Vibration pattern felt (3 pulses)
- [ ] Notification badge shows on lock screen
- [ ] "I Have Prayed" button works and closes alert

### **Task Reminders**
- [ ] Task due time arrives → Task modal appears
- [ ] Tone plays (based on audio settings)
- [ ] Vibration felt (2 pulses)
- [ ] "Complete Task" or "Snooze 15m" buttons work

### **Audio Playback**
- [ ] Quran reader plays audio smoothly
- [ ] Audio doesn't stutter or cut off
- [ ] Mute button silences audio
- [ ] Volume controls work

### **Offline Functionality**
- [ ] Disable WiFi/Data on phone
- [ ] App still works (navigation, cached data)
- [ ] Personal tasks still visible (from localStorage)
- [ ] Prayer times still show (cached from first load)
- [ ] Qibla compass still works (pure math)

### **PWA Installation**
- [ ] On Chrome/Android: Menu → "Install app" works
- [ ] On Safari/iOS: Share → "Add to Home Screen" works
- [ ] App opens full-screen without browser chrome
- [ ] All icons display correctly

---

## 🆘 Troubleshooting

### **Audio Not Playing on Mobile**
- ✅ We added Screen Wake Lock API + vibration (new in this version)
- Make sure notifications are enabled in phone settings
- Try different Azan tone from Audio Studio
- Check browser console for errors (F12 → Console)

### **App Blank/Doesn't Load**
- Check File Manager → `public_html/` has `index.html`
- Clear browser cache (Ctrl+Shift+Delete)
- Try incognito/private mode

### **Manifest/Icons Not Working**
- Verify `brand/abdo-icon-192-wb.png` is in `public_html/brand/`
- Check file name spelling (case-sensitive on Linux)
- Verify `manifest.json` path in HTML matches deployment

### **Service Worker Issues**
- Browsers cache SW aggressively
- Force refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Check DevTools → Application → Service Workers

---

## 📊 Deployment Monitoring

### **Check Hostinger Resource Usage**
1. Log into Hostinger Control Panel
2. Click **Website** → **Bandwidth**
3. Monitor traffic usage (Free plan has limits)

### **Check App Errors**
- Open app in browser
- Press **F12** → **Console** tab
- Look for red error messages
- Check **Network** tab for failed requests

---

## 🎯 What's New This Deployment (v23 — Step 5 Complete)

1. ✅ **Enhanced Mobile Audio Autoplay**
   - Better error handling for iOS/Android
   - Unlocks Web Audio Context on first tap
   - Fallback messages if audio can't autoplay

2. ✅ **Screen Wake Lock API**
   - Keeps screen ON during prayer alerts
   - Automatically releases after alert closes
   - Works on Android Chrome, Safari iOS 16+

3. ✅ **Vibration Patterns**
   - Prayer Azan: 300ms-100ms-300ms (strong triple pulse)
   - Task Reminder: 200ms-100ms-200ms (gentler double pulse)
   - Works on all phones with vibration motor

4. ✅ **Improved Notifications**
   - Badge icon shows on lock screen
   - Vibration pattern built into notification
   - Better fallback if Service Worker unavailable

---

## 🚀 After Deployment

1. **Share the App Link**
   - Send your Hostinger domain to users
   - They can install as PWA on mobile

2. **Monitor Performance**
   - Check Hostinger bandwidth usage
   - Watch for any error logs in console

3. **Collect Feedback**
   - Test with real users on their devices
   - Fix any platform-specific issues

4. **Keep It Updated**
   - Re-deploy whenever you add features
   - Use same File Manager steps

---

## 📞 Support & Questions

- **Hostinger Help:** https://support.hostinger.com
- **PWA Debugging:** Open DevTools (F12) → Application tab
- **Supabase Docs:** https://supabase.com/docs
- **Testing Tool:** https://www.webpagetest.org

---

**Status:** Ready for Production ✅  
**Last Updated:** 2026-08-18  
**App Version:** Step 5 Complete (Mobile Alerts Finished)
