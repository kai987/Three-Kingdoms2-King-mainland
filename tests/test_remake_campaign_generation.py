"""Generation3: identity, individually evidenced ratings, history edits and saves."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,digest
from remake.officers import YearState,year_state,virtue_score
from remake.session import CampaignSession


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs={y:Catalog(ROOT/f'game/data/eras-v3/{y}.json') for y in (184,190,194,200,207,217,221,227,249)}
        cls.previous=Catalog(ROOT/'game/data/eras/217.json')

    def game(self,year=217,side='shu',seed=2026):
        g=Campaign(self.catalogs[year]);g.command('new',{'faction':side,'seed':seed},0);return g

    def ident(self,c,name):return next(i for i,p in c.by_id.items() if p['name']==name)

    def test_120_new_ratings_use_evidence_and_existing_anchors_without_changing_others(self):
        c=self.catalogs[217]
        batch=json.loads((ROOT/'game/config/officer-batch3.json').read_text())['profiles']
        ids={p['person_id'] for p in batch};self.assertEqual(len(ids),120)
        for p in batch:
            i=c.ids[p['person_id']];a=p['calibration']
            self.assertIsNone(self.previous.profiles[i].virtue)
            self.assertEqual(p['virtue'],virtue_score(p['dimensions']))
            self.assertEqual(c.profiles[i].virtue,p['virtue'])
            self.assertEqual(a['virtue'],self.previous.profiles[self.previous.ids[a['person_id']]].virtue)
            self.assertEqual(p['virtue']-a['virtue'],a['difference'])
            self.assertTrue(p['sources']);self.assertFalse(p['is_historical_fact'])
        for i,p in c.profiles.items():
            before=self.previous.profiles[i]
            self.assertEqual((p.health_max,p.martial_strength,p.intellect,p.terrain_affinity),
                             (before.health_max,before.martial_strength,before.intellect,before.terrain_affinity))
            if c.by_id[i]['person_id'] not in ids:self.assertEqual(p.virtue,before.virtue)
        self.assertEqual(sum(not p.missing for p in c.profiles.values()),268)
        self.assertTrue(all(p.missing==('virtue',) for p in c.profiles.values() if p.missing))

    def test_75_faction_starts_are_legal_with_planned_and_running_capacity20(self):
        count=0
        for year,c in self.catalogs.items():
            for side in c.factions:
                with self.subTest(year=year,side=side):
                    g=Campaign(c);g.command('new',{'faction':side,'seed':2026},0);g.validate(g.state)
                    self.assertEqual(len(g.state.cities),96)
                    self.assertEqual(len(g.state.officers),c.data['coverage']['initial_serving']+c.data['coverage']['initial_free'])
                    self.assertEqual(len(c.data['era_assignments']),1000)
                    self.assertTrue(all(len(city.roster.officer_ids)<=20 for city in g.state.cities.values()))
                    planned=Counter(r['city'] for r in c.data['era_assignments'].values() if r['source_status']=='serving' and r['faction'] and r['city'] and r['year_state'] in ('available','death_year_review'))
                    self.assertLessEqual(max(planned.values()),20)
                    for i,o in g.state.officers.items():
                        self.assertFalse(o.profile.missing)
                        self.assertIn(year_state(c.definitions[o.person_id],year),(YearState.AVAILABLE,YearState.DEATH_YEAR_REVIEW))
                    count+=1
        self.assertEqual(count,75)

    def test_184_unifies_imperial_groups_instead_of_inventing_late_states(self):
        g=self.game(184,'han');self.assertEqual(g.state.month,3)
        self.assertEqual(set(g.catalog.factions),{'han','yellow_turban'})
        for name in ('刘焉','董卓','孙坚','曹操','皇甫嵩','卢植','何进'):
            i=self.ident(g.catalog,name);self.assertEqual(g.state.officers[i].faction_id,'han')
        i=self.ident(g.catalog,'张角')
        self.assertEqual(g.state.officers[i].faction_id,'yellow_turban')
        self.assertTrue(g.catalog.data['era_assignments'][g.state.officers[i].person_id]['death_year_resolved'])

    def test_194_sun_ce_follows_yuan_shu_and_keeps_original_source_group(self):
        g=self.game(194,'yuan_shu');i=self.ident(g.catalog,'孙策')
        self.assertEqual(g.state.officers[i].faction_id,'yuan_shu')
        r=g.catalog.data['era_assignments'][g.state.officers[i].person_id]
        self.assertEqual(r['source_ruler'],'孫策');self.assertTrue(r['membership_revision']['sources'])
        self.assertNotIn('wu',g.catalog.factions)

    def test_200_zhang_xiu_and_jia_xu_are_cao_members_not_missing_faction(self):
        g=self.game(200,'wei')
        for name in ('张绣','贾诩'):
            i=self.ident(g.catalog,name);self.assertEqual(g.state.officers[i].faction_id,'wei')
            r=g.catalog.data['era_assignments'][g.state.officers[i].person_id]
            self.assertEqual(r['source_ruler'],'張繡');self.assertEqual(r['faction'],'wei')
        self.assertNotIn('張繡',g.catalog.data['coverage']['pending_factions'])

    def test_named_career_regions_match_effective_factions(self):
        for y,name,city,side in [(207,'刘馥','jiujiang','wei'),(249,'陆胤','jiaozhi','wu'),(217,'文聘','yiyang','wei'),(200,'太史慈','yuzhang','wu')]:
            g=self.game(y,side);i=self.ident(g.catalog,name)
            self.assertIn(i,g.state.cities[city].roster.officer_ids)
            self.assertEqual(g.state.officers[i].faction_id,side)
            r=g.catalog.data['era_assignments'][g.state.officers[i].person_id]
            self.assertTrue(r['posting_reference']['source'])

    def test_190_capacity_excess_stays_pending_without_spawning_or_extra_territory(self):
        g=self.game(190,'yuan_shao')
        rows=[(pid,r) for pid,r in g.catalog.data['era_assignments'].items() if r['status']=='pending_capacity']
        self.assertEqual(len(rows),5)
        self.assertEqual([c.id for c in g.state.cities.values() if c.owner=='yuan_shao'],['bohai'])
        for pid,r in rows:
            self.assertIsNone(r['city']);self.assertNotIn(g.catalog.ids[pid],g.state.officers)
            self.assertNotIn(pid,g.catalog.data['appearance_locations'])

    def test_same_name_and_unreviewed_people_cannot_enter_implicitly(self):
        g=self.game(217)
        for i,p in g.catalog.profiles.items():
            if p.missing:self.assertNotIn(i,g.state.officers)
        self.assertNotIn(g.catalog.ids['san14-candidate-0767'],g.state.officers)
        self.assertIn(g.catalog.ids['san14-candidate-0768'],g.state.officers)
        self.assertEqual(len(set(g.catalog.ids.values())),1000)
        self.assertEqual(g.catalog.ids['san14-candidate-0001'],255)

    def test_all17_scenario_saves_roundtrip_and_changed_hash_is_atomic_failure(self):
        paths=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json']+sorted((ROOT/'game/data/eras').glob('[12]*.json'))+sorted((ROOT/'game/data/eras-v3').glob('[12]*.json'))
        session=CampaignSession(paths);self.assertEqual(len(session.catalogs),17)
        for c in session.catalogs.values():
            session.command('new',{'scenario':c.data['id'],'faction':next(iter(c.factions)),'seed':2026},session.revision)
            saved=session.export_save();before=session.to_dict()
            session.command('new',{'scenario':'mainland217-v3','faction':'shu','seed':30},session.revision)
            session.load_save(saved,session.revision);self.assertEqual(session.to_dict(),before)
            bad=deepcopy(saved);bad['catalog_sha256']='0'*64;bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
            rev=session.revision
            with self.assertRaises(ValueError):session.load_save(bad,rev)
            self.assertEqual(session.to_dict(),before);self.assertEqual(session.revision,rev)

    def test_rebuild_keeps_released_v1_v2_and_new_v3_bytes_deterministic(self):
        paths=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json',ROOT/'game/assets/map.png']+list((ROOT/'game/data/eras').glob('*.json'))+list((ROOT/'game/data/eras-v3').glob('*.json'))
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        subprocess.run([sys.executable,'-B','game/build_campaigns.py'],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
