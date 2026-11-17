"""Runtime-only instrumentation for the fixed Web executable."""
from functools import wraps
from hashlib import sha256
import json
import re
from time import perf_counter
from types import SimpleNamespace

from remake import browser_runtime, view_transport

Runtime = browser_runtime.BrowserRuntime
Transport = view_transport.ViewTransport
_pack = Transport.pack
_compact = Runtime.dispatch_compact_json
_encode = browser_runtime._encode
_dumps = json.dumps
_active = None
_rows = []
_opt_in = 'scenarios-v1|'


def _ms():
    return perf_counter() * 1000


def _split_known(known):
    if not isinstance(known, str) or not known.startswith(_opt_in):
        return known, None
    original, delimiter, shared = known[len(_opt_in):].partition('|')
    if not delimiter or not re.fullmatch(r'(?:[a-f0-9]{64})?', shared):
        return known, None
    return original, shared


@wraps(_compact)
def _dispatch(self, path, method='GET', body=None, known=''):
    global _active
    payload = {}
    if path == '/api/command' and isinstance(body, str):
        try:
            payload = json.loads(body)
        except (ValueError, TypeError):
            return _compact(self, path, method, body, known)
        if not isinstance(payload, dict):
            return _compact(self, path, method, body, known)
    scenario = payload['payload']['scenario'] if payload.get('kind') == 'new' else None
    original, shared_known = _split_known(known)
    measured = path == '/api/state' or scenario is not None
    if not measured and shared_known is None:
        return _compact(self, path, method, body, known)
    row = dict(scenario=scenario, shared=shared_known is not None, pack_ms=0, static_json_ms=0,
               static_sha_ms=0, shared_json_ms=0, shared_sha_ms=0, response_json_ms=0,
               static_worker_hit=False, shared_worker_hit=False, shared_browser_hit=False,
               shared_sent=False, static_sent=False)
    started = _ms()
    _active = (row, shared_known, self.session._opening_previews)
    try:
        result = _compact(self, path, method, body, original)
    finally:
        row['python_ms'] = _ms() - started
        _active = None
    row['status'] = result['status']
    if measured:
        _rows.append(row)
    return result


def _profiled_pack(transport, value, source_sha, known, row):
    is_static = False

    def dumps(value, *args, **kwargs):
        nonlocal is_static
        is_static = isinstance(value, dict)
        start = _ms()
        text = _dumps(value, *args, **kwargs)
        if is_static:
            row['static_json_ms'] += _ms() - start
        return text

    def digest(value):
        start = _ms()
        result = sha256(value)
        row['static_sha_ms'] += _ms() - start if is_static else 0
        return result

    original_json, original_sha = view_transport.json, view_transport.hashlib
    view_transport.json = SimpleNamespace(dumps=dumps)
    view_transport.hashlib = SimpleNamespace(sha256=digest)
    try:
        return _pack(transport, value, source_sha, known)
    finally:
        view_transport.json, view_transport.hashlib = original_json, original_sha


@wraps(_pack)
def _pack_with_shared_scenarios(self, value, source_sha, known=''):
    if _active is None or not isinstance(value, dict) or 'scenarios' not in value.get('catalog', {}):
        return _pack(self, value, source_sha, known)
    row, known_shared, preview = _active
    start = _ms()
    if known_shared is None:
        transport = self
        filtered = value
    else:
        transport = getattr(self, '_experiment_transport', None)
        if transport is None:
            transport = self._experiment_transport = Transport()
        shared = getattr(self, '_experiment_scenarios', None)
        if shared is None or shared[0] is not preview or shared[1] != _experimental_preview_sha:
            scenarios = value['catalog']['scenarios']
            start_json = _ms()
            raw = _dumps(scenarios, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
            row['shared_json_ms'] = _ms() - start_json
            start_sha = _ms()
            token = sha256(raw).hexdigest()
            row['shared_sha_ms'] = _ms() - start_sha
            shared = self._experiment_scenarios = (preview, _experimental_preview_sha, token, scenarios)
        else:
            row['shared_worker_hit'] = True
        filtered = dict(value, catalog={k:v for k,v in value['catalog'].items() if k != 'scenarios'})
    row['static_worker_hit'] = source_sha in transport.catalogs
    result = _profiled_pack(transport, filtered, source_sha, known, row)
    if known_shared is not None:
        row['shared_browser_hit'] = known_shared == shared[2]
        result['scenarios_token'] = shared[2]
        if not row['shared_browser_hit']:
            result['shared_scenarios'] = shared[3]
            row['shared_sent'] = True
    row['static_sent'] = 'static_catalog' in result
    row['pack_ms'] = _ms() - start
    return result


def _profile_encode(value):
    row = _active[0] if _active is not None else None
    start = _ms()
    text = _encode(value)
    if row is not None:
        row['response_json_ms'] += _ms() - start
    return text


Transport.pack = _pack_with_shared_scenarios
Runtime.dispatch_compact_json = _dispatch
browser_runtime._encode = _profile_encode
