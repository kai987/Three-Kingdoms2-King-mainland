"""Use the shipped 208 scenario and real arrival/settlement services for UI QA.

The strategic fixture starts with five Liu Bei officers headed to Changsha.
The combat fixtures use the grouped arrivals, with the first player officer
placed next to the empty fort in the final fixture to reach capture quickly.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import battle_grid
from remake.campaign import Campaign, Catalog
from campaign_fixtures import confirm_default_placement


def fixture():
    game = Campaign(Catalog(ROOT / 'game/data/campaigns/208-10.json'))
    game.command('new', dict(faction='wu', seed=2026), game.revision)
    state = game.state
    own, allied, target = (state.cities[city] for city in ('luling', 'jiangxia', 'changsha'))
    def officers(city):
        return [ident for ident in city.roster.officer_ids if state.officers[ident].troops > 0][:5]

    first, second = officers(own), officers(allied)
    assert len(first) == len(second) == 5
    game._queue_march(state, allied, target, second, 'attack')
    opening = game.export_save()
    game.command('depart', dict(source=own.id, target=target.id, officers=first,
        route_mode='fastest', battle_grain=200), game.revision)
    for _ in range(6):
        game._complete_turn(game.state)
        if game.state.phase == 'arrivals':
            game.command('arrivals', {}, game.revision)
        if game.state.battle:
            break
    state = game.state
    assert state.phase == 'battle' and len(state.battle['attackers']) == 10
    assert game.view()['catalog']['battle_tactical']['placement']['total'] == 5
    placement = game.export_save()
    confirm_default_placement(game)
    state, actor = game.state, first[0]
    battle = state.battle
    camp = battle_grid._field(battle)['camp']
    points = battle['extended']['tactical']['positions']
    occupant = next((ident for ident, p in points.items() if (p['x'], p['y']) == camp), None)
    if occupant is not None:
        points[occupant] = points[str(actor)].copy()
    neighbors = [(camp[0] - 1, camp[1]), (camp[0] + 1, camp[1]),
                 (camp[0], camp[1] - 1), (camp[0], camp[1] + 1)]
    blocked = {(p['x'], p['y']) for ident, p in points.items() if ident != str(actor)}
    for x, y in neighbors:
        if not (0 <= x < 31 and 0 <= y < 19) or (x, y) in blocked:
            continue
        points[str(actor)] = dict(x=x, y=y)
        moves = game.view()['catalog']['battle_tactical']['actors'][str(actor)]['reachable']
        if any((p['x'], p['y']) == camp for p in moves):
            break
    else:
        raise AssertionError('No legal approach to Changsha fort')
    capture = game.export_save()
    clone = Campaign(game.catalog)
    for save in (opening, placement, capture):
        clone.load_save(save, clone.revision)
        assert clone.export_save() == save
    clone.command('battle_move', dict(battle_id=battle['id'], actor=actor, x=camp[0], y=camp[1]), clone.revision)
    assert clone.state.battle['extended']['occupation']['actor'] == actor
    clone.command('settle', dict(battle_id=battle['id']), clone.revision)
    assert clone.state.cities[target.id].owner == own.owner
    return dict(opening=opening, placement=placement, capture=capture, camp=camp,
                source=own.id, target=target.id, first=first, second=second, actor=actor)


if __name__ == '__main__':
    print(json.dumps(fixture(), ensure_ascii=False, separators=(',', ':')))
