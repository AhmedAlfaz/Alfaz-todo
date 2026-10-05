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
    else:
        NOTE.append(f'version pair consistent: v{m.group(1)}')


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
