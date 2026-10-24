"""Record the 37 reviewed remake icons, without touching their generated sources."""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source'))
from remake.facility_equipment import WEAPONS, ARMORS


def build():
    assets = []
    for slot, rows in (('weapon', WEAPONS), ('armor', ARMORS)):
        for row in rows:
            name = f'{slot}-{row["id"]}'
            source = ROOT / 'art/equipment-icons-v1' / f'{name}-source.png'
            target = ROOT / 'game/assets/equipment-icons' / f'{name}.png'
            raw = target.read_bytes()
            if raw[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', raw[16:24]) != (128, 128):
                raise ValueError(f'Expected reviewed 128x128 PNG: {target}')
            assets.append(dict(slot=slot, item=row['id'], name_tc=row['name_tc'],
                name_ja=row['name_ja'], path='/' + str(target.relative_to(ROOT / 'game')),
                width=128, height=128, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                source_file=str(source.relative_to(ROOT)),
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    if len({row['sha256'] for row in assets}) != len(assets):
        raise ValueError('Equipment icons must not alias another item image')
    return dict(schema='tk2-equipment-icons-v1', provenance='remake-equipment-icon',
                generator='built-in-imagegen',
                note='Individual remake pixel icons; not verified original-game item exports. Generated originals and exact prompts are retained separately.',
                prompt_records='art/equipment-icons-v1', assets=assets)


if __name__ == '__main__':
    encoded = json.dumps(build(), ensure_ascii=False, indent=2) + '\n'
    destination = ROOT / 'game/assets/equipment-icons/index.json'
    if '--check' in sys.argv:
        if destination.read_text() != encoded:
            raise SystemExit('Equipment icon manifest is stale')
    else:
        destination.write_text(encoded)
