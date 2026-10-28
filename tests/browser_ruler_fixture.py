"""A controlled current-catalog pending succession for visible browser acceptance.

Use the real 217 catalog and normal successor command. The predecessor's death
is arranged explicitly to reach this boundary without simulating years of AI;
this is not a historical claim or a production shortcut. The checksummed save
must load unchanged through the production loader before the browser imports it.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog


def fixture():
    game = Campaign(Catalog(ROOT / 'game/data/campaigns/217-07.json'))
    game.command('new', dict(faction='shu', seed=2026), game.revision)
    state = game.state
    previous = state.extension['leaders']['shu']
    officer = state.officers[previous]
    city = next(c for c in state.cities.values() if previous in c.roster.officer_ids)
    city.roster.officer_ids.remove(previous)
    city.reserves += officer.troops
    officer.troops = 0
    officer.alive = False
    officer.faction_id = None
    officer.loyalty = 0
    game._reconcile_factions(state)
    selected = next(ident for ident in state.extension['pending_succession']['shu']['candidates']
                    if game.person_name(state, ident) == '关羽')
    original = game.catalog.by_id[previous]
    saved = game.export_save()
    clone = Campaign(game.catalog)
    clone.load_save(saved, clone.revision)
    assert clone.export_save() == saved
    return dict(save=saved, owner='shu', city='shujun',
                previous=dict(id=previous, name=original['name'], person_id=original['person_id']),
                selected=dict(id=selected, name=game.person_name(state, selected),
                              person_id=state.officers[selected].person_id))


if __name__ == '__main__':
    print(json.dumps(fixture(), ensure_ascii=False, separators=(',', ':')))
