"""Real loopback HTTP checks; isolated ephemeral ports, no cloud or live game."""
from contextlib import contextmanager
import gzip
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import socket
import struct
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
spec = importlib.util.spec_from_file_location('tk2_http_transport', ROOT / 'game/serve.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError('Timed out waiting for isolated HTTP server')
        time.sleep(.005)


class RecordingGame:
    def __init__(self):
        self.reads = self.writes = self.loads = 0

    def view(self):
        self.reads += 1
        return {'revision': 0, 'text': 'campaign ' * 4096}

    def export_save(self):
        self.reads += 1
        return {'format': 'test-save', 'text': 'saved ' * 4096}

    def command(self, *unused):
        self.writes += 1
        return self.view()

    def load_save(self, *unused):
        self.loads += 1
        return self.view()


@contextmanager
def isolated_server(game=None, *, timeout=.3, workers=32, audit=None):
    game = game or RecordingGame()
    with tempfile.TemporaryDirectory() as directory:
        here = Path(directory)
        (here / 'asset.txt').write_bytes(b'static version one')
        (here / 'index.html').write_bytes(b'<!doctype html><title>Game shell</title>')
        handler = transport.make_handler(game, {'enabled': False}, "default-src 'self'",
                                         {'/asset': ('asset.txt', 'text/plain'),
                                          '/': ('index.html', 'text/html')}, audit, here)
        server = transport.GameHTTPServer(('127.0.0.1', 0), handler,
                                          max_workers=workers, request_timeout=timeout)
        thread = Thread(target=lambda: server.serve_forever(poll_interval=.01))
        thread.start()
        try:
            yield server, game, here
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)
            if thread.is_alive() or server.connections:
                raise AssertionError('Isolated HTTP server did not stop')


def exchange(port, method='GET', path='/api/state', body=None, headers=None):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def raw_exchange(port, headers, body=b'', *, method='POST', path='/api/command'):
    with socket.create_connection(('127.0.0.1', port), timeout=3) as connection:
        request = f'{method} {path} HTTP/1.1\r\n' + '\r\n'.join(headers) + '\r\n\r\n'
        connection.sendall(request.encode('ascii') + body)
        connection.shutdown(socket.SHUT_WR)
        response = http.client.HTTPResponse(connection)
        response.begin()
        return response.status, dict(response.getheaders()), response.read()


