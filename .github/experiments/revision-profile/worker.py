"""Temporary sampling wrappers for the browser runtime, active on GET /api/state."""
import time as _tk2p_time
from js import performance as _tk2p_clock
import remake.browser_runtime as _tk2p_runtime
from remake.campaign import Campaign as _tk2p_campaign
from remake.session import CampaignSession as _tk2p_session
from remake.view_transport import ViewTransport as _tk2p_transport

_tk2p_records = []
_tk2p_current = None
_tk2p_original_dispatch = _tk2p_runtime.BrowserRuntime.dispatch_json

def _tk2p_now():
    return _tk2p_clock.timeOrigin + _tk2p_clock.now()

def _tk2p_measure(name, original):
    def timed(*args, **kwargs):
        row = _tk2p_current
        if row is None:
            return original(*args, **kwargs)
        start = _tk2p_time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            elapsed = (_tk2p_time.perf_counter() - start) * 1000
            row[name] = row.get(name, 0) + elapsed
    return timed

def _tk2p_dispatch(runtime, path, method='GET', body=None, *, _known=None):
    global _tk2p_current
    if path != '/api/state' or method != 'GET':
        return _tk2p_original_dispatch(runtime, path, method, body, _known=_known)
    row = {'pythonStart': _tk2p_now(), 'compact': _known is not None}
    _tk2p_current = row
    try:
        return _tk2p_original_dispatch(runtime, path, method, body, _known=_known)
    finally:
        row['pythonEnd'] = _tk2p_now()
        _tk2p_current = None
        _tk2p_records.append(row)

_tk2p_session.view = _tk2p_measure('viewMs', _tk2p_session.view)
_tk2p_campaign.view = _tk2p_measure('campaignViewMs', _tk2p_campaign.view)
_tk2p_session._decorate_view = _tk2p_measure('decorateMs', _tk2p_session._decorate_view)
_tk2p_transport.pack = _tk2p_measure('packMs', _tk2p_transport.pack)
_tk2p_runtime._encode = _tk2p_measure('encodeMs', _tk2p_runtime._encode)
_tk2p_runtime.BrowserRuntime.dispatch_json = _tk2p_dispatch
