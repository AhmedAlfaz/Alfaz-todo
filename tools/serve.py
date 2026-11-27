#!/usr/bin/env python3
"""Local preview server for the ABDO PWA.

    python3 tools/serve.py [port]        # default 8099

Why this exists instead of `python3 -m http.server`:

1. **Range requests.** The azan and reader audio are 2–6 MB MP3s and the player seeks with
   `currentTime`. `http.server` ignores `Range`, so a seek restarts the download and, on a slow
   link, playback may not start at all.
2. **No stale shell.** `http.server` lets the browser cache `index.html` and `sw.js` freely. For an
   app whose whole update story is "bump the version, the service worker replaces the shell", a
   cached shell makes every change invisible — including the change you are trying to check.

It binds 0.0.0.0 so a proxied preview can reach it, and sends no `X-Frame-Options`, so the app can
be embedded in the preview iframe. `.htaccess` is Apache-only and does not apply here; this server
serves the repo as-is, which also means `/tools`, `/2` and `.git` are readable on this port. That is
acceptable for a localhost preview and is *not* what the public host does.

Nothing secret is served from here: `push/push-config.php` is gitignored and absent, and the
gitignored `tools/handoff/push-config.php` is only present if someone generated it locally.
"""
import mimetypes
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RANGE = re.compile(r'^bytes=(\d*)-(\d*)$')
# Never stream these over a port that a proxy might expose, even by accident.
DENY = ('/.git/', '/push/push-config.php', '/tools/handoff/push-config.php')


class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=REPO, **kwargs)

    def end_headers(self):
        path = self.path.split('?')[0]
        if path.endswith(('.html', '.js', '.json', '.webmanifest')) or path in ('', '/'):
            self.send_header('Cache-Control', 'no-cache, must-revalidate')
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def _denied(self):
        return any(d in self.path for d in DENY)

    def do_GET(self):
        if self._denied():
            self.send_error(403)
            return
        rng = self.headers.get('Range')
        target = self.translate_path(self.path)
        if rng and os.path.isfile(target):
            m = RANGE.match(rng.strip())
            if m:
                size = os.path.getsize(target)
                first, last = m.group(1), m.group(2)
                if first == '':                       # suffix range: the last N bytes
                    start = max(0, size - int(last or 0))
                    end = size - 1
                else:
                    start = int(first)
                    end = min(int(last) if last else size - 1, size - 1)
                if start <= end:
                    ctype = mimetypes.guess_type(target)[0] or 'application/octet-stream'
                    self.send_response(206)
                    self.send_header('Content-Type', ctype)
                    self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                    self.send_header('Content-Length', str(end - start + 1))
                    self.end_headers()
                    with open(target, 'rb') as f:
                        f.seek(start)
                        self.wfile.write(f.read(end - start + 1))
                    return
        super().do_GET()

    def do_HEAD(self):
        if self._denied():
            self.send_error(403)
            return
        super().do_HEAD()

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    server.daemon_threads = True
    print(f'ABDO preview: http://0.0.0.0:{port}/  (root: {REPO})', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
