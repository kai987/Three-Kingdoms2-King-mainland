"""Batch jobs on the native Rust library or the campaign Worker's WASM instance."""
import json

from . import march_core

_web_call = None
_web_catalog = None
_web_context = None


def install_web(call):
    global _web_call
    _web_call = call


def enabled():
    return _web_call is not None or march_core.enabled()


def _web_request(**payload):
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    reply = json.loads(_web_call(raw))
    if not reply['ok']:
        raise ValueError(reply['error'])
    return reply['value']


def invoke(op, *, data=None, **payload):
    global _web_catalog, _web_context
    if _web_call is None:
        return march_core.invoke(op, data=data, **payload)
    if data is not None:
        if data is not _web_catalog:
            if _web_context is not None:
                _web_request(op='unregister', context=_web_context)
                _web_catalog = _web_context = None
            _web_context = _web_request(op='register', data=march_core.config_for(data))
            _web_catalog = data
        payload['context'] = _web_context
    return _web_request(op=op, **payload)


def routes(game, state, owner, pairs, *, excluded=()):
    from . import winter_weather
    if winter_weather.movement(state):
        engine=game
        if excluded:
            from copy import copy
            denied=frozenset(excluded)
            engine=copy(game)
            engine.catalog=copy(game.catalog)
            engine.catalog.data={**game.catalog.data, **{
                key:[row for row in game.catalog.data.get(key,()) if row['id'] not in denied]
                for key in ('travel_routes','exploration_routes')}}
        return engine._python_supply_paths(state, owner, pairs)
    return invoke('strategic_routes', data=game.catalog.data, **march_core.state_input(state, owner),
                  owner=owner, pairs=pairs, excluded=excluded)
