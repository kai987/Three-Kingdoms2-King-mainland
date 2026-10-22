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
