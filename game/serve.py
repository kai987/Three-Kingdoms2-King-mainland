#!/usr/bin/env python3
"""Local-only standalone game server; explicit static/data allowlist.

Start with `python3 -I -S -B game/serve.py`. No dependency installation needed.
The optional audit records actual file opens, imports and HTTP requests.
"""
from pathlib import Path
import argparse
import json
import re
import signal
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'game'
ORIGINAL_EFFECT_CUES = ('5a', '5d', '5e', '60', '61', '62', '65', '68', '69', '88', '8d', '91', '95')


def audio_effect_static_assets():
    """Only explicitly shipped short original cues are public, not a directory."""
    return {f'/assets/audio/original/effects/seq-{cue}.wav':
            (f'assets/audio/original/effects/seq-{cue}.wav', 'audio/wav')
            for cue in ORIGINAL_EFFECT_CUES}


class GameHTTPServer(ThreadingHTTPServer):
    # Browsers open the deferred scripts/fonts/images concurrently. Python's
    # default backlog5 can reset those sockets while a catalog response is busy.
    request_queue_size = 128


def portrait_static_assets(here=HERE):
    """Register exact presentation URLs, never a browsable asset directory.

    The deployed index fixes the PNG allowlist for this server process. A missing
    or malformed index leaves the frontend's explicit missing-portrait fallback.
    Neither build evidence nor original ROM inputs are exposed.
    """
    static = {'/portraits.js': ('portraits.js', 'text/javascript; charset=utf-8'),
              '/portraits.css': ('portraits.css', 'text/css; charset=utf-8'),
              '/assets/portraits/index.json': ('assets/portraits/index.json', 'application/json; charset=utf-8')}
    root = Path(here).resolve()
    base = root / 'assets/portraits'
    index = base / 'index.json'
    if (root / 'assets').is_symlink() or base.is_symlink() or index.is_symlink():
        return static
    try:
        data = json.loads(index.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return static
    people = data.get('people') if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get('schema') != 'tk2-portraits-v1' or not isinstance(people, dict):
        return static
    for row in people.values():
        path = row.get('path') if isinstance(row, dict) else None
        if not isinstance(path, str) or not re.fullmatch(r'/assets/portraits/(original|generated)/[A-Za-z0-9_-]+\.png', path):
            continue
        target = root / path.lstrip('/')
        if target.parent.is_symlink() or target.is_symlink():
            continue
        static[path] = (path.lstrip('/'), 'image/png')
    return static


def static_file_bytes(here, name):
    """Keep even a replaced symlink inside the explicitly served game tree."""
    root = Path(here).resolve()
    target = root / name
    try:
        target.resolve().relative_to(root)
    except ValueError:
        raise FileNotFoundError(name) from None
    if name.startswith('assets/portraits/') and (target.is_symlink() or target.parent.is_symlink() or
                                                 (root / 'assets/portraits').is_symlink() or
                                                 (root / 'assets').is_symlink()):
        raise FileNotFoundError(name)
    return target.read_bytes()


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
    from remake.march_core import backend_status, config_for
    from remake.cloud_config import public_config, content_security_policy
    cloud_config = public_config(HERE / 'config/cloud-save-public.json')
    cloud_csp = content_security_policy(cloud_config)
    current_index = json.loads((HERE / 'data/campaigns/index.json').read_text())
    game = CampaignSession([HERE / 'data' / name for name in current_index['catalogs']])
    static = {'/': ('index.html', 'text/html; charset=utf-8'),
              '/save-transfer.js': ('save-transfer.js', 'text/javascript; charset=utf-8'),
              '/cloud-save.js': ('cloud-save.js', 'text/javascript; charset=utf-8'),
              '/cloud-save-ui.js': ('cloud-save-ui.js', 'text/javascript; charset=utf-8'),
              '/cloud-save.css': ('cloud-save.css', 'text/css; charset=utf-8'),
              '/vendor/supabase.min.js': ('vendor/supabase.min.js', 'text/javascript; charset=utf-8'),
              '/vendor/supabase-LICENSES.txt': ('vendor/supabase-LICENSES.txt', 'text/plain; charset=utf-8'),
              '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
              '/i18n.js': ('i18n.js', 'text/javascript; charset=utf-8'),
              '/calendar.js': ('calendar.js', 'text/javascript; charset=utf-8'),
              '/audio.js': ('audio.js', 'text/javascript; charset=utf-8'),
              '/officer-choice.js': ('officer-choice.js', 'text/javascript; charset=utf-8'),
              '/assets/audio/index.json': ('assets/audio/index.json', 'application/json; charset=utf-8'),
              '/assets/audio/effects.json': ('assets/audio/effects.json', 'application/json; charset=utf-8'),
              '/assets/audio/original/title.mp3': ('assets/audio/original/title.mp3', 'audio/mpeg'),
              '/assets/audio/original/strategy.mp3': ('assets/audio/original/strategy.mp3', 'audio/mpeg'),
              '/assets/audio/original/battle.mp3': ('assets/audio/original/battle.mp3', 'audio/mpeg'),
              '/assets/audio/original/duel.mp3': ('assets/audio/original/duel.mp3', 'audio/mpeg'),
              '/march-core.js': ('march-core.js', 'text/javascript; charset=utf-8'),
              '/march-worker.js': ('march-worker.js', 'text/javascript; charset=utf-8'),
              '/wasm/march_core.wasm': ('wasm/march_core.wasm', 'application/wasm'),
              '/wasm/THIRD-PARTY-LICENSES.txt': ('wasm/THIRD-PARTY-LICENSES.txt', 'text/plain; charset=utf-8'),
              '/wasm/manifest.json': ('wasm/manifest.json', 'application/json; charset=utf-8'),
              '/map-navigation.js': ('map-navigation.js', 'text/javascript; charset=utf-8'),
              '/locales/zh-hant.json': ('locales/zh-hant.json', 'application/json; charset=utf-8'),
              '/locales/ui-ja.json': ('locales/ui-ja.json', 'application/json; charset=utf-8'),
              '/locales/messages-ja.json': ('locales/messages-ja.json', 'application/json; charset=utf-8'),
              '/locales/opencc/LICENSE': ('locales/opencc/LICENSE', 'text/plain; charset=utf-8'),
              '/style.css': ('style.css', 'text/css; charset=utf-8'),
              '/assets/map.png': ('assets/map.png', 'image/png'),
              '/assets/map-clean.png': ('assets/map-clean.png', 'image/png'),
              '/assets/map-basin.png': ('assets/map-basin.png', 'image/png'),
              '/assets/map-campaign.png': ('assets/map-campaign.png', 'image/png'),
              '/assets/map-navigation.png': ('assets/map-navigation.png', 'image/png'),
              '/assets/city-positions.json': ('assets/city-positions.json', 'application/json; charset=utf-8'),
              '/assets/unifont.woff': ('assets/unifont.woff', 'font/woff')}
    static.update(portrait_static_assets())
    static.update(audio_effect_static_assets())

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
            self.send_header('Content-Security-Policy', cloud_csp)
            self.end_headers()
            self.wfile.write(data)
            audit['requests'].append({'method': self.command, 'path': self.path, 'status': status, 'bytes': len(data)})

        def do_GET(self):
            try:
                if self.path == '/api/state':
                    return self.send(200, game.view())
                if self.path == '/api/cloud-config':
                    return self.send(200, cloud_config)
                if self.path == '/api/march-status':
                    return self.send(200, backend_status())
                if urlsplit(self.path).path == '/api/march-config':
                    try:
                        query = parse_qs(urlsplit(self.path).query, keep_blank_values=True, max_num_fields=1)
                    except ValueError:
                        raise GameError('行军查询参数无效。')
                    if set(query) != {'scenario'} or len(query['scenario']) != 1:
                        raise GameError('行军查询参数无效。')
                    catalog = game.catalogs.get(query['scenario'][0])
                    if catalog is None:
                        raise GameError('未找到这个剧本。')
                    return self.send(200, config_for(catalog.data))
                if self.path == '/api/save':
                    return self.send(200, game.export_save())
                if urlsplit(self.path).path == '/api/city-preview':
                    try:
                        query=parse_qs(urlsplit(self.path).query,keep_blank_values=True,max_num_fields=2)
                    except ValueError:
                        raise GameError('城池查询参数无效。')
                    if set(query)!={'scenario','city'} or any(len(v)!=1 for v in query.values()):
                        raise GameError('城池查询参数无效。')
                    return self.send(200,game.preview_city(query['scenario'][0],query['city'][0]))
                if self.path == '/favicon.ico':
                    return self.send(204, b'', 'image/x-icon')
                if self.path in static:
                    name, mime = static[self.path]
                    try:
                        return self.send(200, static_file_bytes(HERE, name), mime)
                    except OSError:
                        return self.send(404, {'error': '未找到这个资源。'})
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

    server = GameHTTPServer(('127.0.0.1', args.port), Handler)
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
