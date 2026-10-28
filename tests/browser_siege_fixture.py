"""An explicit legal castle-contact save for UI acceptance, not a historical opening.

Use the shipped catalog, actual allocation command and battle initializer. Only
the pending attacker's contact cell is arranged to exercise the castle page
without waiting for an AI commander to choose to stay in its fort. The browser
imports the checksummed save through the normal visible file picker.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake import battle_grid


def fixture():
    game = Campaign(Catalog(ROOT / 'game/data/campaigns/208-10.json'))
    game.command('new', dict(faction='wei', seed=2026), game.revision)
    state = game.state
    source, target = state.cities['jiujiang'], state.cities['danyang']
    ids = sorted(source.roster.officer_ids,
                 key=lambda ident: (-state.officers[ident].profile.martial_strength, ident))[:10]
    actor = ids[0]
    game.command('allocate', dict(city=source.id, officer=actor, troops=999), game.revision)
    state = game.state
    source, target = state.cities['jiujiang'], state.cities['danyang']
    game._start_expanded_battle(state, source, target, ids)
    state.phase = 'battle'
    battle = state.battle
    fort = battle['defenders'][0]['id']
    x, y = battle_grid._field(battle)['camp']
    positions = battle['extended']['tactical']['positions']
    occupied = {(point['x'], point['y']) for ident, point in positions.items() if ident != str(actor)}
    adjacent = next((nx, ny) for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1))
                    if 0 <= nx < 31 and 0 <= ny < 19 and (nx, ny) not in occupied)
    positions[str(actor)] = dict(x=adjacent[0], y=adjacent[1])
    saved = game.export_save()
    # The ordinary production loader must accept the fixture unchanged.
    reference = Campaign(game.catalog)
    reference.load_save(saved, reference.revision)
    assert reference.export_save() == saved
    return dict(save=saved, actor=actor, fort=fort, cell=dict(x=x, y=y),
                map_id=battle['extended']['tactical']['map_id'])


if __name__ == '__main__':
    print(json.dumps(fixture(), ensure_ascii=False, separators=(',', ':')))
