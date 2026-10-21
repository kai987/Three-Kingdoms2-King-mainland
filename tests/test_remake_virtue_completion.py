"""Explicit default provenance, unchanged releases and playable completed rosters."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,GameError,SeedRng
from remake.officers import convert_profile,virtue_score
from remake.session import CampaignSession


class VirtueCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=json.loads((ROOT/'game/data/main-scenarios-v5/index.json').read_text())
        cls.catalogs=[Catalog(ROOT/'game/data'/p) for p in cls.index['catalogs']]
        cls.current=next(c for c in cls.catalogs if c.data['start_year']==217)
        cls.config=json.loads((ROOT/'game/config/virtue-completion.json').read_text())

    def test_all731_completed_existing269_and_other_fields_unchanged(self):
        for c in self.catalogs:
            old=Catalog(ROOT/'game/data/main-scenarios'/f'{c.data["start_year"]}-{c.data["start_month"]:02d}.json')
            for row in c.data['people']:
                pid=row['person_id'];prior=old.by_id[old.ids[pid]]
                self.assertFalse(c.profiles[c.ids[pid]].missing)
                if prior['profile']['virtue'] is not None:self.assertEqual(row,prior)
                else:
                    self.assertEqual(row['runtime_id'],prior['runtime_id'])
                    self.assertEqual(row['ability_source'],prior['ability_source'])
                    for key in ('health_max','martial_strength','intellect','terrain_affinity','source_stats'):
                        self.assertEqual(row['profile'][key],prior['profile'][key])
                    self.assertEqual(row['profile']['health_max'],80)
                    self.assertEqual(row['profile']['terrain_affinity'],0)
            self.assertEqual(Counter((p.get('virtue_design') or {}).get('status') for p in c.data['people']),
                             {'configured_design':284,'configured_default':715,None:1})
            self.assertEqual(c.data['coverage']['configured_profiles'],1000)
            self.assertEqual(c.data['coverage']['pending_profiles'],0)

    def test_history_ratings_are_calibrated_and_defaults_do_not_fabricate_evidence(self):
        c=self.current
        self.assertEqual(len(self.config['reviewed']),16)
        for row in c.data['people']:
            d=row.get('virtue_design')
            if not d:continue
            if d['status']=='configured_design':
                self.assertTrue(d['sources']);self.assertEqual(virtue_score(d['dimensions']),row['profile']['virtue'])
                if row['person_id'] in {r['person_id'] for r in self.config['reviewed']}:
                    a=d['calibration'];self.assertEqual(c.profiles[c.ids[a['person_id']]].virtue,a['virtue'])
            else:
                self.assertEqual(row['profile']['virtue'],60)
                self.assertEqual(d['policy_id'],'virtue-default-60-2026-10-21')
                self.assertIsNone(d['dimensions']);self.assertEqual(d['sources'],[])
                self.assertFalse(d['is_historical_fact'])
                self.assertIn('explicit_user_default60',row['profile']['basis']['virtue'])

    def test_default_conversion_rejects_forged_policy_and_overwrite(self):
        policy=self.config['default_policy']
        self.assertEqual(convert_profile(virtue_design=policy).virtue,60)
        for key,value in [('virtue',61),('virtue',True),('authority','inferred'),('policy_id','other'),
                          ('dimensions',{}),('sources',[{'url':'invented'}]),('is_historical_fact',True)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                convert_profile(virtue_design=dict(policy,**{key:value}))
        with self.assertRaises(ValueError):convert_profile(legacy={'virtue':82},virtue_design=policy)
        self.assertIsNone(convert_profile(virtue_design={'status':'draft'}).virtue)
        with self.assertRaisesRegex(ValueError,'source references'):
            convert_profile(virtue_design={'status':'configured_design','dimensions':{},'sources':[]})

    def test_every_faction_starts_with_capacity_chronology_and_membership_guards(self):
        starts=0
        for c in self.catalogs:
            for faction in c.factions:
                g=Campaign(c);g.command('new',{'faction':faction,'seed':2026},0);g.validate(g.state);starts+=1
                self.assertTrue(all(len(city.roster.officer_ids)<=30 for city in g.state.cities.values()))
                self.assertEqual(c.rules.battle_officers_per_side,10)
                self.assertEqual(len(g.state.officers),len(c.data['initial_officers'])+len(c.data['initial_free_officers']))
                for pid,a in c.data['era_assignments'].items():
                    if a['status'] not in ('serving','free'):self.assertNotIn(c.ids[pid],g.state.officers)
                    if a['status']=='pending_history':self.assertNotIn(pid,c.data['appearance_locations'])
        self.assertEqual(starts,102)

    def test_default_actor_can_recruit_and_uses_real60_in_success_threshold(self):
        # Controlled RNG only; both officers and their actual starting locations
        # come from the217 catalog, not a synthetic roster.
        c=self.current;g=Campaign(c);g.command('new',{'faction':'shu','seed':2026},0)
        city=g.state.cities['shujun']
        actor=next(i for i in city.roster.officer_ids if c.name(i)=='王伉')
        candidate=next(i for i in g._free_candidates(g.state,city) if c.name(i)=='柳隐')
        self.assertEqual(g.state.officers[actor].profile.virtue,60)
        self.assertEqual(g.state.officers[candidate].profile.virtue,60)
        chance=35+30+g.state.officers[actor].profile.intellect//5-12
        for succeeds in (False,True):
            twin=Campaign(c);twin.load_save(g.export_save(),0)
            seed=next(s for s in range(1,10000) if (SeedRng(s).next()%100<chance)==succeeds)
            twin.state.rng.state=seed
            gold=twin.state.cities[city.id].gold
            twin.command('recruit_officer',{'city':city.id,'actor':actor,'officer':candidate},twin.revision)
            self.assertEqual(candidate in twin.state.cities[city.id].roster.officer_ids,succeeds)
            self.assertEqual(twin.state.cities[city.id].gold,gold-60)
            twin.validate(twin.state)

    def test_39_catalog_save_roundtrips_and_only11_current_chapters(self):
        paths=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json']
        for folder in ('eras','eras-v3','main-scenarios','main-scenarios-v5'):
            index=json.loads((ROOT/f'game/data/{folder}/index.json').read_text())
            paths += [ROOT/'game/data'/p for p in index['catalogs']]
        session=CampaignSession(paths)
        self.assertEqual(len(session.catalogs),39)
        for scenario,c in session.catalogs.items():
            session.command('new',{'scenario':scenario,'faction':next(iter(c.factions)),'seed':2026},session.revision)
            save=session.export_save();before=session.to_dict();session.load_save(save,session.revision)
            self.assertEqual(before,session.to_dict())
        current=[s for s in session.view()['catalog']['scenarios'] if not s['archived']]
        self.assertEqual(len(current),11)
        self.assertTrue(all(s['id'].endswith('-v5') for s in current))
        save=session.export_save();save['scenario']='mainland217-07-v4';before=session.to_dict()
        with self.assertRaises(GameError):session.load_save(save,session.revision)
        self.assertEqual(before,session.to_dict())

    def test_completion_rebuild_is_deterministic_and_keeps_all_old_files(self):
        paths=list((ROOT/'game/data').rglob('*.json'))+[ROOT/'expansion/officers/data/virtue-completion-audit.json']
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        subprocess.run([sys.executable,'-B',str(ROOT/'game/build_virtue_completion.py')],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


if __name__=='__main__':unittest.main()
