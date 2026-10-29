"""Controlled current-catalog soldier and battlefield-service UI acceptance.

This is deliberately not a historical opening or a natural AI playthrough.
The real new/allocate commands and battle initializer supply the armies. Only
legal tactical/piece positions, a wounded support HP and a documented starting
seed are arranged to expose contact, villages, conversion and occupation.
Every exported fixture must round-trip through the unchanged production loader.
The browser imports its checksummed JSON through the visible save-file control;
no page-global campaign state is injected.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog
from remake import battle_grid
from remake.officers import recruitment_loyalty


def _base(seed=20261029):
    game = Campaign(Catalog(ROOT / 'game/data/campaigns/208-10.json'))
    game.command('new', dict(faction='wei', seed=seed), game.revision)
    city = game.state.cities['jiujiang']
    ranked = sorted(city.roster.officer_ids,
                    key=lambda ident: (-game.state.officers[ident].profile.martial_strength, ident))
    actor = ranked[0]
    strategist = max(city.roster.officer_ids,
                     key=lambda ident: (game.state.officers[ident].profile.intellect, -ident))
    ids = list(dict.fromkeys([actor, strategist, *ranked]))[:10]
    game.command('allocate', dict(city=city.id, officer=actor, troops=1000), game.revision)
    state = game.state
    game._start_expanded_battle(state, state.cities['jiujiang'], state.cities['danyang'], ids)
    state.phase = 'battle'
    return game, actor, strategist


def _positions(game, moves, *, leave_camp_empty=False):
    """Arrange explicit cells and rehome only any collided fixture bystanders."""
    battle = game.state.battle
    positions = battle['extended']['tactical']['positions']
    points = {str(ident): dict(x=point[0], y=point[1]) for ident, point in moves.items()}
    used = {(point['x'], point['y']) for point in points.values()}
    forbidden = {battle_grid._field(battle)['camp']} if leave_camp_empty else set()
    for key, old in positions.items():
        if key in points:
            continue
        point = old['x'], old['y']
        if point in used or point in forbidden:
            point = next((x, y) for y in range(battle_grid.ROWS)
                         for x in range(battle_grid.COLUMNS)
                         if (x, y) not in used | forbidden)
        points[key] = dict(x=point[0], y=point[1])
        used.add(point)
    positions.update(points)


def _contact(game, actor, target):
    battle = game.state.battle
    field = battle_grid._field(battle)
    occupied = {(p['x'], p['y']) for key, p in battle['extended']['tactical']['positions'].items()
                if key not in {str(actor), str(target)}}
    sites = {(p['x'], p['y']) for p in field['services']} | {field['camp']}
    candidates = sorted(((x, y) for y in range(1, battle_grid.ROWS - 1)
                         for x in range(1, battle_grid.COLUMNS - 1)),
                        key=lambda point: (abs(point[0] - 15) + abs(point[1] - 9), point[1], point[0]))
    first, second = next(((x, y), (x+1, y)) for x, y in candidates
        if (x, y) not in occupied | sites and (x+1, y) not in occupied | sites
        and field['classes'][y][x] != 5 and field['classes'][y][x+1] != 5)
    _positions(game, {actor: first, target: second})
    return first, second


def _save(game, **metadata):
    game.validate(game.state)
    saved = game.export_save()
    other = Campaign(game.catalog)
    other.load_save(saved, other.revision)
    assert other.export_save() == saved
    return dict(save=saved, controlled=True, **metadata)


def field_fixture():
    game, actor, _ = _base()
    target = game.state.battle['defenders'][0]['id']
    first, second = _contact(game, actor, target)
    return _save(game, actor=actor, target=target,
        actor_cell=dict(x=first[0], y=first[1]), target_cell=dict(x=second[0], y=second[1]))


def contact_fixture():
    game, actor, _ = _base()
    battle = game.state.battle
    target = battle['defenders'][0]['id']
    _contact(game, actor, target)
    game.command('attack', dict(battle_id=battle['id'], actor=actor, target=target), game.revision)
    game.command('siege_form', dict(battle_id=battle['id'], formation=3), game.revision)
    row = game.state.battle['extended']['siege']
    assert row['mode'] == 'field'
    friendly = [piece for piece in row['units'] if piece['side'] == 'attackers']
    enemies = [piece for piece in row['units'] if piece['side'] == 'defenders' and piece['kind'] != 'general']
    by_kind = {kind: next(piece for piece in friendly if piece['kind'] == kind)
               for kind in ('infantry', 'archer', 'cavalry', 'general')}
    assert len(enemies) >= 3
    arranged = {by_kind['general']['id']: (0, 0),
        by_kind['infantry']['id']: (5, 5), by_kind['archer']['id']: (3, 3),
        by_kind['cavalry']['id']: (3, 7), enemies[0]['id']: (6, 5),
        enemies[1]['id']: (6, 3), enemies[2]['id']: (4, 7)}
    opposing_general = next(p for p in row['units'] if p['side'] == 'defenders' and p['kind'] == 'general')
    arranged[opposing_general['id']] = (15, 9)
    occupied = set(arranged.values())
    for piece in row['units']:
        point = arranged.get(piece['id'])
        if point is None:
            point = next((x, y) for y in range(10) for x in range(16) if (x, y) not in occupied)
        piece['x'], piece['y'] = point
        occupied.add(point)
    # Advance the three contact kinds, hold all other individual soldiers.
    row['piece_orders']['attackers'] = {p['id']: ('advance' if p['id'] in {
        by_kind[kind]['id'] for kind in ('infantry', 'archer', 'cavalry')} else 'wait')
        for p in friendly}
    return _save(game, actor=actor, target=target,
        contact_pieces={kind: piece['id'] for kind, piece in by_kind.items()})


def conversion_fixture():
    # Search actual starting seeds using real tactic commands on separate
    # reference games. Only the successful pre-command save is exported.
    for seed in range(1, 41):
        game, _, actor = _base(seed)
        battle = game.state.battle
        target = min(battle['defenders'], key=lambda unit: game.state.officers[unit['id']].loyalty)['id']
        _contact(game, actor, target)
        before = _save(game, actor=actor, target=target)
        candidate = Campaign(game.catalog)
        candidate.load_save(before['save'], candidate.revision)
        candidate.command('tactic', dict(battle_id=battle['id'], actor=actor, target=target, tactic=8), candidate.revision)
        if candidate.state.officers[target].faction_id != 'wei':
            continue
        leader = game.state.extension['leaders']['wei']
        virtue = game.state.officers[leader].profile.virtue
        before.update(expected_loyalty=recruitment_loyalty(virtue, game.state.officers[target].loyalty),
                      leader_virtue=virtue, selected_seed=seed,
                      target_troops=next(u['troops'] for u in battle['defenders'] if u['id'] == target))
        assert len(candidate.state.battle['attackers']) == 11
        assert len(candidate.state.battle['defenders']) == 9
        return before
    raise AssertionError('No controlled starting seed produced an immediate legal battlefield conversion')


def occupation_fixture():
    game, actor, _ = _base()
    battle = game.state.battle
    x, y = battle_grid._field(battle)['camp']
    defending = battle['defenders'][0]['id']
    _positions(game, {actor: (x-1, y), defending: (0, 0)}, leave_camp_empty=True)
    quote = battle_grid.move_quote(game, game.state, battle, actor, x, y)
    assert quote['cost'] > 0
    return _save(game, actor=actor, cell=dict(x=x, y=y), cost=quote['cost'])


def facility_fixtures():
    results = {}
    for kind in ('hospital', 'market', 'armory'):
        game, actor, _ = _base()
        battle = game.state.battle
        site = next(service for service in battle_grid._field(battle)['services'] if service['kind'] == kind)
        _positions(game, {actor: (site['x'], site['y'])})
        if kind == 'hospital':
            battle['extended']['support'][str(actor)]['health'] = 10
        board = battle_grid.view(game, game.state, battle)
        offer = board['actors'][str(actor)]['facility']
        assert offer and offer['kind'] == kind
        results[kind] = _save(game, actor=actor, site=site, offer=offer)
    return results


def fixture(kind='field'):
    return {'field': field_fixture, 'contact': contact_fixture,
            'conversion': conversion_fixture, 'occupation': occupation_fixture,
            'facilities': facility_fixtures}[kind]()


if __name__ == '__main__':
    print(json.dumps(fixture(sys.argv[1] if len(sys.argv) > 1 else 'field'),
                     ensure_ascii=False, separators=(',', ':')))