class HTTPBoundaryTests(unittest.TestCase):
    def test_pkce_entry_does_not_log_auth_codes_or_expose_state(self):
        audit = transport.AuditLog()
        with isolated_server(audit=audit) as (server, game, _):
            port = server.server_address[1]
            headers = {'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'navigate',
                       'Sec-Fetch-Dest': 'document'}
            for path in ('/?code=fixture-code-1234', '/?sb_flow_id=flow1234&code=fixture-code-1234'):
                self.assertEqual(exchange(port, path=path, headers=headers)[0], 200)
            for path in ('/?code=short', '/?code=fixture-code-1234&code=other-code',
                         '/?code=fixture-code-1234&token=forbidden', '/?sb_flow_id=flow1234',
                         '/api/save?code=fixture-code-1234'):
                self.assertEqual(exchange(port, path=path, headers=headers)[0], 403)
            self.assertNotIn('fixture-code-1234', json.dumps(audit.snapshot()))
            self.assertEqual((game.reads, game.writes, game.loads), (0, 0, 0))

    def test_cross_site_links_only_open_the_static_top_level_shell(self):
        with isolated_server() as (server, game, _):
            port = server.server_address[1]
            base = [f'Host: 127.0.0.1:{port}', 'Sec-Fetch-Site: cross-site',
                    'Sec-Fetch-Mode: navigate', 'Sec-Fetch-Dest: document']
            for site in ('same-site', 'cross-site'):
                headers = [base[0], f'Sec-Fetch-Site: {site}', *base[2:]]
                status, _, body = raw_exchange(port, headers, method='GET', path='/')
                self.assertEqual(status, 200)
                self.assertIn(b'Game shell', body)
                for path in ('/index.html', '/api/state', '/api/save', '/api/cloud-config', '/asset'):
                    self.assertEqual(raw_exchange(port, headers, method='GET', path=path)[0], 403)
                for path in ('/', '/api/command', '/api/load'):
                    self.assertEqual(raw_exchange(port, headers, b'{}', path=path)[0], 403)
            invalid = [base[:2], [*base[:2], 'Sec-Fetch-Mode: cors', base[3]],
                       [*base[:3], 'Sec-Fetch-Dest: iframe'],
                       [*base[:3], 'Sec-Fetch-Dest: empty'],
                       [*base, 'Sec-Fetch-Mode: navigate'],
                       [*base, 'Sec-Fetch-Dest: document'],
                       [*base, 'Sec-Fetch-Site: cross-site'],
                       [*base, 'Origin: https://attacker.example'],
                       ['Host: attacker.example', *base[1:]], [*base, base[0]]]
            for headers in invalid:
                self.assertEqual(raw_exchange(port, headers, method='GET', path='/')[0], 403)
            self.assertEqual((game.reads, game.writes, game.loads), (0, 0, 0))

    def test_untrusted_requests_are_rejected_before_state_access(self):
        with isolated_server() as (server, game, _):
            port = server.server_address[1]
            local = f'Host: 127.0.0.1:{port}'
            cases = [[], ['Host: attacker.example'], [local, local],
                     [f'Host: localhost:{port}.attacker.example'],
                     [f'Host: user@127.0.0.1:{port}'], [local + ' '],
                     [local, 'Origin: https://attacker.example'],
                     [local, f'Origin: http://127.0.0.1:{port}', f'Origin: http://127.0.0.1:{port}'],
                     [local, 'Origin: null'], [local, 'Sec-Fetch-Site: cross-site'],
                     [local, 'Sec-Fetch-Site: same-site'],
                     [local, 'Sec-Fetch-Site: none', 'Sec-Fetch-Site: none']]
            for method, path in [('GET', '/api/state'), ('GET', '/api/save'), ('POST', '/api/command')]:
                for headers in cases:
                    with self.subTest(method=method, path=path, headers=headers):
                        status, response_headers, _ = raw_exchange(port, headers, method=method, path=path)
                        self.assertEqual(status, 403)
                        self.assertEqual(response_headers['Connection'], 'close')
            for target in ['http://attacker.example/api/state', '//attacker.example/api/state']:
                self.assertEqual(raw_exchange(port, [local], method='GET', path=target)[0], 403)
            self.assertEqual((game.reads, game.writes, game.loads), (0, 0, 0))
            for site in ('same-origin', 'none'):
                status, headers, _ = exchange(port, headers={'Host': f'localhost:{port}',
                    'Origin': f'http://localhost:{port}', 'Sec-Fetch-Site': site})
                self.assertEqual(status, 200)
                self.assertEqual(headers['Connection'], 'close')
            self.assertEqual(exchange(port)[0], 200, 'Header-light local scripts remain supported')

    def test_framing_and_ambiguous_json_never_reach_commands(self):
        with isolated_server() as (server, game, _):
            port = server.server_address[1]
            base = [f'Host: 127.0.0.1:{port}', 'Content-Type: application/json']
            framing = [([], 400), (['Content-Length: 2', 'Content-Length: 2'], 400),
                       (['Content-Length: +2'], 400), (['Content-Length: -2'], 400),
                       (['Content-Length: 2, 2'], 400), (['Content-Length: 2x'], 400),
                       (['Content-Length: 0'], 400), (['Content-Length: 2097153'], 413),
                       (['Content-Length: 2', 'Transfer-Encoding: chunked'], 400),
                       (['Content-Length: 2', 'Transfer-Encoding: identity'], 400),
                       (['Content-Length: 2', 'Content-Type: application/json'], 400),
                       (['Content-Length: 2', 'Content-Encoding: gzip'], 400)]
            for headers, expected in framing:
                with self.subTest(headers=headers):
                    self.assertEqual(raw_exchange(port, base + headers, b'{}')[0], expected)
            malformed = [b'[]', b'{} trailing', b'{"revision":0,"revision":1}',
                         b'{"payload":{"seed":1,"seed":2}}', b'{"x":NaN}',
                         b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}',
                         b'{"x":"\xff"}', b'{"x":' + b'[' * 65 + b'0' + b']' * 65 + b'}']
            for body in malformed:
                with self.subTest(body=body[:70]):
                    self.assertEqual(raw_exchange(port, base + [f'Content-Length: {len(body)}'], body)[0], 400)
            self.assertEqual(raw_exchange(port, base + ['Content-Length: 100'], b'{}')[0], 400)
            self.assertEqual((game.reads, game.writes, game.loads), (0, 0, 0))
            body = b'{"kind":"new","payload":{},"revision":0}'
            self.assertEqual(raw_exchange(port, base + [f'Content-Length: 000{len(body)}'], body)[0], 200)
            self.assertEqual(game.writes, 1)

    def test_body_deadline_releases_idle_and_trickling_clients(self):
        with isolated_server(timeout=.2) as (server, game, _):
            port = server.server_address[1]
            for trickle in (False, True):
                with self.subTest(trickle=trickle), socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
                    start = time.monotonic()
                    connection.sendall(f'POST /api/command HTTP/1.1\r\nHost: localhost:{port}\r\nContent-Type: application/json\r\nContent-Length: 1000\r\n\r\n{{'.encode())
                    if trickle:
                        for _ in range(5):
                            time.sleep(.05)
                            try:
                                connection.sendall(b' ')
                            except OSError:
                                break
                    response = http.client.HTTPResponse(connection)
                    response.begin()
                    self.assertEqual(response.status, 408)
                    response.read()
                    self.assertLess(time.monotonic() - start, 1)
            wait_for(lambda: not server.connections)
            self.assertEqual(game.writes, 0)
            self.assertEqual(exchange(port)[0], 200)

    def test_worker_admission_and_idle_header_timeout_are_bounded(self):
        with isolated_server(timeout=.3, workers=2) as (server, _, _):
            port = server.server_address[1]
            blocked = [socket.create_connection(('127.0.0.1', port), timeout=2) for _ in range(2)]
            try:
                for connection in blocked:
                    connection.sendall(b'GET /api/state HTTP/1.1\r\nHost:')
                wait_for(lambda: len(server.connections) == 2)
                start = time.monotonic()
                self.assertEqual(exchange(port)[0], 503)
                self.assertLess(time.monotonic() - start, .5)
                for connection in blocked:
                    self.assertEqual(connection.recv(1), b'')
                wait_for(lambda: not server.connections)
                self.assertEqual(exchange(port)[0], 200)
            finally:
                for connection in blocked:
                    connection.close()

    def test_valid_slow_body_gets_a_fresh_response_timeout(self):
        game = RecordingGame()
        game.view = lambda: {'text': 'x' * (8 * 1024 * 1024)}
        with isolated_server(game, timeout=.6) as (server, _, _):
            port = server.server_address[1]
            with socket.create_connection(('127.0.0.1', port), timeout=3) as connection:
                connection.sendall(f'POST /api/command HTTP/1.1\r\nHost: localhost:{port}\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{{'.encode())
                time.sleep(.48)
                connection.sendall(b'}')
                # The response exceeds socket buffers. A leftover body timeout
                # would expire while this healthy client is briefly not reading.
                time.sleep(.25)
                response = http.client.HTTPResponse(connection)
                response.begin()
                self.assertEqual(response.status, 200)
                self.assertEqual(len(json.loads(response.read())['text']), 8 * 1024 * 1024)
            self.assertEqual(game.writes, 1)

    def test_static_revalidation_and_symlink_allowlist(self):
        with isolated_server() as (server, _, here):
            port = server.server_address[1]
            status, headers, body = exchange(port, path='/asset', headers={'Accept-Encoding': 'gzip'})
            self.assertEqual((status, body), (200, b'static version one'))
            self.assertEqual(headers['Cache-Control'], 'private, no-cache')
            self.assertNotIn('Content-Encoding', headers)
            tag = headers['ETag']
            status, refreshed, body = exchange(port, path='/asset', headers={'If-None-Match': 'W/' + tag})
            self.assertEqual((status, body, refreshed['ETag']), (304, b'', tag))
            (here / 'asset.txt').write_bytes(b'static version two')
            status, refreshed, body = exchange(port, path='/asset', headers={'If-None-Match': tag})
            self.assertEqual((status, body), (200, b'static version two'))
            self.assertNotEqual(refreshed['ETag'], tag)
            for path in ('/../asset.txt', '/asset.txt', '/missing', '/assets/'):
                self.assertEqual(exchange(port, path=path)[0], 404)
            (here / 'asset.txt').unlink()
            (here / 'asset.txt').symlink_to(ROOT / 'README.md')
            self.assertEqual(exchange(port, path='/asset')[0], 404)

    def test_gzip_negotiation_and_save_bytes(self):
        with isolated_server() as (server, _, _):
            port = server.server_address[1]
            _, identity_headers, identity = exchange(port)
            self.assertEqual(identity_headers['Cache-Control'], 'no-store')
            self.assertEqual(identity_headers['Vary'], 'Accept-Encoding')
            for accepted in ('gzip', 'br, gzip;q=0.5'):
                status, headers, packed = exchange(port, headers={'Accept-Encoding': accepted})
                self.assertEqual((status, headers['Content-Encoding']), (200, 'gzip'))
                self.assertEqual(gzip.decompress(packed), identity)
                self.assertEqual(int(headers['Content-Length']), len(packed))
                self.assertLess(len(packed), len(identity))
            for declined in ('gzip;q=0', 'br, *;q=1', 'gzip;q=bad', 'gzip;q=0, gzip;q=1'):
                _, headers, body = exchange(port, headers={'Accept-Encoding': declined})
                self.assertNotIn('Content-Encoding', headers)
                self.assertEqual(body, identity)
            saved = exchange(port, path='/api/save')[2]
            _, headers, body = exchange(port, path='/api/save', headers={'Accept-Encoding': 'gzip'})
            self.assertEqual(body, saved)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertNotIn('Content-Encoding', headers)

    def test_audit_caps_and_failed_delivery(self):
        audit = transport.AuditLog({key: 2 for key in transport.AUDIT_LIMITS})
        for key in ('file_opens', 'imports', 'denied_access'):
            for number in range(5):
                audit.record(key, str(number))
        with isolated_server(audit=audit) as (server, _, _):
            for _ in range(5):
                self.assertEqual(exchange(server.server_address[1], path='/asset')[0], 200)
        snapshot = audit.snapshot()
        for key in transport.AUDIT_LIMITS:
            self.assertEqual((len(snapshot[key]), snapshot['counts'][key], snapshot['truncated'][key]), (2, 5, 3))
        started, release = Event(), Event()
        game = RecordingGame()
        def held_view():
            started.set()
            release.wait(2)
            return {'text': 'x' * 100000}
        game.view = held_view
        delivery_audit = transport.AuditLog()
        with isolated_server(game, audit=delivery_audit) as (server, _, _):
            connection = socket.create_connection(('127.0.0.1', server.server_address[1]), timeout=2)
            connection.sendall(f'GET /api/state HTTP/1.1\r\nHost: localhost:{server.server_address[1]}\r\n\r\n'.encode())
            self.assertTrue(started.wait(1))
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            connection.close()
            release.set()
            wait_for(lambda: bool(delivery_audit.snapshot()['requests']))
            row = delivery_audit.snapshot()['requests'][0]
            self.assertFalse(row['complete'])
            self.assertEqual(row['bytes'], 0)

    def test_shutdown_waits_for_an_admitted_transaction(self):
        started, release, completed = Event(), Event(), Event()
        game = RecordingGame()
        def held_command(*unused):
            started.set()
            release.wait(3)
            game.writes += 1
            completed.set()
            return {'revision': 1}
        game.command = held_command
        with isolated_server(game, timeout=5) as (server, _, _):
            port = server.server_address[1]
            connection = socket.create_connection(('127.0.0.1', port), timeout=2)
            connection.sendall(f'POST /api/command HTTP/1.1\r\nHost: localhost:{port}\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{{}}'.encode())
            self.assertTrue(started.wait(1))
            server.shutdown()
            closer = Thread(target=server.server_close)
            closer.start()
            try:
                time.sleep(.05)
                self.assertTrue(closer.is_alive(), 'Shutdown must join admitted transactions')
                self.assertFalse(completed.is_set())
            finally:
                release.set()
                connection.close()
                closer.join(2)
            self.assertFalse(closer.is_alive())
            self.assertTrue(completed.is_set())
            self.assertEqual(game.writes, 1)


