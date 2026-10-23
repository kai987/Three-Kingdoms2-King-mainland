"""Attest unchanged compiler inputs across unrelated browser UI changes.

The frozen route compiler evaluates exactly the app slice below. Its full-file
pin and every other geometry source retain exact SHA validation. The one app
exception accepts only a reviewed baseline projection, never a new projection.
"""
from hashlib import sha256
import json
from pathlib import Path
import re


APP_SOURCE = 'game/app.js'
COMPILER_SOURCE = 'game/build_route_geometry.cjs'
ATTESTATION_PATH = 'game/config/route-render-source.json'
START = 'function smoothMapPath('
END = 'function mapBackgroundHref('
FIELDS = frozenset(('schema', 'source', 'original_source_sha256', 'compiler',
                    'compiler_sha256', 'start', 'end', 'projection_sha256',
                    'projection_bytes', 'baseline_commit'))
HASH = re.compile(r'[0-9a-f]{64}')


def renderer_projection(source):
    """Use the frozen compiler's exact byte range, with unambiguous bounds."""
    if not isinstance(source, bytes):
        raise ValueError('Renderer source must be bytes')
    source.decode('utf-8')
    start, end = START.encode(), END.encode()
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError('Renderer projection markers must occur exactly once')
    first, last = source.index(start), source.index(end)
    if first >= last:
        raise ValueError('Renderer projection markers are out of order')
    return source[first:last]


def validate_app_projection(source, original_pin, compiler_pin, attestation):
    """Fail closed on stale baselines or any compiler-extracted byte change."""
    if (not isinstance(attestation, dict) or set(attestation) != FIELDS
            or attestation.get('schema') != 'tk2-route-render-source-v1'
            or attestation.get('source') != APP_SOURCE
            or attestation.get('compiler') != COMPILER_SOURCE
            or attestation.get('start') != START or attestation.get('end') != END
            or not isinstance(original_pin, str) or not HASH.fullmatch(original_pin)
            or not isinstance(compiler_pin, str) or not HASH.fullmatch(compiler_pin)
            or attestation.get('original_source_sha256') != original_pin
            or attestation.get('compiler_sha256') != compiler_pin
            or not isinstance(attestation.get('projection_sha256'), str)
            or not HASH.fullmatch(attestation['projection_sha256'])
            or type(attestation.get('projection_bytes')) is not int
            or attestation['projection_bytes'] <= 0
            or not isinstance(attestation.get('baseline_commit'), str)
            or not re.fullmatch(r'[0-9a-f]{40}', attestation['baseline_commit'])):
        raise ValueError('Invalid route renderer source attestation')
    projection = renderer_projection(source)
    if (len(projection) != attestation['projection_bytes']
            or sha256(projection).hexdigest() != attestation['projection_sha256']):
        raise ValueError('Rendered timing geometry source differs: ' + APP_SOURCE)


def validate_geometry_sources(root, sources):
    """Retain full pins except for an explicitly attested app-only change."""
    root = Path(root)
    for name, expected in sources.items():
        source = (root / name).read_bytes()
        if sha256(source).hexdigest() == expected:
            continue
        if name != APP_SOURCE:
            raise ValueError('Rendered timing geometry source differs: ' + name)
        attestation = json.loads((root / ATTESTATION_PATH).read_text(encoding='utf-8'))
        validate_app_projection(source, expected, sources.get(COMPILER_SOURCE), attestation)
