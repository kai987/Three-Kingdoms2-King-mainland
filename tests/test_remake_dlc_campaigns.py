"""DLC dates, explicit IF exceptions, roster safety and retained old saves."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog
from remake.officers import YearState,year_state


class DlcCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((ROOT/'game/config/dlc-scenarios.json').read_text())
        cls.index=json.loads((ROOT/'game/data/main-scenarios-v12/index.json').read_text())
        cls.catalogs={}
        for path in cls.index['catalogs']:
            c=Catalog(ROOT/'game/data'/path);cls.catalogs[(c.data['start_year'],c.data['start_month'])]=c

    def game(self,year,month,side='shu'):
        g=Campaign(self.catalogs[year,month]);g.command('new',dict(faction=side,seed=2026),0);return g

    def person(self,catalog,name):
        matches=[p for p in catalog.data['people'] if p['name']==name]
        self.assertEqual(len(matches),1);return matches[0]

    def test_25_unique_dates_and_official_categories_keep225_single_and211_custom(self):
        self.assertEqual(len(self.catalogs),25)
        self.assertEqual(len(self.spec['entries']),12)
        groups=Counter(e['group'] for e in self.spec['entries'])
        self.assertEqual(groups,{'dlc':3,'if':6,'bonus':2,'custom':1})
        expected={(188,6),(196,6),(197,7),(201,5),(209,6),(210,11),(211,7),(212,6),(225,7),(234,2),(235,1),(263,5)}
        self.assertEqual({(e['year'],e['month']) for e in self.spec['entries']},expected)
        self.assertEqual(sum((d['year'],d['month'])==(225,7) for d in self.index['summary']),1)
        for date,c in self.catalogs.items():self.assertEqual(c.data['content_generation'],12)
        custom=self.catalogs[211,7].data['main_scenario']
        self.assertEqual(custom['title'],'入蜀爭奪戰');self.assertTrue(custom['user_custom'])
        self.assertIsNone(custom['official_source']);self.assertIn('潼關之戰',custom['official_same_date_title'].values())
        self.assertEqual(self.catalogs[234,2].data['main_scenario']['title_i18n']['ja'],'秋風五丈原')
        for e in self.spec['entries']:
            self.assertEqual(set(e['title_i18n']),{'zh-Hant','ja'})
            self.assertEqual(set(e['summary_i18n']),{'zh-Hant','ja'})

    def test_all219_faction_starts_obey_years_capacity_identity_and_save_roundtrip(self):
        starts=0
        for date,c in self.catalogs.items():
            self.assertEqual(len(c.definitions),1000);self.assertEqual(len(c.map_cities),115)
            self.assertEqual(c.rules.city_officer_capacity,30);self.assertEqual(c.rules.battle_officers_per_side,10)
            for side in c.factions:
                with self.subTest(date=date,side=side):
                    g=Campaign(c);g.command('new',dict(faction=side,seed=2026),0);g.validate(g.state)
                    self.assertEqual(len(g.state.cities),len(c.active_city_ids(*date)))
                    for key,city in g.state.cities.items():
                        self.assertLessEqual(len(city.roster.officer_ids),30)
                        for ident in city.roster.officer_ids:self.assertEqual(g.state.officers[ident].faction_id,city.owner)
                    for o in g.state.officers.values():
                        self.assertIn(year_state(c.definitions[o.person_id],date[0]),(YearState.AVAILABLE,YearState.DEATH_YEAR_REVIEW))
                    restored=Campaign(c);restored.load_save(g.export_save(),0)
                    self.assertEqual(restored.to_dict(),g.to_dict());starts+=1
        self.assertEqual(starts,219)

    def test_existing13_episodes_and_all_profiles_are_unchanged_in_substance(self):
        old=json.loads((ROOT/'game/data/main-scenarios-v11/index.json').read_text())
        for filename in old['catalogs']:
            prior=json.loads((ROOT/'game/data'/filename).read_text());after=deepcopy(self.catalogs[prior['start_year'],prior['start_month']].data)
            after['id']=prior['id'];after['content_generation']=prior['content_generation']
            self.assertEqual(after,prior)
        for e in self.spec['entries']:
            prior=json.loads((ROOT/'game/data/main-scenarios-v11'/(e['base']+'.json')).read_text())
            current=self.catalogs[e['year'],e['month']].data
            originals={p['person_id']:p for p in prior['people']}
            for person in current['people']:
                p=originals[person['person_id']]
                self.assertEqual(person['runtime_id'],p['runtime_id']);self.assertEqual(person['profile'],p['profile'])
            for field in ('cities','city_foundings','travel_hazards','travel_routes','sea_routes','exploration_routes','initial_city_resources','city_income'):
                self.assertEqual(current[field],prior[field])

    def test_key_story_territories_rulers_and_same_year_people_are_real_opening_state(self):
        expected={(211,7):{'shu':'刘备','liu_zhang':'刘璋','zhang_lu':'张鲁','ma_teng':'马超'},
                  (225,7):{'wei':'曹丕','shu':'刘禅','wu':'孙权','nanman':'孟获'},
                  (234,2):{'wei':'曹叡','shu':'刘禅','wu':'孙权'},
                  (263,5):{'wei':'曹奂','shu':'刘禅','wu':'孙休'}}
        for date,sides in expected.items():
            c=self.catalogs[date];g=self.game(*date,side='shu')
            for side,name in sides.items():
                p=self.person(c,name);self.assertEqual(c.factions[side]['captain'],name)
                self.assertEqual(g.state.extension['leaders'][side],p['runtime_id'])
        self.assertEqual(self.catalogs[201,5].data['initial_owners']['nanyang'],'wei')
        self.assertEqual(self.catalogs[201,5].data['initial_owners']['yingchuan'],'shu')
        self.assertEqual(self.catalogs[210,11].data['initial_owners']['shujun'],'wu')
        self.assertEqual(self.catalogs[210,11].data['initial_owners']['hanzhong'],'wu')
        self.assertEqual(self.catalogs[235,1].data['initial_owners']['jingzhao'],'shu')
        self.assertEqual(self.catalogs[225,7].data['initial_owners']['jianning'],'nanman')
        c=self.catalogs[234,2];p=self.person(c,'诸葛亮');self.assertEqual(self.game(234,2).state.officers[p['runtime_id']].faction_id,'shu')
        c=self.catalogs[263,5];g=self.game(263,5,side='wei')
        for name in ['司马昭','司马炎','羊祜','杜预','钟会','邓艾','邓忠']:
            p=self.person(c,name);self.assertEqual(g.state.officers[p['runtime_id']].faction_id,'wei')
        for name in ['曹丕','曹叡','刘备','孙权']:
            p=self.person(c,name);self.assertNotIn(p['runtime_id'],g.state.officers)
        # The two same-name Ma Zhong entries must remain separate identities.
        g=self.game(225,7);self.assertEqual(g.state.officers[767].faction_id,'shu')
        if 766 in g.state.officers:self.assertNotEqual(g.state.officers[766].faction_id,'shu')

    def test_chronology_exceptions_are_local_explicit_and_advance_normally(self):
        for date,name,before,after in [((188,6),'区星',187,188),((196,6),'张杨',195,199),
                ((197,7),'张杨',195,199),((210,11),'周瑜',210,220),((235,1),'诸葛亮',234,245)]:
            c=self.catalogs[date];p=self.person(c,name);note=p['scenario_chronology_override']
            self.assertEqual(note['before']['death_year'],before);self.assertEqual(note['after']['death_year'],after)
            self.assertEqual(p['death_year'],after);self.assertTrue(note['sources'])
        g=self.game(235,1,side='shu');ident=self.person(g.catalog,'诸葛亮')['runtime_id']
        # Controlled calendar fixture isolates annual survival after the IF start.
        for _ in range(12):
            g._complete_month(g.state);g._spawn_eligible(g.state);g._reconcile_factions(g.state);g.validate(g.state)
        self.assertTrue(g.state.officers[ident].alive);self.assertEqual(g.state.year,236)
        self.assertEqual(self.person(Catalog(ROOT/'game/data/main-scenarios-v11/238-01.json'),'诸葛亮')['death_year'],234)

    def test_pending_capacity_and_narrative_exclusions_do_not_respawn_next_month_or_year(self):
        g=self.game(201,5,side='wei');pending=g.catalog.data['dlc_audit']['pending_capacity']
        self.assertEqual(len(pending),14)
        ids={g.catalog.ids[r['person_id']] for r in pending}
        self.assertTrue(ids.isdisjoint(g.state.officers))
        self.assertTrue({r['person_id'] for r in pending}.isdisjoint(g.catalog.data['appearance_locations']))
        for _ in range(12):
            g._complete_month(g.state);g._spawn_eligible(g.state);g._reconcile_factions(g.state);g.validate(g.state)
            self.assertTrue(ids.isdisjoint(g.state.officers))
        for date,name in [((197,7),'袁术'),((211,7),'马腾'),((212,6),'曹操')]:
            g=self.game(*date);ident=self.person(g.catalog,name)['runtime_id']
            for _ in range(12):
                self.assertNotIn(ident,g.state.officers)
                g._complete_month(g.state);g._spawn_eligible(g.state);g._reconcile_factions(g.state);g.validate(g.state)
            self.assertNotIn(ident,g.state.officers)

    def test263_city_openings_and_new_force_colors_are_distinguishable(self):
        c=self.catalogs[263,5];self.assertEqual(len(c.data['active_cities']),114)
        for key in ('linhai','linchuan','jianan'):self.assertIn(key,c.data['active_cities']);self.assertEqual(c.data['initial_owners'][key],'wu')
        self.assertNotIn('wuxing',c.data['active_cities'])
        c=self.catalogs[188,6];colors=[c.factions[key]['color'] for key in ('han_sui','zhang_chun','ou_xing','liu_yu')]
        self.assertEqual(len(colors),len(set(colors)))

    def test_new_dated_chapters_continue_real_monthly_AI_and_save_receipts(self):
        for date in ((211,7),(225,7),(234,2),(263,5)):
            with self.subTest(date=date):
                g=self.game(*date);start=g.state.turn
                g.command('end_turn',{},g.revision)
                for _ in range(150):
                    if g.state.phase=='ai':g.command('ai',dict(turn=g.state.turn),g.revision)
                    elif g.state.phase=='arrivals':g.command('arrivals',{},g.revision)
                    elif g.state.phase=='battle':g.command('retreat',dict(battle_id=g.state.battle['id']),g.revision)
                    elif g.state.phase=='result':g.command('settle',dict(battle_id=g.state.battle['id']),g.revision)
                    else:break
                    g.validate(g.state)
                self.assertEqual(g.state.turn,start+1);self.assertIn(g.state.phase,('city','finished'))
                restored=Campaign(g.catalog);restored.load_save(g.export_save(),0);self.assertEqual(restored.to_dict(),g.to_dict())

    def test_offline_rebuild_preserves_all_released_catalogs_and_v11_save(self):
        files=list((ROOT/'game/data').rglob('*.json'));before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        # New cities formerly inherited owners through a set iteration, so
        # equal data could receive different raw JSON/catalog-save hashes.
        # Exercise separate processes with deliberately different hash salts.
        for seed in ('3','17','8675309'):
            with self.subTest(hashseed=seed):
                subprocess.run([sys.executable,'-B',str(ROOT/'game/build_dlc_campaigns.py')],cwd=ROOT,
                    env={**os.environ,'PYTHONHASHSEED':seed},check=True,capture_output=True)
                self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        old=Campaign(Catalog(ROOT/'game/data/main-scenarios-v11/217-07.json'));old.command('new',dict(faction='wei',seed=2026),0)
        restored=Campaign(old.catalog);restored.load_save(old.export_save(),0);self.assertEqual(restored.export_save(),old.export_save())


if __name__=='__main__':unittest.main()
