import io, sys

C = '/home/user/Alfaz-todo/push/client.js'
s = io.open(C, encoding='utf-8').read()

start = s.index('  function showVersion() {')
tail_marker = "el.parentNode.title = 'uid ' + pushUid();"
end = s.index('\n  }', s.index(tail_marker)) + len('\n  }')

new = """  // One always-populated line. An earlier version only wrote text when it happened to find a
  // matching cache entry, so any unexpected state left the '…' placeholder on screen and told us
  // nothing. A diagnostic that can stay silent is worse than none.
  function reportState() {
    try {
      var el = document.getElementById('app-version-num');
      if (!el) return;
      var ver = 'v?';
      try { ver = window.__abdoPushVersion || ver; } catch (e) {}
      var state = ls(STATE_KEY);
      var label = state === 'on' ? 'alerts ON' : (state === 'off' ? 'alerts OFF' : 'not asked');
      var sdk = !cfg ? 'no config here' : (!window.OneSignal ? 'sdk missing' : 'sdk loading');
      try {
        if (window.OneSignal && window.OneSignal.User && window.OneSignal.User.pushSubscription) {
          var sub = null;
          try { sub = window.OneSignal.User.pushSubscription.get(); } catch (e0) {}
          sdk = (sub && sub.id) ? 'id ok' : 'no id yet';
        }
      } catch (e) {}
      var perm = 'n/a';
      try { perm = ('Notification' in window) ? Notification.permission : 'unsupported'; } catch (e) {}
      var extra = label + '  ·  ' + sdk + '  ·  ' + perm;
      if (state === 'on') {
        try { extra = label + '  ·  ' + (ls('alfaz_push_player') ? 'queued' : 'not synced') + '  ·  ' + perm; } catch (e) {}
      }
      el.textContent = ver + '  ·  ' + extra;
      try { el.parentNode.title = 'uid ' + pushUid(); } catch (e) {}
    } catch (e) {
      try { document.getElementById('app-version-num').textContent = 'report failed'; } catch (e2) {}
    }
  }"""
s = s[:start] + new + s[end:]

# version is now published once, from the service worker registration, so it cannot be blank
s = s.replace("""      if ('serviceWorker' in navigator) {""",
              """      if ('serviceWorker' in navigator) {""")

s = s.replace('statusLine();', 'reportState();')
s = s.replace('showVersion();', 'reportState();')

io.open(C, 'w', encoding='utf-8').write(s)
t = io.open(C, encoding='utf-8').read()
ok = (t.count('function reportState()') == 1 and t.count('reportState();') >= 3
      and 'statusLine' not in t and 'showVersion' not in t)
print('  reportState defined once:', t.count('function reportState()') == 1)
print('  call sites:', t.count('reportState();'))
print('  old names gone:', 'statusLine' not in t and 'showVersion' not in t)
print('  version source still present (window.__abdoPushVersion):', '__abdoPushVersion' in t)
sys.exit(0 if ok else '  SHAPE WRONG - not committing')
