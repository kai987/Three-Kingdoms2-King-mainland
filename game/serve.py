#!/usr/bin/env python3
"""Local-only standalone game server; explicit static/data allowlist.

Start with `python3 -I -S -B game/serve.py`. No dependency installation needed.
The optional audit records actual file opens, imports and HTTP requests.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import re
import signal
import socket
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore, Lock
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'game'
ORIGINAL_EFFECT_CUES = ('5a', '5d', '5e', '60', '61', '62', '65', '68', '69', '88', '8d', '91', '95')
ORIGINAL_UI_IDS = ('facility-armory', 'facility-hospital', 'facility-market', 'facility-school',
                   'command-city', 'command-army', 'command-warehouse', 'command-town',
                   'equipment-weapon-category', 'equipment-armor-category',
                   'event-armory-interior', 'event-market-interior', 'event-sortie',
                   'event-decorative-frame')
MAX_BODY_BYTES = 2 * 1024 * 1024
AUDIT_LIMITS = {'file_opens': 5000, 'imports': 1024, 'requests': 4096, 'denied_access': 1024}


def document_entry_path(path):
    """Only the static root and bounded PKCE callback parameters are entry URLs."""
    try:
        url = urlsplit(path)
        if url.path != '/' or url.fragment:
            return False
        if not url.query:
            return True
        args = parse_qs(url.query, keep_blank_values=True, max_num_fields=2)
        return ('code' in args and set(args) <= {'code', 'sb_flow_id'}
                and len(args['code']) == 1 and re.fullmatch(r'[A-Za-z0-9_-]{8,512}', args['code'][0])
                and ('sb_flow_id' not in args or len(args['sb_flow_id']) == 1
                     and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', args['sb_flow_id'][0])))
    except ValueError:
        return False


def versioned_asset_path(path):
    """Resolve one bounded cache key; the static allowlist still gates the path."""
    try:
        url = urlsplit(path)
        if url.scheme or url.netloc or url.fragment or not url.path.startswith('/assets/'):
            return None
        args = parse_qs(url.query, keep_blank_values=True, max_num_fields=1)
        if (set(args) == {'v'} and len(args['v']) == 1
                and re.fullmatch(r'(?:[a-fA-F0-9]{64}|current-map-v[1-9][0-9]{0,3})', args['v'][0])):
            return url.path
    except ValueError:
        pass
    return None


class AuditLog:
    """Optional diagnostics have fixed storage bounds and retain dropped counts."""
    def __init__(self, limits=None):
        self.limits = dict(AUDIT_LIMITS if limits is None else limits)
        self.rows = {key: [] for key in self.limits}
        self.counts = dict.fromkeys(self.limits, 0)
        self.lock = Lock()

    def record(self, kind, value):
        with self.lock:
            self.counts[kind] += 1
            if len(self.rows[kind]) < self.limits[kind]:
                self.rows[kind].append(value)

    def snapshot(self):
        with self.lock:
            return {**{key: list(rows) for key, rows in self.rows.items()},
                    'counts': dict(self.counts), 'limits': dict(self.limits),
                    'truncated': {key: self.counts[key] - len(rows) for key, rows in self.rows.items()}}


def strict_json(raw):
    """Reject ambiguous or excessive JSON before any campaign operation runs."""
    # main() sets the source path; static-asset tools import this file without
    # booting the campaign, so keep the shared parser import lazy.
    from remake.json_boundary import DepthLimitError, loads
    try:
        return loads(raw)
    except DepthLimitError as exc:
        raise ValueError(str(exc)) from None


def accepts_gzip(headers):
    """Require an explicit gzip token; malformed/zero preferences fail closed."""
    qualities = []
    for value in headers.get_all('Accept-Encoding', []):
        for item in value.split(','):
            parts = [part.strip().lower() for part in item.split(';')]
            if parts[0] != 'gzip':
                continue
            if len(parts) == 1:
                qualities.append(1.0)
            elif len(parts) == 2 and re.fullmatch(r'q=(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)', parts[1]):
                qualities.append(float(parts[1][2:]))
            else:
                qualities.append(0.0)
    return bool(qualities) and min(qualities) > 0


def audio_effect_static_assets():
    """Only explicitly shipped short original cues are public, not a directory."""
    return {f'/assets/audio/original/effects/seq-{cue}.wav':
            (f'assets/audio/original/effects/seq-{cue}.wav', 'audio/wav')
            for cue in ORIGINAL_EFFECT_CUES}


def original_ui_static_assets():
    """Publish the small reviewed UI set, never source windows or emulator states."""
    result = {'/assets/original-ui/index.json':
              ('assets/original-ui/index.json', 'application/json; charset=utf-8')}
    for identity in ORIGINAL_UI_IDS:
        for name in (f'{identity}-4x.png', f'pixel-base/{identity}.png', f'source/{identity}.png'):
            path = 'assets/original-ui/' + name
            result['/' + path] = (path, 'image/png')
    return result


def equipment_icon_static_assets():
    """Only the fixed per-item remake icons are public; generation sources stay local."""
    result = {'/assets/equipment-icons/index.json':
              ('assets/equipment-icons/index.json', 'application/json; charset=utf-8')}
    for slot, count in (('weapon', 29), ('armor', 8)):
        for identity in range(count):
            path = f'assets/equipment-icons/{slot}-{identity}.png'
            result['/' + path] = (path, 'image/png')
    return result


def battle_static_assets(here=None):
    """Ship only manifest-listed PNGs, never the original ROM or emulator states."""
    here = Path(here) if here is not None else HERE
    base = here / 'assets/battle-original'
    result = {'/assets/battle-original/index.json':
              ('assets/battle-original/index.json', 'application/json; charset=utf-8')}
    if (here / 'assets').is_symlink() or base.is_symlink() or (base / 'index.json').is_symlink():
        return {}
    try:
        data = json.loads((base / 'index.json').read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema') != 'tk2-battle-original-v1':
            return result
        def visit(value):
            if isinstance(value, dict):
                path = value.get('path')
                if isinstance(path, str) and re.fullmatch(r'/assets/battle-original/[A-Za-z0-9_-]+\.png', path):
                    target = here / path.lstrip('/')
                    if not target.is_symlink() and target.is_file():
                        result[path] = (path.lstrip('/'), 'image/png')
                for row in value.values():
                    visit(row)
            elif isinstance(value, list):
                for row in value:
                    visit(row)
        visit(data)
    except (OSError, ValueError):
        pass
    return result


def battlefield_static_assets(here=None):
    """Only the thirty exported map PNGs and their metadata are public."""
    here = Path(here) if here is not None else HERE
    base = here / 'assets/battlefields'
    if (here / 'assets').is_symlink() or base.is_symlink() or (base / 'index.json').is_symlink():
        return {}
    result = {'/assets/battlefields/index.json': ('assets/battlefields/index.json', 'application/json; charset=utf-8')}
    try:
        data = json.loads((base / 'index.json').read_text(encoding='utf-8'))
        if data.get('schema') != 'tk2-original-battlefields-v1' or not isinstance(data.get('maps'), dict):
            return result
        for index in range(30):
            identity = f'original-{index:02d}'
            row = data['maps'].get(identity, {})
            path = f'/assets/battlefields/{identity}.png'
            target = here / path.lstrip('/')
            if row.get('id') == identity and row.get('path') == path and not target.is_symlink() and target.is_file():
                result[path] = (path.lstrip('/'), 'image/png')
    except (OSError, ValueError, AttributeError):
        pass
    return result


def enhanced_battle_static_assets(here=None):
    """Only the shipped4x battle manifest and its fixed PNG filenames are public."""
    here = Path(here) if here is not None else HERE
    base = here / 'assets/battle-enhanced'
    index = base / 'index.json'
    if (here / 'assets').is_symlink() or base.is_symlink() or index.is_symlink():
        return {}
    result = {'/assets/battle-enhanced/index.json':
              ('assets/battle-enhanced/index.json', 'application/json; charset=utf-8')}
    try:
        data = json.loads(index.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema') != 'tk2-battle-enhanced-v1' or data.get('scale') != 4:
            return result
        def visit(value):
            if isinstance(value, dict):
                path = value.get('path')
                if isinstance(path, str) and re.fullmatch(r'/assets/battle-enhanced/[A-Za-z0-9_-]+\.png', path):
                    target = here / path.lstrip('/')
                    if not target.is_symlink() and target.is_file():
                        result[path] = (path.lstrip('/'), 'image/png')
                for row in value.values():
                    visit(row)
            elif isinstance(value, list):
                for row in value:
                    visit(row)
        visit(data)
    except (OSError, ValueError):
        pass
    return result


class GameHTTPServer(ThreadingHTTPServer):
    # Browsers open the deferred scripts/fonts/images concurrently. Python's
    # default backlog5 can reset those sockets while a catalog response is busy.
    request_queue_size = 128
    daemon_threads = False

    def __init__(self, address, handler, *, max_workers=32, request_timeout=5):
        self.workers = BoundedSemaphore(max_workers)
        self.request_timeout = request_timeout
        self.connections = set()
        self.connections_lock = Lock()
        super().__init__(address, handler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(self.request_timeout)
        return connection, address

    def process_request(self, request, client_address):
        if not self.workers.acquire(blocking=False):
            # Admission never waits for a worker or a slow peer to read a reply.
            try:
                request.setblocking(False)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nConnection: close\r\n'
                                b'Content-Length: 0\r\nCache-Control: no-store\r\nRetry-After: 1\r\n\r\n')
            except OSError:
                pass
            self.shutdown_request(request)
            return
        with self.connections_lock:
            self.connections.add(request)
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self.connections_lock:
                self.connections.discard(request)
            self.workers.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self.connections_lock:
                self.connections.discard(request)
            self.workers.release()

    def server_close(self):
        # Wake idle header/body readers before ThreadingMixIn joins its workers.
        with self.connections_lock:
            connections = list(self.connections)
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        super().server_close()


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
    for person_id, row in people.items():
        path = row.get('path') if isinstance(row, dict) else None
        if not isinstance(path, str) or not re.fullmatch(r'/assets/portraits/(original|generated)/[A-Za-z0-9_-]+\.png', path):
            continue
        target = root / path.lstrip('/')
        if target.parent.is_symlink() or target.is_symlink():
            continue
        static[path] = (path.lstrip('/'), 'image/png')
        enhanced = row.get('enhanced')
        if (not isinstance(enhanced, dict) or enhanced.get('width') != 128 or enhanced.get('height') != 160 or
                re.fullmatch(r'[A-Za-z0-9_-]+', person_id) is None):
            continue
        enhanced_path = enhanced.get('path')
        if enhanced_path != f'/assets/portraits/enhanced/{person_id}.png':
            continue
        target = root / enhanced_path.lstrip('/')
        if target.parent.is_symlink() or target.is_symlink():
            continue
        static[enhanced_path] = (enhanced_path.lstrip('/'), 'image/png')
    return static


def civil_portrait_static_assets(here=HERE):
    """Only the three fixed, identity-bound civil portrait variants are public."""
    root = Path(here).resolve()
    base = root / 'assets/civil-staff'
    enhanced = base / 'enhanced'
    index = enhanced / 'index.json'
    if ((root / 'assets').is_symlink() or base.is_symlink() or
            enhanced.is_symlink() or index.is_symlink()):
        return {}
    static = {'/assets/civil-staff/enhanced/index.json':
              ('assets/civil-staff/enhanced/index.json', 'application/json; charset=utf-8')}
    try:
        data = json.loads(index.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return static
    if (not isinstance(data, dict) or data.get('schema') != 'tk2-civil-portraits-v1' or
            data.get('width') != 128 or data.get('height') != 160 or not isinstance(data.get('portraits'), dict)):
        return static
    for key in ('clerk-1', 'clerk-2', 'clerk-3'):
        row = data['portraits'].get(key)
        path = f'/assets/civil-staff/enhanced/{key}.png'
        if (not isinstance(row, dict) or row.get('path') != path or
                row.get('width') != 128 or row.get('height') != 160):
            continue
        target = root / path.lstrip('/')
        if not target.is_symlink() and target.is_file():
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
    for directory in ('assets/portraits', 'assets/battle-original', 'assets/battle-enhanced', 'assets/civil-staff', 'assets/original-ui', 'assets/equipment-icons'):
        if name.startswith(directory + '/') and (target.is_symlink() or target.parent.is_symlink() or
                                                  (root / directory).is_symlink() or
                                                  (root / 'assets').is_symlink()):
            raise FileNotFoundError(name)
    return target.read_bytes()


def make_handler(game, cloud_config, cloud_csp, static, audit=None, here=HERE):
    from remake.errors import GameError

    class Handler(BaseHTTPRequestHandler):
        # Every response closes its connection, including rejections with unread bodies.
        protocol_version = 'HTTP/1.0'

        def log_message(self, *unused):
            pass

        def handle(self):
            try:
                super().handle()
            except (ConnectionError, TimeoutError):
                self.close_connection = True

        def parse_request(self):
            if not super().parse_request():
                return False
            port = self.server.server_address[1]
            authorities = {f'127.0.0.1:{port}', f'localhost:{port}'}
            if port == 80:
                authorities.update(('127.0.0.1', 'localhost'))
            hosts = self.headers.get_all('Host', [])
            origins = self.headers.get_all('Origin', [])
            sites = self.headers.get_all('Sec-Fetch-Site', [])
            # Email confirmations and ordinary links may navigate to the static
            # shell from another site. This exception never covers API data,
            # subresources, frames, writes, or invalid Host/Origin headers.
            document_entry = (self.command == 'GET' and document_entry_path(self.path)
                              and self.headers.get_all('Sec-Fetch-Mode', []) == ['navigate']
                              and self.headers.get_all('Sec-Fetch-Dest', []) == ['document'])
            site_allowed = (not sites or len(sites) == 1 and
                            (sites[0] in ('same-origin', 'none') or
                             document_entry and sites[0] in ('same-site', 'cross-site')))
            target = self.requestline.split()[1]
            if (len(hosts) != 1 or hosts[0] not in authorities
                    or origins and (len(origins) != 1 or origins[0] not in {'http://' + host for host in authorities})
                    or not site_allowed
                    or not target.startswith('/') or target.startswith('//')):
                self.send(403, {'error': '请在本地游戏页面操作。'})
                return False
            return True

        def send(self, status, data, mime='application/json; charset=utf-8', *, etag=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            vary = status == 200 and self.path.startswith('/api/') and self.path != '/api/save' and mime.startswith('application/json')
            compressed = False
            if vary and len(data) >= 4096 and accepts_gzip(self.headers):
                packed = gzip.compress(data, compresslevel=1, mtime=0)
                if len(packed) < len(data):
                    data, compressed = packed, True
            self.close_connection = True
            self.connection.settimeout(self.server.request_timeout)
            self.send_response(status)
            self.send_header('Content-Type', mime)
            if status not in (204, 304):
                self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            self.send_header('Cache-Control', 'private, no-cache' if etag else 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', cloud_csp)
            if etag:
                self.send_header('ETag', etag)
            if vary:
                self.send_header('Vary', 'Accept-Encoding')
            if compressed:
                self.send_header('Content-Encoding', 'gzip')
            complete = False
            try:
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
                complete = True
            finally:
                if audit is not None:
                    safe_path = (self.path.split('?', 1)[0][:2048] + '?[query omitted]'
                                 if '?' in self.path else self.path[:2048])
                    audit.record('requests', {'method': self.command[:32], 'path': safe_path,
                                             'status': status, 'bytes': len(data) if complete else 0,
                                             'complete': complete})

        def do_GET(self):
            try:
                if self.path == '/api/state':
                    return self.send(200, game.view())
                if self.path == '/api/cloud-config':
                    return self.send(200, cloud_config)
                if self.path == '/api/march-status':
                    from remake.march_core import backend_status
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
                    from remake.march_core import config_for
                    return self.send(200, config_for(catalog.data))
                if self.path == '/api/save':
                    return self.send(200, game.export_save())
                if urlsplit(self.path).path == '/api/city-preview':
                    try:
                        query = parse_qs(urlsplit(self.path).query, keep_blank_values=True, max_num_fields=2)
                    except ValueError:
                        raise GameError('城池查询参数无效。')
                    if set(query) != {'scenario', 'city'} or any(len(v) != 1 for v in query.values()):
                        raise GameError('城池查询参数无效。')
                    return self.send(200, game.preview_city(query['scenario'][0], query['city'][0]))
                static_path = '/' if document_entry_path(self.path) else (versioned_asset_path(self.path) or self.path)
                if static_path in static:
                    name, mime = static[static_path]
                    try:
                        data = static_file_bytes(here, name)
                    except OSError:
                        return self.send(404, {'error': '未找到这个资源。'})
                    etag = '"' + hashlib.sha256(data).hexdigest() + '"'
                    tags = ','.join(self.headers.get_all('If-None-Match', [])).split(',')
                    if any(tag.strip() == '*' or tag.strip().removeprefix('W/') == etag for tag in tags):
                        return self.send(304, b'', mime, etag=etag)
                    return self.send(200, data, mime, etag=etag)
                self.send(404, {'error': '未找到这个页面。'})
            except GameError as exc:
                self.send(exc.status, {'error': str(exc)})
            except (ConnectionError, TimeoutError):
                pass

        def do_POST(self):
            try:
                if self.path not in ('/api/command', '/api/load'):
                    return self.send(404, {'error': '未找到这个操作。'})
                lengths = self.headers.get_all('Content-Length', [])
                if (self.headers.get_all('Transfer-Encoding') or len(lengths) != 1
                        or re.fullmatch(r'[0-9]+', lengths[0]) is None):
                    return self.send(400, {'error': '操作数据长度无效。'})
                digits = lengths[0].lstrip('0') or '0'
                if len(digits) > 7 or int(digits) > MAX_BODY_BYTES:
                    return self.send(413, {'error': '存档或操作数据大小无效。'})
                length = int(digits)
                if not length or len(self.headers.get_all('Content-Type', [])) != 1 or self.headers.get_content_type() != 'application/json' or self.headers.get_all('Content-Encoding'):
                    return self.send(400, {'error': '操作数据格式无效。'})
                try:
                    deadline = time.monotonic() + self.server.request_timeout
                    raw = bytearray()
                    while len(raw) < length:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError('Body deadline')
                        self.connection.settimeout(remaining)
                        chunk = self.rfile.read1(min(65536, length - len(raw)))
                        if not chunk:
                            break
                        raw.extend(chunk)
                except TimeoutError:
                    return self.send(408, {'error': '操作数据接收超时，进度未改变。'})
                if len(raw) != length:
                    return self.send(400, {'error': '操作数据不完整，进度未改变。'})
                payload = strict_json(raw)
                if not isinstance(payload, dict):
                    raise ValueError('payload')
                if self.path == '/api/command':
                    view = game.command(payload.get('kind'), payload.get('payload', {}), payload.get('revision'))
                else:
                    view = game.load_save(payload.get('save'), payload.get('revision'))
                self.send(200, view)
            except GameError as exc:
                self.send(exc.status, {'error': str(exc)})
            except (ValueError, TypeError, KeyError, RecursionError):
                self.send(400, {'error': '输入或存档不符合当前规则，进度未改变。'})
            except (ConnectionError, TimeoutError):
                pass
            except Exception:
                traceback.print_exc()
                self.send(500, {'error': '操作未完成，请核对当前进度后重试。'})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8878)
    parser.add_argument('--audit-log', type=Path)
    args = parser.parse_args()
    audit = AuditLog() if args.audit_log else None

    def audit_hook(event, values):
        if event == 'open':
            path = str(values[0])
            if any(part in Path(path).parts for part in ('.toolchain', '.venv-trace', 'analysis')) or Path(path).suffix.lower() in {'.nes', '.state'}:
                audit.record('denied_access', path[:2048])
                raise PermissionError('Forbidden original runtime input: ' + path)
            audit.record('file_opens', {'path': path[:2048], 'mode': str(values[1])[:32]})
        elif event == 'import':
            name = str(values[0])
            if name == 'py65' or name.startswith(('py65.', 'recovered.')):
                audit.record('denied_access', name[:256])
                raise ImportError('Forbidden runtime module: ' + name)
            audit.record('imports', name[:256])
    if args.audit_log:
        sys.addaudithook(audit_hook)
    sys.path.insert(0, str(ROOT / 'source'))
    from remake.session import CampaignSession
    from remake.cloud_config import public_config, content_security_policy
    cloud_config = public_config(HERE / 'config/cloud-save-public.json')
    cloud_csp = content_security_policy(cloud_config)
    current_index = json.loads((HERE / 'data/campaigns/index.json').read_text())
    game = CampaignSession([HERE / 'data' / name for name in current_index['catalogs']])
    static = {'/': ('index.html', 'text/html; charset=utf-8'),
              '/favicon.ico': ('favicon.ico', 'image/x-icon'),
              '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
              '/assets/site-icon-32.png': ('assets/site-icon-32.png', 'image/png'),
              '/assets/site-icon-180.png': ('assets/site-icon-180.png', 'image/png'),
              '/loading-cover.js': ('loading-cover.js', 'text/javascript; charset=utf-8'),
              '/loading-cover.css': ('loading-cover.css', 'text/css; charset=utf-8'),
              '/assets/loading/cover.png': ('assets/loading/cover.png', 'image/png'),
              '/save-transfer.js': ('save-transfer.js', 'text/javascript; charset=utf-8'),
              '/cloud-save.js': ('cloud-save.js', 'text/javascript; charset=utf-8'),
              '/cloud-recovery.js': ('cloud-recovery.js', 'text/javascript; charset=utf-8'),
              '/cloud-save-ui.js': ('cloud-save-ui.js', 'text/javascript; charset=utf-8'),
              '/cloud-save.css': ('cloud-save.css', 'text/css; charset=utf-8'),
              '/vendor/supabase.min.js': ('vendor/supabase.min.js', 'text/javascript; charset=utf-8'),
              '/vendor/supabase-LICENSES.txt': ('vendor/supabase-LICENSES.txt', 'text/plain; charset=utf-8'),
              '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
              '/autosave.js': ('autosave.js', 'text/javascript; charset=utf-8'),
              '/view-cache.js': ('view-cache.js', 'text/javascript; charset=utf-8'),
              '/map-render-cache.js': ('map-render-cache.js', 'text/javascript; charset=utf-8'),
              '/i18n.js': ('i18n.js', 'text/javascript; charset=utf-8'),
              '/calendar.js': ('calendar.js', 'text/javascript; charset=utf-8'),
              '/audio.js': ('audio.js', 'text/javascript; charset=utf-8'),
              '/events.js': ('events.js', 'text/javascript; charset=utf-8'),
              '/events.css': ('events.css', 'text/css; charset=utf-8'),
              '/original-ui.js': ('original-ui.js', 'text/javascript; charset=utf-8'),
              '/original-ui.css': ('original-ui.css', 'text/css; charset=utf-8'),
              '/command-menu.css': ('command-menu.css', 'text/css; charset=utf-8'),
              '/equipment-ui.css': ('equipment-ui.css', 'text/css; charset=utf-8'),
              '/facilities-ui.css': ('facilities-ui.css', 'text/css; charset=utf-8'),
              '/officer-choice.js': ('officer-choice.js', 'text/javascript; charset=utf-8'),
              '/officer-selection.js': ('officer-selection.js', 'text/javascript; charset=utf-8'),
              '/civil-staff.js': ('civil-staff.js', 'text/javascript; charset=utf-8'),
              '/domestic.js': ('domestic.js', 'text/javascript; charset=utf-8'),
              '/treasury.js': ('treasury.js', 'text/javascript; charset=utf-8'),
              '/facilities.js': ('facilities.js', 'text/javascript; charset=utf-8'),
              '/equipment.js': ('equipment.js', 'text/javascript; charset=utf-8'),
              '/battle-scene.js': ('battle-scene.js', 'text/javascript; charset=utf-8'),
              '/battlefields.js': ('battlefields.js', 'text/javascript; charset=utf-8'),
              '/command-books.js': ('command-books.js', 'text/javascript; charset=utf-8'),
              '/order-confirm.js': ('order-confirm.js', 'text/javascript; charset=utf-8'),
              '/config/battlefield-city-bindings.json': ('config/battlefield-city-bindings.json', 'application/json; charset=utf-8'),
              '/battle-scene.css': ('battle-scene.css', 'text/css; charset=utf-8'),
              '/duel-appearance.js': ('duel-appearance.js', 'text/javascript; charset=utf-8'),
              '/config/duel-appearances.json': ('config/duel-appearances.json', 'application/json; charset=utf-8'),
              '/assets/civil-staff/clerk-1.png': ('assets/civil-staff/clerk-1.png', 'image/png'),
              '/assets/civil-staff/clerk-2.png': ('assets/civil-staff/clerk-2.png', 'image/png'),
              '/assets/civil-staff/clerk-3.png': ('assets/civil-staff/clerk-3.png', 'image/png'),
              '/route-options.js': ('route-options.js', 'text/javascript; charset=utf-8'),
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
              '/layout.js': ('layout.js', 'text/javascript; charset=utf-8'),
              '/march-supply.js': ('march-supply.js', 'text/javascript; charset=utf-8'),
              '/map-terrain.js': ('map-terrain.js', 'text/javascript; charset=utf-8'),
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
              '/assets/map-road-centers.png': ('assets/map-road-centers.png', 'image/png'),
              '/assets/map-city-ground.png': ('map-source/hydrology-ground.png', 'image/png'),
              '/assets/map-western-range.png': ('assets/map-western-range.png', 'image/png'),
              '/assets/city-positions.json': ('assets/city-positions.json', 'application/json; charset=utf-8'),
              '/assets/unifont.woff': ('assets/unifont.woff', 'font/woff')}
    static.update(portrait_static_assets())
    static.update(civil_portrait_static_assets())
    static.update(audio_effect_static_assets())
    static.update(original_ui_static_assets())
    static.update(equipment_icon_static_assets())
    static.update(battle_static_assets())
    static.update(battlefield_static_assets())
    static.update(enhanced_battle_static_assets())

    Handler = make_handler(game, cloud_config, cloud_csp, static, audit)

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
            report = audit.snapshot()
            report['loaded_modules'] = {name: getattr(module, '__file__', None)
                                       for name, module in sorted(sys.modules.items())}
            report['game_journal'] = game.journal
            report['final_revision'] = game.revision
            report['final_state'] = game.to_dict()
            args.audit_log.parent.mkdir(parents=True, exist_ok=True)
            args.audit_log.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
