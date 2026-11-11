"""Loopback-only pilot HTTP adapter; not an internet-facing production server."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from sreboard.store import Store, Problem

STATIC = Path(__file__).resolve().parent.parent / 'static'


def make_server(db_path, webhook_token, operator_token, port=0):
    if min(len(webhook_token), len(operator_token)) < 16 or webhook_token == operator_token:
        raise ValueError('Use distinct webhook/operator tokens of at least 16 characters')
    store = Store(db_path)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_):
            pass  # Never log bearer tokens, webhook bodies, or internal alert titles.

        def reply(self, status, value, content_type='application/json; charset=utf-8'):
            body = json.dumps(value, ensure_ascii=True).encode() if isinstance(value, dict) else value
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; object-src 'none'; "
                             "base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def authorized(self, token):
            supplied = self.headers.get('Authorization', '')
            if not hmac.compare_digest(supplied.encode(), ('Bearer ' + token).encode()):
                raise Problem(401, 'Missing or invalid bearer token')

        def body(self):
            if self.headers.get('Transfer-Encoding'):
                raise Problem(400, 'Transfer-Encoding is unsupported')
            try:
                size = int(self.headers.get('Content-Length', ''))
            except ValueError:
                raise Problem(400, 'Content-Length required')
            if size < 0 or size > 16384:
                raise Problem(413, 'Body exceeds 16 KiB')
            if self.headers.get_content_type() != 'application/json':
                raise Problem(415, 'Use application/json')
            def pairs(items):
                result = {}
                for key, val in items:
                    if key in result:
                        raise ValueError('Duplicate JSON field')
                    result[key] = val
                return result
            def constant(_):
                raise ValueError('Non-finite JSON number')
            try:
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError('Incomplete body')
                return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
            except (ValueError, UnicodeError):
                raise Problem(400, 'Malformed JSON')

        def dispatch(self):
            path = urlsplit(self.path).path
            if self.command == 'GET' and path == '/health':
                return self.reply(200, {'status': 'ok', 'scope': 'local-pilot'})
            files = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if self.command == 'GET' and path in files:
                filename, mime = files[path]
                file = STATIC / filename
                if not file.is_file():
                    raise Problem(404, 'UI not installed yet')
                return self.reply(200, file.read_bytes(), mime)
            if self.command == 'POST' and path == '/api/webhook':
                self.authorized(webhook_token)
                alert, duplicate = store.create(self.body())
                return self.reply(200 if duplicate else 201, {'alert': alert, 'duplicate': duplicate})
            if path.startswith('/api/'):
                self.authorized(operator_token)
                if self.command == 'GET' and path == '/api/alerts':
                    return self.reply(200, store.active())
                parts = path.strip('/').split('/')
                if len(parts) == 3 and parts[:2] == ['api', 'alerts'] and self.command == 'GET':
                    return self.reply(200, store.detail(parts[2]))
                if len(parts) == 4 and parts[:2] == ['api', 'alerts'] and parts[3] == 'state' and self.command == 'POST':
                    return self.reply(200, {'alert': store.transition(parts[2], self.body())})
            raise Problem(404, 'Route not found')

        def handle_request(self):
            try:
                self.dispatch()
            except Problem as exc:
                self.reply(exc.status, {'error': exc.message})
            except Exception:
                self.reply(500, {'error': 'Internal error; inspect server locally'})

        do_GET = do_POST = handle_request

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    server = make_server(os.environ.get('SREB_DB', 'sreboard.sqlite'),
                         os.environ.get('SREB_WEBHOOK_TOKEN', ''),
                         os.environ.get('SREB_OPERATOR_TOKEN', ''),
                         int(os.environ.get('SREB_PORT', '8765')))
    print(f'SRE Board local pilot: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
