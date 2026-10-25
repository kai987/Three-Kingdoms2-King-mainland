"""Controlled scenario inputs for real calendar/transaction/browser acceptance.

No state or save is injected. Identities, art, profiles and the engine are the
published implementation; only the initial scenario date and holdings differ.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile

from remake.campaign import Catalog
from campaign_fixtures import controlled_catalog

ROOT = Path(__file__).resolve().parents[1]
SONG = 'historical-song-jian'
BEIGONG = 'historical-beigong-boyu'
LI = 'historical-li-wenhou'
BIAN = 'historical-bian-zhang'
HAN = 'san14-candidate-0166'


def dated_catalog(kind='founding'):
    if kind in ('founding','coup'):
        data = json.loads((ROOT/'game/data/campaigns/184-02.json').read_text())
        data.update(id='controlled-liangzhou-184-10', start_month=10,
                    title='涼州起兵驗收', active_cities=['henan','jincheng','tianshui','longxi'], city_foundings={})
        sides = {'han','bian_zhang','song_jian'}
        data['factions'] = [row for row in data['factions'] if row['id'] in sides]
        data['faction_rulers'] = {k:v for k,v in data['faction_rulers'].items() if k in sides}
        ruler = next(row for row in data['initial_officers'] if row['ruler'] and row['city']=='henan')
        data['initial_officers'] = [ruler]
        data['initial_free_officers'] = [row for row in data['initial_free_officers']
                                         if row['person_id'] in {SONG,BIAN,BEIGONG,LI,HAN}]
        data['initial_owners'] = dict(henan='han', jincheng='neutral', tianshui='neutral', longxi='neutral')
        if kind=='coup':
            data.update(id='controlled-han-sui-186-11',start_year=186,start_month=11,
                        title='韓遂自立驗收',faction_foundings=[],historical_exit_dates={})
            data['factions']=[{k:v for k,v in r.items() if k!='available_from'}
                              for r in data['factions'] if r['id']!='song_jian']
            data['faction_rulers'].pop('song_jian')
            data['initial_owners'].update(jincheng='bian_zhang',tianshui='bian_zhang')
            data['initial_free_officers']=[]
            data['initial_officers'] += [dict(person_id=p,city='jincheng',troops=300,
                ruler=p==BIAN,resolve_death_year=p in (BIAN,BEIGONG,LI)) for p in (BIAN,BEIGONG,LI,HAN)]
        data['appearance_windows'] = {p['person_id']:[] for p in data['people']}
        data['appearance_locations'] = {r['person_id']:r['city']
            for r in data['initial_officers']+data['initial_free_officers']}
        data['links'] = []; data['travel_routes'] = []; data['exploration_routes'] = []
    elif kind == 'retirement':
        data = deepcopy(controlled_catalog().data)
        data.update(id='controlled-song-jian-214-09', start_year=214, start_month=9,
                    title='宋建壽命與繼承驗收')
        data['initial_officers'] = [dict(r, ruler=False if r['city']=='xiangyang' else r['ruler'])
            for r in data['initial_officers'] if r['person_id']!='san14-candidate-0001']
        data['initial_officers'].append(dict(person_id=SONG, city='xiangyang', troops=300,
                                            ruler=True, resolve_death_year=True))
        data['faction_rulers']['shu'] = 1024
        next(r for r in data['factions'] if r['id']=='shu').update(captain='宋建',name='宋建势力')
        data['era_assignments'][SONG] = dict(status='serving', faction='shu', city='xiangyang')
        data['historical_exit_dates'] = {SONG:[214,10]}
        data['appearance_locations'][SONG] = 'xiangyang'
    else:
        raise ValueError('Unknown controlled dated scenario')
    data['rules']['ai_max_attacks_per_turn'] = 0
    data['facility_rules']['disasters_enabled'] = False
    data['facility_ai_default'] = False
    data['city_income'] = {c:dict(gold=0,grain=0,reserves=0) for c in data['active_cities']}
    data['initial_city_resources'] = {c:dict(gold=1200,grain=3800,reserves=1200)
                                      for c in data['active_cities']}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'dated.json'
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
        return Catalog(path)