class HTTPGameIntegrationTests(unittest.TestCase):
    def test_real_game_save_load_gzip_and_shutdown_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / 'audit.json'
            with tempfile.TemporaryFile(mode='w+') as errors:
                process = subprocess.Popen([sys.executable, '-I', '-S', '-B', str(ROOT / 'game/serve.py'),
                    '--port', '0', '--audit-log', str(audit_path)], cwd=ROOT,
                    env={**os.environ, 'MARCH_CORE_BACKEND': 'python'}, stdout=subprocess.PIPE,
                    stderr=errors, text=True)
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ)
                        self.assertTrue(selector.select(20), 'Game server startup timeout')
                        line = process.stdout.readline()
                    match = re.search(r'127\.0\.0\.1:(\d+)', line)
                    self.assertIsNotNone(match, 'Isolated server failed to start')
                    port = int(match.group(1))
                    self.assertNotEqual(port, 8878)
                    status, _, identity = exchange(port)
                    self.assertEqual(status, 200)
                    state = json.loads(identity)
                    _, headers, packed = exchange(port, headers={'Accept-Encoding': 'gzip'})
                    self.assertEqual(headers['Content-Encoding'], 'gzip')
                    self.assertEqual(gzip.decompress(packed), identity)
                    print(f'HTTP state transport: identity={len(identity)} bytes, gzip={len(packed)} bytes')
                    command = {'kind': 'new', 'revision': state['revision'],
                               'payload': {'scenario': 'mainland217-07', 'faction': 'shu', 'seed': 2026}}
                    status, _, body = exchange(port, 'POST', '/api/command', json.dumps(command),
                                               {'Content-Type': 'application/json'})
                    self.assertEqual(status, 200, body[:200])
                    revision = json.loads(body)['revision']
                    status, _, save = exchange(port, path='/api/save')
                    self.assertEqual(status, 200)
                    rng = json.loads(save)['state']['rng']
                    self.assertEqual(exchange(port, path='/api/save', headers={'Accept-Encoding': 'gzip'})[2], save)
                    for invalid in (b'{"save":NaN,"revision":1}', b'{"save":{},"save":{},"revision":1}', b'{"save":{},"revision":1}'):
                        self.assertEqual(exchange(port, 'POST', '/api/load', invalid, {'Content-Type': 'application/json'})[0], 400)
                        self.assertEqual(exchange(port, path='/api/save')[2], save)
                    load_body = b'{"save":' + save + b',"revision":' + str(revision).encode() + b'}'
                    status, _, body = exchange(port, 'POST', '/api/load', load_body, {'Content-Type': 'application/json'})
                    self.assertEqual(status, 200, body[:200])
                    self.assertEqual(json.loads(body)['revision'], revision + 1)
                    self.assertEqual(exchange(port, path='/api/save')[2], save)
                finally:
                    if process.poll() is None:
                        process.terminate()
                    process.communicate(timeout=15)
                    errors.seek(0)
                    diagnostics = errors.read()
                self.assertEqual(process.returncode, 0, diagnostics)
                self.assertNotIn('Traceback', diagnostics)
            audit = json.loads(audit_path.read_text())
            self.assertEqual(audit['final_state']['rng'], rng)
            self.assertEqual(audit['final_revision'], revision + 1)
            self.assertEqual(audit['game_journal'][-1]['kind'], 'load')
            for key in transport.AUDIT_LIMITS:
                self.assertLessEqual(len(audit[key]), audit['limits'][key])
                self.assertEqual(audit['counts'][key], len(audit[key]) + audit['truncated'][key])


if __name__ == '__main__':
    unittest.main()
