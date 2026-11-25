"""Portable compressed save state with a small, readable recovery header."""
import base64
import json
import zlib

from .economy_rules import FIELD as ECONOMY_VERSION_FIELD
from .json_boundary import loads
from .logistics_rules import FIELD as LOGISTICS_VERSION_FIELD
from .logistics_strategy import FIELD as AI_VERSION_FIELD, POLICY as AI_POLICY_FIELD
from .transport_emergency import FIELD as TRANSPORT_VERSION_FIELD, EXPERIMENT as TRANSPORT_EXPERIMENT_FIELD

MAX_STATE_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024 - 128


def header(state):
    result = {key: state[key] for key in ('seed', 'player', 'year', 'month', 'day', 'turn', 'phase')}
    result['extension'] = {key: state['extension'][key] for key in ('campaign_id', 'difficulty', 'lifespan', ECONOMY_VERSION_FIELD, LOGISTICS_VERSION_FIELD, AI_VERSION_FIELD, AI_POLICY_FIELD,
                               TRANSPORT_VERSION_FIELD, TRANSPORT_EXPERIMENT_FIELD)
                           if key in state['extension']}
    return result


def pack(content):
    state = content['state']
    raw = json.dumps(state, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_STATE_BYTES:
        raise ValueError('Save state too large')
    data = base64.b64encode(zlib.compress(raw, 1)).decode('ascii')
    return dict(content, version=3, state=header(state), deflate=data)


def unpack(content):
    if not isinstance(content['deflate'], str) or len(content['deflate']) > MAX_FILE_BYTES:
        raise ValueError('Invalid compressed save')
    packed = base64.b64decode(content['deflate'], validate=True)
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(packed, MAX_STATE_BYTES + 1)
    except zlib.error as exc:
        raise ValueError('Invalid compressed state') from exc
    if len(raw) > MAX_STATE_BYTES or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid compressed state length')
    state = loads(raw)
    if not isinstance(state, dict) or header(state) != content['state']:
        raise ValueError('Invalid recovery header')
    return {**{k: v for k, v in content.items() if k != 'deflate'}, 'version': 2, 'state': state}
