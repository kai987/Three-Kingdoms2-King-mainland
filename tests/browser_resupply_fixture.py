"""Isolated real HTTP/UI fixture for daily supply and courier acceptance.

Only the scenario input is controlled. The public server, transaction handlers,
calendar, AI, starvation, logistics, saves and frontend remain production code.
No live campaign or browser state is injected or modified by the fixture.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests'), str(ROOT / 'game')]
from campaign_fixtures import controlled_catalog
from remake.campaign import Catalog
from remake.session import CampaignSession as RealSession
import remake.session as sessions


def resupply_catalog():
    data = deepcopy(controlled_catalog().data)
    original = data['initial_officers']
    source = [dict(row, city='nanyang') for row in original if row['city'] == 'xiangyang'][:3]
    warehouse = [dict(row, city='jiangxia', ruler=False) for row in original
                 if row['city'] in ('xiangyang', 'jiangxia', 'nanjun')
                 and row['person_id'] not in {person['person_id'] for person in source}]
    enemy = [dict(row, city='xiangyang') for row in original if row['city'] == 'nanyang']
    assert len(source) == len(warehouse) == 3 and len(enemy) == 1
    active = ['nanyang', 'nanjun', 'jiangxia', 'bajun', 'xiangyang']
    data.update(id='controlled-segment-resupply', title='受控補給驗收', active_cities=active,
                initial_owners={city: 'wei' if city == 'xiangyang' else 'shu' for city in active},
                city_foundings={}, initial_officers=[*source, *warehouse, *enemy])
    by_person = {row['person_id']: row for row in data['people']}
    rulers = {'shu': source[0], 'wei': enemy[0]}
    data['factions'] = [dict(id=side, name=side, captain=by_person[row['person_id']]['name'],
        city=row['city'], color='#00a000' if side == 'shu' else '#ff0000')
        for side, row in rulers.items()]
    data['faction_rulers'] = {side: by_person[row['person_id']]['runtime_id'] for side, row in rulers.items()}
    data['appearance_locations'] = {row['person_id']: row['city'] for row in data['initial_officers']}
    data['initial_city_resources'] = {city: dict(gold=0, grain=0, reserves=0) for city in active}
    data['initial_city_resources']['nanyang'] = dict(gold=100, grain=100, reserves=0)
    data['initial_city_resources']['jiangxia'] = dict(gold=100, grain=1000, reserves=0)
    data['city_income'] = {city: dict(gold=0, grain=0, reserves=0) for city in active}
    routes = [('nanyang', 'nanjun', 10), ('nanjun', 'bajun', 20), ('jiangxia', 'nanjun', 2)]
    data['links'] = [[a, b] for a, b, days in routes]
    data['travel_routes'] = [dict(id=f'fixture:{a}:{b}', **{'from': a, 'to': b},
        mode='land', terrain='plain', distance_km=30 * days, land_km=30 * days,
        sea_km=0, days=days) for a, b, days in routes]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'resupply.json'
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        return Catalog(path)


def main():
    import serve
    catalog = resupply_catalog()

    def fixture_session(paths):
        with patch.object(sessions, 'Catalog', return_value=catalog):
            return RealSession([ROOT / 'controlled-resupply.json'])

    sessions.CampaignSession = fixture_session
    serve.main()


if __name__ == '__main__':
    main()
