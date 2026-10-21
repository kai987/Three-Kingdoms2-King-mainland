"""Optional native adapter for the same pure Rust core shipped to the browser.

Only JSON calculations cross this boundary. State, RNG, transactions and the
released save format remain owned by the campaign. Missing native builds use
our retained Python reference; explicit ``rust`` mode fails instead of hiding a
missing or broken build. Context overrides are local to the current thread.
"""
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
import ctypes
import json
import os
from pathlib import Path
import sys
from threading import RLock

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ('travel_rules', 'travel_hazards', 'city_coordinates', 'travel_routes',
          'exploration_routes', 'links')
_backend = ContextVar('march_core_backend', default=None)
_lock = RLock()
_library = None
_attempted = False
_load_error = None
_contexts = OrderedDict()
_calls = 0


class CoreUnavailable(RuntimeError):
    """An explicitly requested native build is absent or has the wrong ABI."""


def config_for(data):
    """Extract immutable route inputs without rewriting the catalog or its SHA."""
    return {field: data[field] for field in FIELDS if field in data}


@contextmanager
def using_backend(name):
    if name not in ('auto', 'python', 'rust'):
        raise ValueError('Unknown march backend')
    token = _backend.set(name)
    try:
        yield
    finally:
        _backend.reset(token)


def _mode():
    mode = _backend.get() or os.environ.get('MARCH_CORE_BACKEND', 'auto')
    if mode not in ('auto', 'python', 'rust'):
        raise ValueError('MARCH_CORE_BACKEND must be auto, python or rust')
    return mode


def _load():
    global _attempted, _library, _load_error
    with _lock:
        if _attempted:
            return _library
        _attempted = True
        name = 'libmarch_core.dylib' if sys.platform == 'darwin' else 'march_core.dll' if sys.platform == 'win32' else 'libmarch_core.so'
        path = ROOT / 'build' / 'march-core' / name
        try:
            lib = ctypes.CDLL(str(path))
            lib.march_version.argtypes = []
            lib.march_version.restype = ctypes.c_uint32
            if lib.march_version() != 1:
                raise OSError('Unsupported march core ABI')
            lib.march_alloc.argtypes = [ctypes.c_uint32]
            lib.march_alloc.restype = ctypes.c_void_p
            lib.march_call.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            lib.march_call.restype = ctypes.c_void_p
            lib.march_result_len.argtypes = []
            lib.march_result_len.restype = ctypes.c_uint32
            lib.march_free.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            lib.march_free.restype = None
            _library = lib
        except (OSError, AttributeError) as exc:
            _load_error = str(exc)
        return _library


def enabled():
    mode = _mode()
    if mode == 'python':
        return False
    available = _load() is not None
    if not available and mode == 'rust':
        raise CoreUnavailable(_load_error or 'Build the native march core first')
    return available


def _call(lib, request):
    global _calls
    raw = json.dumps(request, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    if len(raw) > 0xffffffff:
        raise ValueError('March request too large')
    source = lib.march_alloc(len(raw))
    if not source:
        raise CoreUnavailable('March input allocation failed')
    result = None
    length = 0
    try:
        ctypes.memmove(source, raw, len(raw))
        result = lib.march_call(source, len(raw))
        length = lib.march_result_len()
        if not result or not length:
            raise CoreUnavailable('March core returned no result')
        reply = json.loads(ctypes.string_at(result, length))
        _calls += 1
    finally:
        if result:
            lib.march_free(result, length)
        lib.march_free(source, len(raw))
    if not reply.get('ok'):
        raise ValueError(reply.get('error', 'March calculation failed'))
    return reply['value']


def invoke(operation, *, data=None, **payload):
    """Call one operation under a lock covering ABI buffers and context lifetime."""
    if not enabled():
        raise CoreUnavailable('Native march core is disabled')
    with _lock:
        lib = _load()
        if data is not None and operation in ('allowed', 'evaluate_leg', 'route_allowed'):
            # These public helpers accept mutable dictionaries. Send their small
            # rule/coordinate inputs directly, so edits between calls are visible;
            # only immutable campaign graphs use registered contexts.
            payload['data'] = {field: data[field] for field in
                               ('travel_rules', 'travel_hazards', 'city_coordinates') if field in data}
        elif data is not None:
            identity = id(data)
            entry = _contexts.get(identity)
            if entry is None or entry[0] is not data:
                context = _call(lib, {'op': 'register', 'data': config_for(data)})
                _contexts[identity] = (data, context)
                if len(_contexts) > 128:
                    _, old = _contexts.popitem(last=False)
                    _call(lib, {'op': 'unregister', 'context': old[1]})
            else:
                context = entry[1]
                _contexts.move_to_end(identity)
            payload['context'] = context
        return _call(lib, dict(payload, op=operation))


def state_input(state):
    return dict(cities=[dict(id=city.id, owner=city.owner) for city in state.cities.values()],
                month=state.month,
                discovered=state.extension.get('travel', {}).get('discovered', []))


def backend_status():
    native = enabled()
    return dict(engine='rust' if native else 'python', abi=1 if native else None,
                calls=_calls, contexts=len(_contexts))
