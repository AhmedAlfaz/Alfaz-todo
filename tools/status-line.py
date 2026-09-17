import io, re, sys

C = '/home/user/Alfaz-todo/push/client.js'
s = io.open(C, encoding='utf-8').read()

# A single status line in the sidebar, showing the real state of the whole push chain.
# Deliberate: every previous round of this was me guessing what a user's device was doing
# from outside. The device knows. Say what it knows.
add = """  // One honest line in the sidebar: what this device actually did, not what we assume it did.
  function statusLine() {
    try {
      var el = document.getElementById('app-version-num');
      if (!el) return;
      var v = el.textContent || '';
      var state = ls(STATE_KEY);
      var label = state === 'on' ? 'alerts on' : (state === 'off' ? 'alerts off' : 'not asked yet');
      var extra = '';
      try {
        if (window.OneSignal && window.OneSignal.User) {
          var sub = window.OneSignal.User.pushSubscription.get ? window.OneSignal.User.pushSubscription.get() : null;
          extra = sub && sub.id ? ' · id ok' : ' · no id';
        } else if (cfg) { extra = ' · sdk pending'; }
        else { extra = ' · push off here'; }
      } catch (e) { extra = ' · id pending'; }
      var perm = ('Notification' in window) ? Notification.permission : 'unsupported';
      el.textContent = v + '  ·  ' + label + extra + '  ·  ' + perm;
      el.parentNode.title = 'uid ' + pushUid();
    } catch (e) {}
  }

"""
anchor = '  // ---- boot ----'
assert s.count(anchor) == 1, 'anchor'
s = s.replace(anchor, add + anchor)

# call it wherever state can change
s = s.replace("        setState('on');", "        setState('on'); try { statusLine(); } catch (e) {}")
s = s.replace("  window.abdoPushNever = function () {\n    closeAsk();\n    setState('off');",
              "  window.abdoPushNever = function () {\n    closeAsk();\n    setState('off'); try { statusLine(); } catch (e) {}")
s = s.replace("    loadSiteConfig(function (j) {\n      setupShare();",
              "    loadSiteConfig(function (j) {\n      setupShare();\n      try { statusLine(); } catch (e) {}")
s = s.replace("  function start() {\n    setupShare();", "  function start() {\n    setupShare();\n    try { statusLine(); } catch (e) {}")
io.open(C, 'w', encoding='utf-8').write(s)

t = io.open(C, encoding='utf-8').read()
stripped = re.sub(r"'(?:\\.|[^'])*'", "''", t)
stripped = re.sub(r'"(?:\\.|[^"])*"', '""', stripped)
stripped = re.sub(r'/\*.*?\*/', '', stripped, flags=re.S)
stripped = re.sub(r'//.*', '', stripped)
print('  braces', stripped.count('{') - stripped.count('}'), 'parens', stripped.count('(') - stripped.count(')'))
print('  statusLine defined:', 'function statusLine()' in t, '| calls:', t.count('statusLine();'))
