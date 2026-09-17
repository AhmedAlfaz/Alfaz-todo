import io, re, sys, glob

# 1) one small, correct behaviour in cron: a queue file with no events is dead weight
#    (it is what an opt-out leaves behind) and it inflates any device count. Delete it.
K = '/home/user/Alfaz-todo/push/push-cron.php'
k = io.open(K, encoding='utf-8').read()
old = "    if ($keep === []) { @unlink($file); continue; }"
new = """    if ($keep === []) { @unlink($file); continue; }
    if ($keep !== [] && !$has_future) { @unlink($file); continue; }   // nothing left to send"""
assert k.count(old) == 1, 'cron unlink anchor'
k = k.replace(old, new)

old2 = "    $changed = false; $keep = [];"
new2 = "    $changed = false; $keep = []; $has_future = false;"
assert k.count(old2) == 1, 'cron init anchor'
k = k.replace(old2, new2)

old3 = "        if (!$due) { $keep[] = $e; continue; }"
new3 = "        if (!$due) { $keep[] = $e; $has_future = true; continue; }"
assert k.count(old3) == 1, 'cron due anchor'
k = k.replace(old3, new3)
io.open(K, 'w', encoding='utf-8').write(k)
print('  cron: prunes a device file once its schedule is empty')

# 2) drop the debug page from the repo and from the site; delete the one-off tooling too
for f in ['/home/user/Alfaz-todo/push-check.php',
          '/home/user/Alfaz-todo/tools/find-devices.py',
          '/home/user/Alfaz-todo/tools/fix-cron.py',
          '/home/user/Alfaz-todo/tools/fix-noop.py',
          '/home/user/Alfaz-todo/tools/fix-payload.py',
          '/home/user/Alfaz-todo/tools/add-version.py',
          '/home/user/Alfaz-todo/tools/patch_v40.py',
          '/home/user/Alfaz-todo/tools/patch_v41.py']:
    try:
        import os; os.remove(f); print('  removed', f.split('/')[-1])
    except FileNotFoundError:
        pass

# push-sync shim: keep the endpoint, but stop pointing at a check page that no longer exists
S = '/home/user/Alfaz-todo/push/push-config.example.php'
s = io.open(S, encoding='utf-8').read()
s = s.replace('// push-check.php says so and the fallback below keeps the sender working inside push/.',
              '// the cron run reports it, and the fallback below keeps the sender working.')
s = s.replace('(or, if that path is unknown: wget -q -O - "https://YOUR-DOMAIN/abdo-cron.php")',
              '(or: wget -q -O - "https://YOUR-DOMAIN/abdo-cron.php?key=YOUR_KEY")')
io.open(S, 'w', encoding='utf-8').write(s)

for f in ['/home/user/Alfaz-todo/push/push-cron.php', '/home/user/Alfaz-todo/push/push-config.example.php']:
    t = io.open(f, encoding='utf-8').read()
    tt = re.sub(r"'(?:\\.|[^'])*'", "''", t)
    tt = re.sub(r'"(?:\\.|[^"])*"', '""', tt)
    tt = re.sub(r'/\*.*?\*/', '', tt, flags=re.S)
    tt = re.sub(r'//[^\n]*', '', tt)
    bal = (tt.count('{') - tt.count('}'), tt.count('(') - tt.count(')'), tt.count('[') - tt.count(']'))
    stray = t.count('*/') != len(re.findall(r'/\*[\s\S]*?\*/', t))
    names = re.findall(r'^\s*function ([a-z_]+)\(', t, re.M)
    dupes = [n for n in set(names) if names.count(n) > 1]
    print('  check', f.split('/')[-1], 'braces/parens/brackets', bal, 'stray-comment-close', stray, 'dupes', dupes)
    if any(bal) or stray or dupes:
        sys.exit('  REFUSING TO COMMIT ' + f)
print('  all static checks pass')
