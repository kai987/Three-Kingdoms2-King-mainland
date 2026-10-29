"""Small controlled current-rule fixtures, never playable historical chapters."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile

from remake.campaign import Catalog

ROOT = Path(__file__).resolve().parents[1]


def controlled_catalog():
    data = json.loads((ROOT / 'game/data/campaigns/217-07.json').read_text())
    # Keep the actual current identities, profiles, geography and travel/hazard
    # schema. Four controlled cities isolate transactions and battle receipts.
    active = ['nanyang', 'xiangyang', 'nanjun', 'jiangxia']
    data.update(id='controlled-current-rules', start_month=11,
                title='受控規則測試', active_cities=active, city_foundings={},
                initial_owners=dict(zip(active, ['wei', 'shu', 'neutral', 'wu'])))
    data['rules']['ai_max_attacks_per_turn'] = 0
    # These small legacy fixtures isolate battle/calendar rules. Seasonal
    # disasters and autonomous town visits have their own real-campaign tests.
    data['facility_rules']['disasters_enabled'] = False
    data['facility_ai_default'] = False
    # Keep the established isolated battle/march oracles independent of the
    # weighted equipment exchanges. Real catalogs and the equipment suite use
    # actual source/signature loadouts with weighted combat enabled.
    data['equipment_rules']['combat_enabled'] = False
    data['equipment_initial'] = {person['person_id']:dict(weapon_id=0,armor_id=0,
        basis='controlled_transaction_starter') for person in data['people']}
    data['factions'] = [dict(id=key, name=key, captain=name, city=city, color='#ff0000')
        for key, name, city in [('wei', '夏侯惇', 'nanyang'), ('shu', '刘备', 'xiangyang'), ('wu', '甘宁', 'jiangxia')]]
    rows = [('san14-candidate-0124', 'nanyang', 480, True),
            ('san14-candidate-0952', 'xiangyang', 180, True),
            ('san14-candidate-0147', 'xiangyang', 180, False),
            ('san14-candidate-0005', 'xiangyang', 80, False),
            ('san14-candidate-0440', 'xiangyang', 120, False),
            ('san14-candidate-0179', 'jiangxia', 560, True),
            ('san14-candidate-0001', 'nanjun', 120, False)]
    data['initial_officers'] = [dict(person_id=p, city=c, troops=t, ruler=r) for p, c, t, r in rows]
    people = {p['person_id']: p for p in data['people']}
    data['faction_rulers'] = {side: people[pid]['runtime_id'] for side, pid in [
        ('wei', rows[0][0]), ('shu', rows[1][0]), ('wu', rows[5][0]) ]}
    data['initial_free_officers'] = []
    data['appearance_locations'] = {p: c for p, c, _, _ in rows}
    data['appearance_windows'] = {p: [] for p in people}
    data['era_assignments'] = {}
    data['initial_resources'] = dict(gold=1200, grain=3800, reserves=1200)
    data['initial_city_resources'] = {c: deepcopy(data['initial_resources']) for c in active}
    data['city_income'] = {c: dict(gold=35, grain=90, reserves=0) for c in active}
    pairs = [('nanyang', 'xiangyang'), ('xiangyang', 'nanjun'), ('nanjun', 'jiangxia')]
    data['links'] = [list(pair) for pair in pairs]
    data['travel_routes'] = [dict(id=f'controlled:{a}:{b}', **{'from': a, 'to': b},
        mode='land', terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1)
        for a, b in pairs]
    data['exploration_routes'] = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'controlled.json'
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        return Catalog(path)


def reach_battle(game):
    """Advance the real calendar and arrival handler for a queued test army."""
    marches = game.state.extension['travel']['marches']
    arrival = max(row['arrival_turn'] for row in marches)
    while game.state.turn < arrival:
        game._complete_turn(game.state)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
    game.state.phase = 'arrivals'
    game.command('arrivals', {}, game.revision)
    assert game.state.phase == 'battle'
    return game.state.battle['id']


def advance_month(game):
    """Exercise all three real ten-day services for one calendar month."""
    month = game.state.year, game.state.month
    while (game.state.year, game.state.month) == month:
        game._complete_turn(game.state)


def arrange_contact(game, battle=None, actor=None, target=None):
    """Stage a legal native-grid contact for isolated effect/receipt fixtures.

    This is explicit test setup, not a playable movement shortcut. Real march
    and battle-flow tests must issue battle_move/battle_wait. Positions remain
    authoritative and all tactical rules stay enabled; no RNG/resources change.
    """
    from remake import battle_grid
    battle = battle or game.state.battle
    actor = battle['attackers'][0] if actor is None else actor
    target = battle['defenders'][0] if target is None else target
    actor = actor['id'] if isinstance(actor, dict) else actor
    target = target['id'] if isinstance(target, dict) else target
    field = battle_grid._field(battle)
    pairs = [((x, y), (nx, ny)) for y in range(battle_grid.ROWS)
             for x in range(battle_grid.COLUMNS) if field['classes'][y][x] == 2
             for nx, ny in ((x+1, y), (x, y+1))
             if 0 <= nx < battle_grid.COLUMNS and 0 <= ny < battle_grid.ROWS
             and field['classes'][ny][nx] == 2]
    if not pairs:
        raise AssertionError('Native field has no plain contact pair for this fixture')
    first, second = pairs[0]
    positions = battle['extended']['tactical']['positions']
    positions[str(actor)] = dict(x=first[0], y=first[1])
    positions[str(target)] = dict(x=second[0], y=second[1])
    occupied = {first, second}
    for side in battle_grid.SIDES:
        for unit in battle[side]:
            if unit['id'] in (actor, target):
                continue
            key = str(unit['id'])
            point = positions[key]
            original = (point['x'], point['y'])
            if original in occupied:
                candidates = [(x, y) for y in range(battle_grid.ROWS)
                    for x in range(battle_grid.COLUMNS) if (x, y) not in occupied]
                original = min(candidates, key=lambda p: (abs(p[0]-point['x'])+abs(p[1]-point['y']), p[1], p[0]))
                positions[key] = dict(x=original[0], y=original[1])
            occupied.add(original)
    return actor, target


def arrange_tactic(game, tactic, actor=None, target=None):
    """Explicit legal native cells for one isolated, already-unlocked effect.

    Selects actual terrain cells and neighboring enemy units; it never edits
    the field, removes tactical state or bypasses command validation.
    """
    from remake import battle_grid
    battle = game.state.battle
    actor = battle['attackers'][0] if actor is None else actor
    target = battle['defenders'][0] if target is None else target
    own, actor = battle_grid._unit(battle, actor)
    foe, target = battle_grid._unit(battle, target)
    field = battle_grid._field(battle)
    ac = 4 if tactic == 9 else 5 if tactic == 13 else 0 if tactic == 11 else 2
    tc = 0 if tactic in (1, 2, 3, 7) else 3 if tactic in (4, 10, 12) else 5 if tactic == 6 else 2
    others = [u for u in battle[foe] if u['id'] != target['id']]
    neighbor_class = 3 if tactic in (10, 12) else None
    layout = None
    for y in range(battle_grid.ROWS):
        for x in range(battle_grid.COLUMNS):
            if field['classes'][y][x] != tc:
                continue
            neighbors = [(nx, ny) for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1))
                if 0 <= nx < battle_grid.COLUMNS and 0 <= ny < battle_grid.ROWS]
            for source in neighbors:
                if field['classes'][source[1]][source[0]] != ac:
                    continue
                free = [p for p in neighbors if p != source and (neighbor_class is None
                    or field['classes'][p[1]][p[0]] == neighbor_class)
                    and (tactic != 14 or field['classes'][p[1]][p[0]] != 5)]
                if len(free) >= len(others):
                    layout = source, (x, y), free
                    break
            if layout:
                break
        if layout:
            break
    if layout is None:
        raise AssertionError(f'No native legal layout for tactic{tactic} on {battle["target"]}')
    source, center, extra = layout
    positions = battle['extended']['tactical']['positions']
    occupied = set()
    for unit, point in [(actor, source), (target, center), *zip(others, extra)]:
        positions[str(unit['id'])] = dict(x=point[0], y=point[1])
        occupied.add(point)
    assigned = {actor['id'], target['id'], *(u['id'] for u in others)}
    for side in battle_grid.SIDES:
        for unit in battle[side]:
            if unit['id'] in assigned:
                continue
            point = next((x, y) for y in range(battle_grid.ROWS)
                         for x in range(battle_grid.COLUMNS) if (x, y) not in occupied)
            positions[str(unit['id'])] = dict(x=point[0], y=point[1])
            occupied.add(point)
    tactical = battle['extended']['tactical']
    tactical['side'] = own
    tactical['passed'] = {side: False for side in battle_grid.SIDES}
    tactical['points'][own] = battle_grid.point_cap(battle_grid._troops(battle, own))


def soldier_encounter_step(game, *, formation=3, orders=None):
    """Submit one real public command for a pending controlled soldier scene."""
    battle=game.state.battle
    row=(battle or {}).get('extended',{}).get('siege')
    if game.state.phase!='battle' or row is None:
        return None
    if battle['extended']['duel']:
        kind,payload='duel_action',dict(move='strike')
    elif row['stage']=='formation':
        kind,payload='siege_form',dict(formation=formation)
    elif row['stage']=='orders':
        kind,payload='siege_orders',dict(orders=orders or {key:'advance'for key in ('infantry','archer','cavalry','general')})
    else:
        kind,payload='siege_step',{}
    return game.command(kind,dict(battle_id=battle['id'],**payload),game.revision)


def finish_soldier_encounter(game, *, formation=3, orders=None, limit=260):
    """Run formation/orders/steps/duel through the real bounded public API.

    No HP, troops, damage, RNG, side or AP is injected by this driver. Any next
    AI encounter opened as the old one returns is another real pending scene.
    The caller can use this helper again; a natural200-round bound is retained.
    """
    receipts=[]
    for _ in range(limit):
        before=game.state.battle
        old=(before or {}).get('extended',{}).get('siege')
        if game.state.phase!='battle' or old is None:
            return receipts
        fingerprint=(old['actor'],old['target'],old.get('mode','siege'))
        old_round=old['round']
        receipts.append(soldier_encounter_step(game,formation=formation,orders=orders))
        new=(game.state.battle or {}).get('extended',{}).get('siege')
        if new is not None and ((new['actor'],new['target'],new.get('mode','siege'))!=fingerprint or new['round']<old_round):
            return receipts
    raise AssertionError('Real soldier encounter did not finish inside its public command bound')
