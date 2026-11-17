from functools import wraps
import json
from time import perf_counter
from remake.campaign import Campaign
from remake.session import CampaignSession

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
_original_session_command = CampaignSession.command

@wraps(_original_session_command)
def _profile_session_command(self, kind, payload, revision):
    global _active_start
    if kind != 'new':
        return _original_session_command(self, kind, payload, revision)
    row = {'scenario': payload.get('scenario'), 'new_ms': [], 'view_ms': [], 'decorate_ms': []}
    _active_start = row
    started = perf_counter()
    try:
        return _original_session_command(self, kind, payload, revision)
    finally:
        row['session_ms'] = (perf_counter() - started) * 1000
        _active_start = None
        _start_measurements.append(row)

CampaignSession.command = _profile_session_command
