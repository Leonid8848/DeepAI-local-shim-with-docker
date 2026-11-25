#!/usr/bin/env python3
"""OpenAI-compatible local shim for api2.deepai.org (single own key, SSE streaming, reasoning passthrough)."""
import json, os, sys, time, threading, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UP = 'https://api2.deepai.org'
KEY = os.environ.get('DEEPAI_API_KEY', '')
ROUTES = {'/v1/chat/completions': '/deepai_code/chat/completions'}
HDRS = {'Api-Key': KEY, 'X-Deepai-Code-Theos': '8', 'Content-Type': 'application/json'}
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deepai-shim.log')
LOCK = threading.Lock()


def log(msg):
    try:
        with LOCK, open(LOG, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (time.strftime('%H:%M:%S'), msg))
    except Exception:
        pass


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _reply(self, code, ctype, data):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _stream(self, r, tag, t0):
        self.send_response(r.status)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Transfer-Encoding', 'chunked')
        self.end_headers()
        first = None
        events = 0
        try:
            while True:
                line = r.readline()
                if not line:
                    break
                if line.startswith(b'data: '):
                    payload = line[6:].strip()
                    if payload and payload != b'[DONE]':
                        try:
                            j = json.loads(payload)
                            for ch in j.get('choices', []):
                                d = ch.get('delta') or {}
                                if isinstance(d.get('reasoning'), str) and 'reasoning_content' not in d:
                                    d['reasoning_content'] = d['reasoning']
                            line = b'data: ' + json.dumps(j, ensure_ascii=False).encode() + b'\n'
                            events += 1
                        except Exception:
                            pass
                if first is None:
                    first = time.time() - t0
                self.wfile.write(b'%x\r\n' % len(line) + line + b'\r\n')
                self.wfile.flush()
            self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        log('%s stream events=%d first=%.2fs total=%.2fs' % (tag, events, first or -1, time.time() - t0))

    def _proxy(self, path, body=None, method='GET', tag='req'):
        t0 = time.time()
        req = urllib.request.Request(UP + path, data=body, headers=HDRS, method=method)
        try:
            r = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            data = e.read()
            log('%s upstream=%d %s' % (tag, e.code, data[:120].decode('utf-8', 'replace').replace('\n', ' ')))
            return self._reply(e.code, e.headers.get('Content-Type', 'application/json'), data)
        ctype = r.headers.get('Content-Type', 'application/octet-stream')
        if not ctype.startswith('text/event-stream'):
            data = r.read()
            log('%s json %d bytes %s total=%.2fs' % (tag, len(data), ctype, time.time() - t0))
            return self._reply(r.status, ctype, data)
        self._stream(r, tag, t0)

    def do_GET(self):
        if self.path.rstrip('/') not in ('/v1/models', '/models'):
            return self._reply(404, 'application/json', b'{"error":"not found"}')
        req = urllib.request.Request(UP + '/deepai_code/models', headers=HDRS)
        try:
            raw = urllib.request.urlopen(req, timeout=60).read()
        except urllib.error.HTTPError as e:
            return self._reply(e.code, 'application/json', e.read())
        up = json.loads(raw)
        items = up.get('models') or up.get('data') or []
        data = [{'id': m.get('id'), 'object': 'model', 'owned_by': 'deepai'} for m in items if m.get('id')]
        log('models list -> %d' % len(data))
        self._reply(200, 'application/json', json.dumps({'object': 'list', 'data': data}).encode())

    def do_POST(self):
        path = ROUTES.get(self.path.split('?')[0])
        if not path:
            return self._reply(404, 'application/json', b'{"error":"not found"}')
        body = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        try:
            req = json.loads(body or b'{}')
        except Exception:
            req = {}
        tag = 'chat model=%s stream=%s accept=%s' % (req.get('model'), req.get('stream'), self.headers.get('Accept'))
        self._proxy(path, body=body, method='POST', tag=tag)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9100
    bind = os.environ.get('DEEPAI_SHIM_BIND', '127.0.0.1')
    print('shim on http://%s:%d/v1' % (bind, port), flush=True)
    ThreadingHTTPServer((bind, port), H).serve_forever()
