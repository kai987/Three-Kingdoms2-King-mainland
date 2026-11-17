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
