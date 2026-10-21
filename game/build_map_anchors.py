#!/usr/bin/env python3
"""Register Web hit areas against the actual approved v42 rendered castles.

The earlier iconLayout array predates several manual northwest/northern moves.
The v42 renderer uses cities.displayArtX/Y and crops136px from the left.
"""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]


def build():
    plan=json.loads((ROOT/'expansion/map/city-map-city-sea-plan-v42.json').read_text())
    positions={c['key']:[c['displayArtX']-136,c['displayArtY']] for c in plan['cities']}
    if len(positions)!=96 or any(not (0<=x<1352 and 0<=y<1024) for x,y in positions.values()):
        raise ValueError('Invalid rendered city registration')
    result={'schema':'rendered-v42-city-positions-v1',
        'map_sha256':hashlib.sha256((ROOT/'game/assets/map.png').read_bytes()).hexdigest(),
        'source':'expansion/map/city-map-city-sea-plan-v42.json displayArtX/displayArtY; crop x136',
        'positions':positions}
    (ROOT/'game/assets/city-positions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':build()
