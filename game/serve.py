#!/usr/bin/env python3
"""Local-only standalone game server; explicit static/data allowlist.

Start with `python3 -I -S -B game/serve.py`. No dependency installation needed.
The optional audit records actual file opens, imports and HTTP requests.
"""
from pathlib import Path
import argparse
import json
import signal
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'game'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8878)
    parser.add_argument('--audit-log', type=Path)
    args = parser.parse_args()
    audit = {'file_opens': [], 'imports': [], 'requests': [], 'denied_access': []}

    def audit_hook(event, values):
        if event == 'open':
            path = str(values[0])
            if any(part in Path(path).parts for part in ('.toolchain', '.venv-trace', 'analysis')) or Path(path).suffix.lower() in {'.nes', '.state'}:
                audit['denied_access'].append(path)
                raise PermissionError('Forbidden original runtime input: ' + path)
            if len(audit['file_opens']) < 50000:
                audit['file_opens'].append({'path': path, 'mode': str(values[1])})
        elif event == 'import':
            name = str(values[0])
            if name == 'py65' or name.startswith(('py65.', 'recovered.')):
                audit['denied_access'].append(name)
                raise ImportError('Forbidden runtime module: ' + name)
            audit['imports'].append(name)
    if args.audit_log:
        sys.addaudithook(audit_hook)
    sys.path.insert(0, str(ROOT / 'source'))
    from remake.campaign import GameError
    from remake.session import CampaignSession
    era_index = json.loads((HERE / 'data/eras/index.json').read_text())
    current_index = json.loads((HERE / 'data/eras-v3/index.json').read_text())
    main_index = json.loads((HERE / 'data/main-scenarios/index.json').read_text())
    game = CampaignSession([HERE / 'data/demo.json', HERE / 'data/mainland.json'] +
                           [HERE / 'data' / name for name in era_index['catalogs'] + current_index['catalogs'] + main_index['catalogs']])
    static = {'/': ('index.html', 'text/html; charset=utf-8'),
              '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
              '/style.css': ('style.css', 'text/css; charset=utf-8'),
              '/assets/map.png': ('assets/map.png', 'image/png'),
              '/assets/city-positions.json': ('assets/city-positions.json', 'application/json; charset=utf-8'),
              '/assets/unifont.woff': ('assets/unifont.woff', 'font/woff')}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass

        def send(self, status, data, mime='application/json; charset=utf-8'):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)
            audit['requests'].append({'method': self.command, 'path': self.path, 'status': status, 'bytes': len(data)})

        def do_GET(self):
            try:
                if self.path == '/api/state':
                    return self.send(200, game.view())
                if self.path == '/api/save':
                    return self.send(200, game.export_save())
                if self.path == '/favicon.ico':
                    return self.send(204, b'', 'image/x-icon')
                if self.path in static:
                    name, mime = static[self.path]
                    return self.send(200, (HERE / name).read_bytes(), mime)
                self.send(404, {'error': '未找到这个页面。'})
            except GameError as exc:
                self.send(exc.status, {'error': str(exc)})

        def do_POST(self):
            try:
                origin = self.headers.get('Origin')
                port = self.server.server_address[1]
                if origin and origin not in {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}:
                    return self.send(403, {'error': '请在本地游戏页面操作。'})
                if self.headers.get_content_type() != 'application/json':
                    return self.send(400, {'error': '操作数据格式无效。'})
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2 * 1024 * 1024:
                    return self.send(400, {'error': '存档或操作数据大小无效。'})
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError('payload')
                if self.path == '/api/command':
                    view = game.command(payload.get('kind'), payload.get('payload', {}), payload.get('revision'))
                elif self.path == '/api/load':
                    view = game.load_save(payload.get('save'), payload.get('revision'))
                else:
                    return self.send(404, {'error': '未找到这个操作。'})
                self.send(200, view)
            except GameError as exc:
                self.send(exc.status, {'error': str(exc)})
            except (ValueError, TypeError, KeyError) as exc:
                self.send(400, {'error': '输入或存档不符合当前规则，进度未改变。'})
            except Exception:
                traceback.print_exc()
                self.send(500, {'error': '操作未完成，当前进度未改变。'})

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    print(f'本地试玩：http://127.0.0.1:{server.server_address[1]}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if args.audit_log:
            audit['loaded_modules'] = {name: getattr(module, '__file__', None)
                                       for name, module in sorted(sys.modules.items())}
            audit['game_journal'] = game.journal
            audit['final_revision'] = game.revision
            audit['final_state'] = game.to_dict()
            args.audit_log.parent.mkdir(parents=True, exist_ok=True)
            args.audit_log.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
