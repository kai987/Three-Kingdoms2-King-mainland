#!/usr/bin/env python3
"""Rebuild approved city labels and native castle masks without repainting."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def build():
    source = json.loads((ROOT / 'game/config/map-source.json').read_text(encoding='utf-8'))
    if source.get('schema') != 'tk2-map-source-v1':
        raise ValueError('Unknown approved map source')
    for name, expected in source['approved_asset_sha256'].items():
        if Path(name).name != name or Path(name).suffix != '.png':
            raise ValueError('Invalid approved map asset name')
        if hashlib.sha256((ROOT / 'game/assets' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Approved map pixels changed: ' + name)
    result = source['presentation']
    rows = source['native_castle_sprite']['rows']
    for field, color in (('castle_fill_pixels', 6), ('castle_outline_pixels', 2)):
        expected = [[x*4-16, y*4-16] for y, row in enumerate(rows) for x, value in enumerate(row) if value == color]
        if result[field] != expected:
            raise ValueError('Approved castle mask differs from native source rows')
    if result['background_sha256'] != source['approved_asset_sha256']['map-basin.png'] or result['campaign_background_sha256'] != source['approved_asset_sha256']['map-campaign.png']:
        raise ValueError('Presentation refers to different map pixels')
    (ROOT / 'game/assets/map-presentation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    build()
