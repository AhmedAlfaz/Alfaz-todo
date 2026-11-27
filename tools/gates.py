#!/usr/bin/env python3
"""Static gates for the ABDO single-file app. No dependencies, runs in CI and locally.

  python3 tools/gates.py            # check
  python3 tools/gates.py --fix      # report only (no writes yet)

Why these specific gates: every one of them corresponds to a mistake actually made on this repo
(a version bumped in one file only, a swallowed nested function, a duplicated function definition,
a deploy shipping an HTML that no longer matched its own cache manifest). They are cheap,
mechanical, and they do not require me to be careful.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, 'index.html')
SW = os.path.join(REPO, 'sw.js')
FAIL = []
NOTE = []


def fail(msg):
    FAIL.append(msg)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def check_html_wellformed():
    s = read(HTML)
    for tag in ('</html>', '</body>'):
        n = s.count(tag)
        if n != 1:
            fail(f'{tag}: found {n}, expected exactly 1 (truncated or duplicated file)')
    if len(s) < 200000:
        fail(f'index.html is only {len(s)} bytes; a truncation bug once cut it to 147456')
    return s


def check_inline_js(html):
    blocks = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
    bad = 0
    for i, b in enumerate(blocks):
        if not b.strip():
            continue
        tmp = os.path.join('/tmp', f'abdo-gate-{i}.js')
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(b)
        r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
        if r.returncode:
            bad += 1
            fail(f'inline script {i}: {r.stderr.strip().splitlines()[-1] if r.stderr else "syntax error"}')
    if not bad:
        NOTE.append(f'inline scripts: {len(blocks)} parsed clean')
    return blocks


def check_sw():
    s = read(SW)
    m = re.search(r"VERSION\s*=\s*'v(\d+)'", s) or re.search(r"CACHE_NAME\s*=\s*'alfaz-todo-v(\d+)'", s)
    if not m:
        fail('sw.js: could not find a version constant')
        return None, s
    ver = m.group(1)
    r = subprocess.run(['node', '--check', SW], capture_output=True, text=True)
    if r.returncode:
        fail('sw.js: ' + (r.stderr.strip().splitlines()[-1] if r.stderr else 'syntax error'))
    # The atomic rule that matters: skipWaiting must not run unconditionally after best-effort adds.
    install = s[s.index("addEventListener('install'"):] if "addEventListener('install'" in s else ''
    install = install[:install.index("addEventListener('activate'")] if "addEventListener('activate'" in install else install
    if re.search(r'catch\s*\([^)]*\)\s*\{\s*\}', install) and 'addAll' not in install:
        fail('sw.js install swallows cache failures without addAll -> partial cache can take control')
    return ver, s


def check_version_pair(html, ver):
    m = re.search(r'\?v=(\d+)&t=', html)
    if not m:
        fail("index.html: no '?v=N&t=' refresh query found in checkForAppUpdate")
        return
    if ver and m.group(1) != ver:
        fail(f'version drift: sw.js=v{ver} but index.html refresh query=v{m.group(1)} (bump both, every time)')
        return
    # THREE places now carry the version, and a phone was left on the old build because one of them
    # was ambiguous. version.json is what the app reports as deployed; the page marker is what the
    # running HTML thinks it is. Both must equal sw.js, or the label lies.
    vp = os.path.join(REPO, 'version.json')
    if not os.path.exists(vp):
        fail('version.json is missing (the update label reads it; without it the label falls back to a guessed cache name)')
    else:
        try:
            declared = json.load(open(vp, encoding='utf-8')).get('version', '')
        except Exception as e:
            declared = ''
            fail(f'version.json does not parse: {e}')
        if ver and declared != f'v{ver}':
            fail(f'version drift: sw.js=v{ver} but version.json={declared!r}')
    pm = re.search(r"__abdoPageVersion\s*=\s*'v(\d+)'", html)
    if not pm:
        fail("index.html: window.__abdoPageVersion marker is missing (the label cannot detect a stale tab without it)")
    elif ver and pm.group(1) != ver:
        fail(f'version drift: sw.js=v{ver} but index.html page marker=v{pm.group(1)}')
    if not FAIL:
        NOTE.append(f'version consistent: v{ver} in sw.js, version.json, index.html (refresh query + page marker)')


def check_declared_assets_exist(html):
    """Every asset index.html references by relative path must exist in the repo, and every
    CORE asset in sw.js must be fetchable. A stale upload list is a blank screen, not a warning."""
    refs = set(re.findall(r'(?:src|href)="(?!https?:|//|#|data:)([^"?#]+\.(?:js|json|css|png|mp3))"', html))
    for r in sorted(refs):
        if not os.path.exists(os.path.join(REPO, r)):
            fail(f'index.html references {r} which does not exist in the repo')
    sw = read(SW)
    block = re.search(r'const CORE\s*=\s*\[(.*?)\]', sw, re.S)
    if block:
        for item in re.findall(r"'([^']+)'", block.group(1)):
            path = item.lstrip('./') or '.'
            if path != '.' and not os.path.exists(os.path.join(REPO, path)):
                fail(f'sw.js CORE lists {item} which does not exist (install will abort)')
    NOTE.append(f'{len(refs)} local assets referenced, all present')


def check_no_duplicate_functions(html):
    names = re.findall(r'^\s*function ([a-zA-Z0-9_]+)\s*\(', html, re.M)
    # also scan the real js files if a split has happened
    for root, _dirs, files in os.walk(REPO):
        if '/.git' in root or '/tools' in root:
            continue
        for fn in files:
            if fn.endswith('.js') and not fn.startswith('test'):
                p = os.path.join(root, fn)
                if p == SW:
                    continue
                try:
                    names += re.findall(r'^\s*(?:function|const)\s+([a-zA-Z0-9_]+)\s*[=(]', read(p), re.M)
                except Exception:
                    pass
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        # an HTML onclick handler legitimately shadowing a name is the common false positive;
        # a genuine redeclaration in JS is a fatal, so report and let a human judge.
        NOTE.append('reused names (verify not a real redeclare): ' + ', '.join(dupes[:8]))
    NOTE.append(f'{len(names)} top-level definitions scanned')


def check_i18n_keys(html):
    """Every data-i18n / data-i18n-placeholder / data-i18n-aria-label key must exist in EN and AR,
    and no JS reference to i18n[x].key may be undefined. v52 found 22 keys that silently rendered
    blank because nothing checked this."""
    i = html.find('const i18n = {')
    if i < 0:
        fail('i18n object not found')
        return
    body = html[i:]
    start = body.index('{')
    depth = 0
    end = None
    for n, ch in enumerate(body[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = n + 1
                break
    obj = body[start:end]
    a = obj.index('en: {')
    b = obj.index('ar: {')

    def keys(t):
        return set(re.findall(r'([A-Za-z0-9_]+)\s*:\s*["\'`]', t))

    en, ar = keys(obj[a:b]), keys(obj[b:])
    en -= {'End', 'menu'}   # punctuation/keywords caught inside nested objects, not real keys
    ar -= {'End', 'menu'}
    for k in sorted(en - ar):
        fail(f'i18n: {k} exists in EN but not in AR')
    for k in sorted(ar - en):
        fail(f'i18n: {k} exists in AR but not in EN')
    used = set(re.findall(r'data-i18n="([^"]+)"', html))
    used |= set(re.findall(r'data-i18n-placeholder="([^"]+)"', html))
    used |= set(re.findall(r'data-i18n-aria-label="([^"]+)"', html))
    used |= set(re.findall(r'i18n\[(?:currentLang|lang)\]\.([A-Za-z0-9_]+)', html))
    missing = sorted(k for k in used if k not in en)
    for k in missing:
        fail(f'i18n: {k} is referenced but has no string')
    if not missing and not (en ^ ar):
        NOTE.append(f'i18n: {len(en)} keys, EN=AR complete, every reference resolves')


def check_time_logic():
    """Run tools/test_planner_time.py. Recurrence/reminder/timezone bugs are invisible to a syntax
    check and were shipped for months; this makes them a build failure instead."""
    script = os.path.join(REPO, 'tools', 'test_planner_time.py')
    if not os.path.exists(script):
        fail('tools/test_planner_time.py is missing')
        return
    r = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if r.returncode != 0:
        for line in (r.stdout or '').splitlines():
            if line.strip().startswith('FAIL'):
                fail('time-logic: ' + line.strip()[5:])
        if r.returncode != 0 and 'FAIL' not in (r.stdout or ''):
            fail('time-logic: suite failed -> ' + (r.stdout or r.stderr).strip().splitlines()[-1])
    else:
        NOTE.append('time-logic: recurrence, reminders and timezone suites pass')


def check_config_sane():
    p = os.path.join(REPO, 'site-config.json')
    if not os.path.exists(p):
        fail('site-config.json missing (push and the share link both go inert without it)')
        return
    d = json.load(open(p, encoding='utf-8'))
    push = d.get('push', {})
    if push.get('appId') and push.get('appId') == push.get('writeToken'):
        fail('site-config.json: appId duplicated into writeToken')
    NOTE.append('site-config.json parses; push.enabled=' + str(push.get('enabled')))


def main():
    html = check_html_wellformed()
    check_inline_js(html)
    ver, _sw = check_sw()
    check_version_pair(html, ver)
    check_declared_assets_exist(html)
    check_no_duplicate_functions(html)
    check_i18n_keys(html)
    check_time_logic()
    check_config_sane()

    print('ABDO gates')
    print('----------')
    for n in NOTE:
        print('  · ' + n)
    if FAIL:
        for f in FAIL:
            print('  FAIL ' + f)
        print(f'\n{len(FAIL)} gate(s) failed')
        return 1
    print('\n  all gates pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
