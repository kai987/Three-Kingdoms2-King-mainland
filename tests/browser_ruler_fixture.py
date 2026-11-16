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


def at_large_fixture():
    game = Campaign(Catalog(ROOT / 'game/data/campaigns/249-01.json'))
    game.command('new', dict(faction='wu', seed=2026), game.revision)
    state = game.state
    while (state.year, state.month, state.day) < (252, 3, 21):
        game._complete_turn(state)
        game._reconcile_factions(state)
    game.command('end_turn', {}, game.revision)
    state = game.state
    # Resume at the end of the AI queue, just before the real monthly boundary.
    state.extension.update(ai_queue=['henan'], ai_cursor=1)
    before = game.export_save()
    game.command('ai', dict(turn=state.turn), game.revision)
    state = game.state
    pending = state.extension['pending_succession']['wu']
    offer = pending['recruit']
    heir, previous, city = offer['officer'], pending['previous'], offer['city']
    assert state.officers[heir].person_id == 'san14-candidate-0578'
    assert state.officers[previous].person_id == 'san14-candidate-0553'
    saved = game.export_save()
    clone = Campaign(game.catalog)
    clone.load_save(saved, clone.revision)
    assert clone.export_save() == saved
    return dict(before=before, save=saved, officer=heir, previous=previous, city=city,
                officer_name=game.person_name(state, heir),
                previous_name=game.person_name(state, previous))


if __name__ == '__main__':
    build = at_large_fixture if sys.argv[1:] == ['--at-large'] else fixture
    print(json.dumps(build(), ensure_ascii=False, separators=(',', ':')))
