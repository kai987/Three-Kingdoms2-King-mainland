from functools import wraps
import json
from time import perf_counter
from remake.campaign import Campaign
from remake.session import CampaignSession
from remake import browser_runtime
from remake.view_transport import ViewTransport

_start_measurements = []
_active_start = None

def _time_method(owner, name, key):
    original = getattr(owner, name)

    @wraps(original)
    def timed(*args, **kwargs):
        row = _active_start
        if row is None:
            return original(*args, **kwargs)
        started = perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            row[key].append((perf_counter() - started) * 1000)

    setattr(owner, name, timed)

_time_method(Campaign, '_new', 'new_ms')
_time_method(Campaign, 'view', 'view_ms')
_time_method(CampaignSession, '_decorate_view', 'decorate_ms')
_time_method(CampaignSession, 'command', 'session_ms')
_time_method(browser_runtime.BrowserRuntime, '_catalog', 'catalog_ms')
_time_method(ViewTransport, 'pack', 'pack_ms')
_time_method(browser_runtime, '_encode', 'encode_ms')
_original_dispatch = browser_runtime.BrowserRuntime.dispatch_json

@wraps(_original_dispatch)
def _profile_dispatch(self, path, method='GET', body=None, **kwargs):
    global _active_start
    if path != '/api/command' or method != 'POST':
        return _original_dispatch(self, path, method, body, **kwargs)
    data = json.loads(body)
    if data['kind'] != 'new':
        return _original_dispatch(self, path, method, body, **kwargs)
    row = {key: [] for key in ('new_ms','view_ms','decorate_ms','session_ms',
                                'catalog_ms','pack_ms','encode_ms')}
    row['scenario'] = data['payload']['scenario']
    _active_start = row
    started = perf_counter()
    try:
        return _original_dispatch(self, path, method, body, **kwargs)
    finally:
        row['dispatch_ms'] = (perf_counter() - started) * 1000
        _active_start = None
        _start_measurements.append(row)

browser_runtime.BrowserRuntime.dispatch_json = _profile_dispatch

# Only the measured opening call replaces these names inside view_transport.
# The Web files, inputs, return values and original digest functions stay intact.
from hashlib import sha256 as _sha256
from types import SimpleNamespace
from remake import view_transport as _transport

_pack = ViewTransport.pack
_json_dumps = _transport.json.dumps
_pack_data = None
_pack_active = None
_static_samples = []
_other_pack_calls = []
_SAMPLE_KEYS = ('scenarios', 'rules', 'calendar_rules', 'difficulties', 'tactics', 'map_presentation')

def _clock_ms():
    return perf_counter() * 1000

def _profile_dumps(value, *args, **kwargs):
    part = _pack_data['static'] if isinstance(value, dict) else _pack_data['route']
    global _pack_active
    _pack_active = part
    part['json_start'] = _clock_ms()
    text = _json_dumps(value, *args, **kwargs)
    part['json_end'] = _clock_ms()
    return text

class _TimedDigest:
    def __init__(self, original, part):
        self.original = original
        self.part = part

    def hexdigest(self):
        value = self.original.hexdigest()
        self.part['sha_end'] = _clock_ms()
        self.part['digest'] = value
        return value

def _profile_sha(data):
    part = _pack_active
    part['bytes'] = len(data)
    part['sha_start'] = _clock_ms()
    return _TimedDigest(_sha256(data), part)

@wraps(_pack)
def _profile_opening_pack(self, value, source_sha, known=''):
    global _pack_data, _pack_active
    if _active_start is None:
        hit = source_sha in self.catalogs
        result = _pack(self, value, source_sha, known)
        if isinstance(result, dict) and result.get('transport') == _transport.SCHEMA:
            _other_pack_calls.append(dict(source_sha=source_sha, cache_hit=hit, token=result['catalog_token']))
        return result
    cache_before=list(self.catalogs)
    hit = source_sha in self.catalogs
    known_static, _, known_route = known.partition(':')
    details = {'static':{},'route':{}}
    _pack_data = details
    original_json, original_hashlib = _transport.json, _transport.hashlib
    _transport.json = SimpleNamespace(dumps=_profile_dumps)
    _transport.hashlib = SimpleNamespace(sha256=_profile_sha)
    started = _clock_ms()
    try:
        result = _pack(self, value, source_sha, known)
    finally:
        ended = _clock_ms()
        _transport.json, _transport.hashlib = original_json, original_hashlib
        _pack_data = _pack_active = None
    cold = details['static']
    route = details['route']
    assert bool(cold) != hit and bool(route)
    assert result['quote_token'] == route['digest']
    if cold:
        assert result['catalog_token'] == cold['digest']
        _, static = self.catalogs[source_sha]
        _static_samples.append((_active_start['scenario'], {k:static[k] for k in _SAMPLE_KEYS if k in static}))
    _active_start['pack_detail'] = dict(
        source_sha=source_sha, cache_before=cache_before, cache_after=list(self.catalogs), cache_hit=hit,
        browser_static_hit=known_static == result['catalog_token'],
        browser_quote_hit=known_route == result['quote_token'],
        sends_static='static_catalog' in result,
        sends_quotes='travel_quotes' in result['view']['catalog'],
        token=result['catalog_token'], quote_token=result['quote_token'], total_ms=ended-started,
        static_construct_ms=cold['json_start']-started if cold else 0,
        static_json_ms=cold['json_end']-cold['json_start'] if cold else 0,
        static_utf8_ms=cold['sha_start']-cold['json_end'] if cold else 0,
        static_sha_ms=cold['sha_end']-cold['sha_start'] if cold else 0,
        static_bytes=cold.get('bytes',0),
        route_key_ms=route['json_start']-(cold['sha_end'] if cold else started),
        route_json_ms=route['json_end']-route['json_start'],
        route_utf8_ms=route['sha_start']-route['json_end'],
        route_sha_ms=route['sha_end']-route['sha_start'], route_bytes=route['bytes'],
        dynamic_assembly_ms=ended-route['sha_end'])
    return result

ViewTransport.pack = _profile_opening_pack

def _opening_pack_report():
    # Sample selected common fields only after all timed calls and assertions.
    components = []
    for scenario, sample in _static_samples:
        for key, value in sample.items():
            raw = _json_dumps(value, sort_keys=True, ensure_ascii=False,
                              allow_nan=False,separators=(',', ':')).encode('utf-8')
            components.append(dict(scenario=scenario, key=key, bytes=len(raw),
                                   sha256=_sha256(raw).hexdigest()))
    return json.dumps(dict(openings=_start_measurements, components=components, other_pack_calls=_other_pack_calls))
