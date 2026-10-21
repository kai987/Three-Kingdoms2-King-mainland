"""City-size economy, troop accounting and an actually usable new road."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog
from remake.session import CampaignSession


class CityCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((ROOT/'game/data/main-scenarios-v6/index.json').read_text())
        cls.catalogs=[Catalog(ROOT/'game/data'/p) for p in cls.index['catalogs']]
        cls.current=next(c for c in cls.catalogs if c.data['start_year']==217)

    def game(self):
        g=Campaign(self.current);g.command('new',{'faction':'shu','seed':2026},0);return g

    def test_all102_starts_use_city_specific_resources_with_unchanged_officers(self):
        starts=0
        for c in self.catalogs:
            old=Catalog(ROOT/'game/data/main-scenarios-v5'/f'{c.data["start_year"]}-{c.data["start_month"]:02d}.json')
            self.assertEqual(c.data['people'],old.data['people'])
            self.assertEqual(c.data['initial_officers'],old.data['initial_officers'])
            self.assertEqual(c.data['initial_owners'],old.data['initial_owners'])
            self.assertEqual(Counter(r['tier'] for r in c.data['city_profiles'].values()),{'normal':83,'large':9,'giant':4})
            for faction in c.factions:
                g=Campaign(c);g.command('new',{'faction':faction,'seed':2026},0);g.validate(g.state);starts+=1
                for key,city in g.state.cities.items():
                    self.assertEqual({k:getattr(city,k) for k in ('gold','grain','reserves')},c.data['initial_city_resources'][key])
                    self.assertLessEqual(len(city.roster.officer_ids),30)
            self.assertEqual(c.map_cities['shujun']['terrain'],'plain')
            self.assertEqual(c.map_cities['guanghan']['terrain'],'plain')
            self.assertEqual(old.map_cities['shujun']['terrain'],'mountain')
        self.assertEqual(starts,102)

    def test_large_and_giant_exceed_normal_in_all_three_resources_and_income(self):
        d=self.current.data
        for field in ('initial_city_resources','city_income'):
            normal=d[field]['yinping'];large=d[field]['shujun'];giant=d[field]['yingchuan']
            for key in ('gold','grain','reserves'):
                self.assertGreater(large[key],normal[key]);self.assertGreater(giant[key],large[key])
        self.assertTrue(all(p['is_SAN14_starting_resources'] is False for p in d['city_profiles'].values()))
        self.assertTrue(d['city_profiles']['shujun']['reference_income'])

    def test_monthly_city_income_adds_reserves_to_the_soldier_ledger_only_for_owned_cities(self):
        g=self.game();before={k:(c.gold,c.grain,c.reserves) for k,c in g.state.cities.items()}
        recruited=g.state.soldiers['recruited'];total=0
        # Isolate the calendar service; no AI purchasing/combat obscures income.
        g._complete_month(g.state)
        for key,c in g.state.cities.items():
            income=g.catalog.data['city_income'][key] if c.owner!='neutral' else dict(gold=0,grain=0,reserves=0)
            self.assertEqual((c.gold,c.grain,c.reserves),tuple(before[key][i]+income[k] for i,k in enumerate(('gold','grain','reserves'))))
            total+=income['reserves']
        self.assertEqual(g.state.soldiers['recruited']-recruited,total);g.validate(g.state)

    def test_chengdu_can_actually_attack_yinping_and_settle_on_the_new_direct_road(self):
        g=self.game();city=g.state.cities['shujun'];ident=city.roster.officer_ids[0]
        self.assertIn('yinping',g._neighbors('shujun'));self.assertIn('shujun',g._neighbors('yinping'))
        self.assertNotIn(frozenset(('yinping','shujun')),Catalog(ROOT/'game/data/main-scenarios-v5/217-07.json').links)
        g.command('depart',{'source':'shujun','target':'yinping','officers':[ident]},g.revision)
        self.assertEqual(g.state.battle['source'],'shujun');self.assertEqual(g.state.battle['target'],'yinping')
        self.assertEqual(g.state.phase,'result') # Actual217 start has no Yinping defenders.
        g.command('settle',{'battle_id':g.state.battle['id']},g.revision)
        self.assertEqual(g.state.cities['yinping'].owner,'shu');g.validate(g.state)

    def test_new_direct_road_is_used_for_friendly_transfer_cost(self):
        g=self.game();g.state.cities['yinping'].owner='shu' # Controlled already-captured empty city.
        ident=g.state.cities['shujun'].roster.officer_ids[1];grain=g.state.cities['shujun'].grain
        self.assertEqual(g._friendly_path(g.state,'shujun','yinping','shu'),['shujun','yinping'])
        g.command('transfer',{'source':'shujun','target':'yinping','officers':[ident]},g.revision)
        self.assertEqual(g.state.cities['shujun'].grain,grain-5)
        self.assertIn(ident,g.state.cities['yinping'].roster.officer_ids);g.validate(g.state)

    def test_all50_catalogs_keep_separate_save_identities_and_old_resource_rules(self):
        paths=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json']
        for folder in ('eras','eras-v3','main-scenarios','main-scenarios-v5','main-scenarios-v6'):
            index=json.loads((ROOT/f'game/data/{folder}/index.json').read_text());paths.extend(ROOT/'game/data'/p for p in index['catalogs'])
        s=CampaignSession(paths);self.assertEqual(len(s.catalogs),50)
        self.assertEqual(len([r for r in s.view()['catalog']['scenarios'] if not r['archived']]),11)
        for key,c in s.catalogs.items():
            s.command('new',{'scenario':key,'faction':next(iter(c.factions)),'seed':2026},s.revision)
            saved=s.export_save();before=s.to_dict();s.load_save(saved,s.revision);self.assertEqual(before,s.to_dict())
            if c.data.get('content_generation',0)<6:
                self.assertFalse(s.view()['catalog']['road_additions'])
                self.assertFalse(s.view()['catalog']['city_income'])
            else:self.assertEqual(s.view()['catalog']['road_additions'],[['yinping','shujun']])

    def test_offline_rebuild_does_not_change_the39_published_catalogs(self):
        files=list((ROOT/'game/data').rglob('*.json'));before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        subprocess.run([sys.executable,'-B','game/build_city_campaigns.py'],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


if __name__=='__main__':unittest.main()
