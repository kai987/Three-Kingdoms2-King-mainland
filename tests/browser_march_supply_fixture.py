"""Export a real Shu opening with an empty transit depot for browser QA."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake.march_core import using_backend


def fixture():
    catalog = Catalog(ROOT / 'game/data/campaigns/217-07.json')
    game = Campaign(catalog)
    game.command('new', dict(faction='shu', seed=2026), game.revision)
    state = game.state
    state.cities['guanghan'].grain = 0
    path = game._travel_path(state, 'shujun', 'nanjun', 'shu', 'fastest')['path']
    assert path[1] == 'guanghan' and state.cities[path[1]].owner == 'shu'
    assert 370 in state.cities['shujun'].roster.officer_ids

    save = game.export_save()
    restored = Campaign(catalog)
    restored.load_save(save, restored.revision)
    assert restored.export_save() == save
    return save


if __name__ == '__main__':
    with using_backend('python'):
        print(json.dumps(fixture(), ensure_ascii=False, separators=(',', ':')))
