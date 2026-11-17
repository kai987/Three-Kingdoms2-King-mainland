"""Export a Shu opening with an empty transit depot and a stocked bypass."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake.march_supply import cost
from remake.route_hazards import evaluate_leg, route_allowed
from remake.march_core import using_backend


def fixture():
    catalog = Catalog(ROOT / 'game/data/campaigns/217-07.json')
    game = Campaign(catalog)
    game.command('new', dict(faction='shu', seed=2026), game.revision)
    state = game.state
    state.cities['guanghan'].grain = 0
    primary = game._travel_path(state, 'shujun', 'nanjun', 'shu', 'fastest')
    assert primary['days'] == 45 and primary['path'][1] == 'guanghan'
    assert state.cities['guanghan'].owner == 'shu'
    assert 370 in state.cities['shujun'].roster.officer_ids

    # The existing road network offers this 56-day route with enough grain
    # for each leg even when rounded without the previous leg's ration credit.
    detour = ('shujun', 'qianwei', 'jiangyang', 'bajun', 'fuling', 'badong', 'nanjun')
    route_ids = ('shujun:qianwei:river', 'jiangyang:qianwei:land', 'jiangyang:bajun:river',
                 'bajun:fuling:river', 'fuling:badong:river', 'badong:nanjun:river')
    by_id = {row['id']: row for row in game._known_routes(state)}
    days = 0
    for source, target, route_id in zip(detour, detour[1:], route_ids):
        route = by_id[route_id]
        assert route_allowed(catalog.data, route, source, target)
        leg = evaluate_leg(catalog.data, route, source, target, state.month)
        assert state.cities[source].owner == 'shu'
        assert state.cities[source].grain >= cost(state.officers[370].troops, 1, leg['days'])
        days += leg['days']
    assert days == 56

    save = game.export_save()
    restored = Campaign(catalog)
    restored.load_save(save, restored.revision)
    assert restored.export_save() == save
    return save


if __name__ == '__main__':
    with using_backend('python'):
        print(json.dumps(fixture(), ensure_ascii=False, separators=(',', ':')))
