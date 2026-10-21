"""Reviewed territory, roster preservation and unique legacy date upgrades."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign, Catalog
from remake.session import CampaignSession


class UnifiedCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((ROOT/'game/data/main-scenarios-v9/index.json').read_text())
        cls.catalogs={}
        for path in cls.index['catalogs']:
            c=Catalog(ROOT/'game/data'/path)
            cls.catalogs[c.data['start_year']]=c

    def test_unique_dates_and_all117_faction_starts(self):
        self.assertEqual(set(self.catalogs),{184,190,191,194,200,207,208,217,219,221,227,238,249})
        count=0
        for year,c in self.catalogs.items():
            self.assertEqual(c.rules.city_officer_capacity,30)
            self.assertEqual(len(c.map_cities),106)
            self.assertEqual(len(c.active_city_ids(year)),105 if year<215 else 106)
            for side in c.factions:
                game=Campaign(c);game.command('new',dict(faction=side,seed=2026),0)
                game.validate(game.state);count+=1
                self.assertTrue(all(len(city.roster.officer_ids)<=30 for city in game.state.cities.values()))
        self.assertEqual(count,117)

    def test_184_nine_factions_seventeen_cities_without_losing_officers(self):
        data=self.catalogs[184].data
        owners=data['initial_owners']
        self.assertEqual({key for key,value in owners.items() if value=='han'},
                         {'henan','jingzhao','wei','chenliu'})
        self.assertEqual({key for key,value in owners.items() if value=='yellow_turban'},
                         {'pingyuan','bohai','dongjun','yingchuan','nanyang','qiao'})
        self.assertEqual(Counter(owners.values())['neutral'],88)
        expected={'han':49,'yellow_turban':27,'dong_zhuo':14,'wu':11,
                  'gongsun_zan':10,'liu_yan':8,'ding_yuan':7,'shi_xie':6,'ma_teng':5}
        self.assertEqual(dict(Counter(owners[r['city']] for r in data['initial_officers'])),expected)
        before=json.loads((ROOT/'game/data/main-scenarios-v8/184-02.json').read_text())
        self.assertEqual({r['person_id']:r['troops'] for r in data['initial_officers']},
                         {r['person_id']:r['troops'] for r in before['initial_officers']})
        for faction in data['factions']:
            leader=next(p for p in data['people'] if p['name']==faction['captain'])
            row=next(r for r in data['initial_officers'] if r['person_id']==leader['person_id'])
            self.assertTrue(row['ruler']);self.assertEqual(row['city'],faction['city'])

    def test_guandu_territory_does_not_convert_wei_officers(self):
        data=self.catalogs[200].data
        before=json.loads((ROOT/'game/data/main-scenarios-v8/200-01.json').read_text())
        self.assertEqual(data['initial_owners']['shangdang'],'yuan_shao')
        old={r['person_id']:before['initial_owners'][r['city']] for r in before['initial_officers']}
        now={r['person_id']:data['initial_owners'][r['city']] for r in data['initial_officers']}
        self.assertEqual(old,now)
        for row in before['initial_officers']:
            if row['city']=='shangdang':self.assertEqual(now[row['person_id']],'wei')

    def test_reviewed_sources_and_frontiers_remain_distinct(self):
        for year,c in self.catalogs.items():
            d=c.data;audit=d['garrison_audit']
            assigned={r['person_id']:r for r in d['initial_officers']}
            self.assertEqual(set(assigned),{r['person_id'] for r in audit['postings']})
            for row in audit['postings']:
                self.assertEqual(row['city'],assigned[row['person_id']]['city'])
                self.assertTrue(row['name'])
                if row['basis']=='authored_enemy_frontier_balanced':
                    self.assertIn(row['city'],audit['factions'][row['faction']]['frontier_cities'])
                if row['basis']=='reviewed_SAN14_source_city_to_board':
                    source=row['source_reference']
                    self.assertEqual((source['year'],source['month']),(year,d['start_month']))
                    self.assertEqual(source['source_ruler'],d['era_assignments'][row['person_id']]['source_ruler'])
                    self.assertTrue(source['url'].startswith('https://wikiwiki.jp/sangokushi14/'))
            # Profiles, terrain, roads and city artwork are unchanged from v8.
            prior=Catalog(ROOT/f'game/data/main-scenarios-v8/{year if year not in (221,249) else 238}-{d["start_month"]:02d}.json') if year not in (221,249) else Catalog(ROOT/'game/data/main-scenarios-v8/238-01.json')
            for field in ('people','cities','links','travel_routes','world'):
                self.assertEqual(d[field],prior.data[field])
        data=self.catalogs[227].data
        self.assertTrue(any(r['basis']=='attested_yanmen_post_227' and r['city']=='yanmen'
                            for r in data['garrison_audit']['postings']))

    def test_supplementary_dates_use_completed_profiles_and_preserve_membership(self):
        for year in (221,249):
            data=self.catalogs[year].data
            self.assertEqual(data['main_scenario']['group'],'supplement')
            self.assertEqual(len(data['people']),1000)
            self.assertTrue(all(p['profile']['virtue'] is not None for p in data['people']))
            old=json.loads((ROOT/f'game/data/eras-v3/{year}.json').read_text())
            for pid,assignment in data['era_assignments'].items():
                self.assertEqual(assignment['source_ruler'],old['era_assignments'][pid]['source_ruler'])
            self.assertTrue(all(data['initial_owners'][key]=='wei' for key in
                ('xiping','zhangye','jiuquan','dunhuang','zhao','julu','hejian','qinghe','yanmen','xinxing')))

    def test_new_garrisons_survive_natural_monthly_ai_and_save_reload(self):
        for year,side in ((184,'han'),(217,'wei'),(249,'shu')):
            game=Campaign(self.catalogs[year])
            game.command('new',dict(faction=side,seed=2026),0)
            for _ in range(12):
                if game.state.phase=='finished':break
                game.command('end_turn',{},game.revision)
                game.command('ai',dict(turn=game.state.turn),game.revision)
                for _ in range(100):
                    phase=game.state.phase
                    if phase=='arrivals':game.command('arrivals',{},game.revision)
                    elif phase in ('battle','result'):
                        game.command('retreat' if phase=='battle' else 'settle',
                            dict(battle_id=game.state.battle['id']),game.revision)
                    else:break
                else:self.fail('AI/arrival processing did not finish')
                game.validate(game.state)
            saved=game.export_save();loaded=Campaign(game.catalog)
            loaded.load_save(saved,0)
            self.assertEqual(loaded.to_dict(),game.to_dict())
            self.assertEqual(game.state.completed_ai_turns,list(range(1,game.state.turn)))
            self.assertGreaterEqual(game.state.turn,10)

    def test_old_save_and_offline_rebuild_keep_every_released_file_unchanged(self):
        paths=list((ROOT/'game/data').rglob('*.json'))
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        subprocess.run([sys.executable,'-B','game/build_unified_campaigns.py'],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        session=CampaignSession([ROOT/'game/data/main-scenarios-v5/184-02.json',
                                 ROOT/'game/data/main-scenarios-v9/184-02.json'])
        session.command('new',dict(scenario='mainland184-02-v5',faction='han',seed=2026),0)
        save=session.export_save();session.load_save(save,session.revision)
        self.assertEqual(session.export_save(),save)
        self.assertEqual(len(session.game.state.cities),96)


if __name__=='__main__':unittest.main()
