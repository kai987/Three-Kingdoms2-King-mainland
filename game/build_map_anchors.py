#!/usr/bin/env python3
"""Rebuild the approved map hit areas from the canonical map source."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def build():
    source = json.loads((ROOT / 'game/config/map-source.json').read_text(encoding='utf-8'))
    if source.get('schema') != 'tk2-map-source-v1':
        raise ValueError('Unknown approved map source')
    expected = source['approved_asset_sha256']['map.png']
    if hashlib.sha256((ROOT / 'game/assets/map.png').read_bytes()).hexdigest() != expected:
        raise ValueError('Approved map pixels changed')
    result = source['anchors']
    if result['map_sha256'] != expected:
        raise ValueError('Hit areas refer to different map pixels')
    if len(result['positions']) != 96 or any(not (0 <= x < 1352 and 0 <= y < 1024) for x, y in result['positions'].values()):
        raise ValueError('Invalid approved base-map registration')
    (ROOT / 'game/assets/city-positions.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    build()
