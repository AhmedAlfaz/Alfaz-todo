#!/usr/bin/env python3
"""v41 patch: wire the push client (inert without push-config.json) + cache bump.
Strict anchors; aborts without writing if anything does not match exactly once."""
import io, sys

P = '/home/user/Alfaz-todo/index.html'
SW = '/home/user/Alfaz-todo/sw.js'

s = io.open(P, encoding='utf-8').read()
before = len(s)

def sub(text, old, new, label):
    n = text.count(old)
    if n != 1:
        print(f"ABORT [{label}]: anchor matched {n}, expected 1"); sys.exit(1)
    print(f"ok  [{label}]")
    return text.replace(old, new)

# 1) scripts before </head>
s = sub(s, "  </style>\n</head>",
        '  </style>\n'
        '  <!-- ABDO push: inert until push-config.json exists on this origin. -->\n'
        '  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>\n'
        '  <script src="push/client.js" defer></script>\n'
        '</head>', 'head scripts')

# 2) i18n toast keys (en + ar) so the strings are not hard-coded in one language
s = sub(s, '        prayerTimesStale: "These times are ~{h}h old \u2014 check your connection and refresh.",',
           '        prayerTimesStale: "These times are ~{h}h old \u2014 check your connection and refresh.",\n'
           '        pushOnToast: "\U0001f514 Alerts are on \u2014 we will nudge you at prayer time and for tasks.",\n'
           '        pushFailToast: "Could not turn on alerts. They still work while the app is open.",',
           'i18n en push keys')

lines = s.split('\n')
ar_start = next((i for i, l in enumerate(lines) if l.strip() == 'ar: {'), None)
if ar_start is None:
    print("ABORT [i18n ar]: no ar block"); sys.exit(1)
tgt = None
for i in range(ar_start, min(ar_start + 220, len(lines))):
    if 'prayerTimesStale:' in lines[i]:
        tgt = i; break
if tgt is None:
    print("ABORT [i18n ar]: prayerTimesStale not found in ar block"); sys.exit(1)
if any('pushOnToast' in l for l in lines[ar_start:ar_start + 220]):
    print("ABORT [i18n ar]: push keys already present"); sys.exit(1)
ind = lines[tgt][:len(lines[tgt]) - len(lines[tgt].lstrip())]
lines.insert(tgt + 1, ind + 'pushOnToast: "\U0001f514 تم تفعيل التنبيهات \u2014 نذكّرك بوقت الصلاة وبمهامك.",')
lines.insert(tgt + 2, ind + 'pushFailToast: "لم نستطع تفعيل التنبيهات. التذكيرات تعمل طالما التطبيق مفتوح.",')
s = '\n'.join(lines)
print(f"ok  [i18n ar push keys] after line {tgt + 1}")

# 3) refresh query v40 -> v41
s = sub(s, "?v=40&t=", "?v=41&t=", 'refresh query')

io.open(P, 'w', encoding='utf-8').write(s)
after = len(s)
print(f"\nindex.html {before} -> {after} (delta {after - before})")
if after < before or after < 250000:
    print("ABORT: file did not grow as expected"); sys.exit(1)

w = io.open(SW, encoding='utf-8').read()
old_shell = """const SHELL = [
  './',
  './index.html',
  './manifest.json',"""
new_shell = """const SHELL = [
  './',
  './index.html',
  './manifest.json',
  './push-config.json',"""
if w.count(old_shell) != 1:
    print(f"ABORT [sw shell]: {w.count(old_shell)}"); sys.exit(1)
w = w.replace(old_shell, new_shell)
if w.count("CACHE_NAME = 'alfaz-todo-v40'") != 1:
    print("ABORT [sw version]"); sys.exit(1)
w = w.replace("CACHE_NAME = 'alfaz-todo-v40'", "CACHE_NAME = 'alfaz-todo-v41'")
print("ok  [sw cache v41 + config in shell]")
io.open(SW, 'w', encoding='utf-8').write(w)
print("\nDONE")
