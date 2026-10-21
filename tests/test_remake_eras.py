"""New catalogs remain separate from legacy save identities; never use ROM inputs."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
from remake.campaign import Campaign, Catalog, digest
from remake.officers import YearState, year_state, virtue_score
from remake.session import CampaignSession


class EraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = [ROOT/f'game/data/eras/{y}.json' for y in (200,207,217,221,227,249)]
        cls.catalogs = [Catalog(p) for p in cls.paths]

    def game(self, year=217, faction='shu'):
        c = next(c for c in self.catalogs if c.data['start_year']==year)
        g=Campaign(c);g.command('new',{'faction':faction,'seed':2026},0)
        return g

    def test_all36_faction_starts_use_exact_identity_capacity_and_chronology(self):
        starts=0
        for c in self.catalogs:
            for f in c.factions:
                with self.subTest(era=c.data['id'],faction=f):
                    g=Campaign(c);g.command('new',{'faction':f,'seed':2026},0);g.validate(g.state)
                    self.assertEqual(len(g.state.cities),96)
                    self.assertEqual(len(g.state.officers),c.data['coverage']['initial_serving']+c.data['coverage']['initial_free'])
                    self.assertEqual(len(c.data['era_assignments']),1000)
                    self.assertEqual(len(c.ids),1000)
                    for city in g.state.cities.values():self.assertLessEqual(len(city.roster.officer_ids),20)
                    plan=Counter(r['city'] for r in c.data['era_assignments'].values() if r['source_status']=='serving' and r['faction'] and r['year_state'] in ('available','death_year_review'))
                    self.assertLessEqual(max(plan.values()),20)
                    for i,o in g.state.officers.items():
                        self.assertFalse(o.profile.missing)
                        self.assertIn(year_state(c.definitions[o.person_id],g.state.year),(YearState.AVAILABLE,YearState.DEATH_YEAR_REVIEW))
                    starts+=1
        self.assertEqual(starts,36)

    def test_948_hp_and_terrain_filled_but_no_bulk_virtue_or_charisma_mapping(self):
        old=Catalog(ROOT/'game/data/mainland.json');new=self.catalogs[0]
        pending=[i for i,p in old.profiles.items() if p.missing]
        self.assertEqual(len(pending),948)
        self.assertTrue(all(new.profiles[i].health_max==80 and new.profiles[i].terrain_affinity in (0,1,2) for i in pending))
        self.assertEqual(sum(bool(p.missing) for p in new.profiles.values()),852)
        self.assertTrue(all(p.missing==('virtue',) for p in new.profiles.values() if p.missing))
        batch=json.loads((ROOT/'game/config/officer-batch2.json').read_text())['profiles']
        self.assertEqual(len(batch),96)
        for p in batch:
            self.assertFalse(old.profiles[old.ids[p['person_id']]].virtue)
            self.assertEqual(new.profiles[new.ids[p['person_id']]].virtue,virtue_score(p['dimensions']))
            self.assertTrue(p['sources']);self.assertFalse(p['is_historical_fact'])
        for i,p in old.profiles.items():
            if p.virtue is not None:self.assertEqual(new.profiles[i].virtue,p.virtue)

    def test_same_name_ma_zhong_remains_two_people_and_only_shu_profile_enabled(self):
        g=self.game()
        wu=g.catalog.ids['san14-candidate-0767'];shu=g.catalog.ids['san14-candidate-0768']
        self.assertNotEqual(wu,shu)
        self.assertIn(wu,g.catalog.by_id);self.assertNotIn(wu,g.state.officers)
        self.assertIn(shu,g.state.officers);self.assertEqual(g.state.officers[shu].faction_id,'shu')
        self.assertEqual(g.catalog.profiles[wu].missing,('virtue',))

    def test_history_regions_and_faction_changes_follow_selected_era(self):
        g=self.game(217)
        xiahou=next(i for i,p in g.catalog.by_id.items() if p['name']=='夏侯渊')
        self.assertIn(xiahou,g.state.cities['hanzhong'].roster.officer_ids)
        self.assertEqual(g.state.cities['hanzhong'].owner,'wei')
        self.assertEqual(g.state.cities['xiangyang'].owner,'wei')
        self.assertEqual(self.game(221).state.cities['hanzhong'].owner,'shu')
        names={200:('曹操','孙策','刘备'),217:('曹操','孙权','刘备'),227:('曹叡','孙权','刘禅'),249:('曹芳','孙权','刘禅')}
        for y,expected in names.items():
            g=self.game(y)
            self.assertEqual(tuple(g.catalog.name(g.state.extension['leaders'][f]) for f in ('wei','wu','shu')),expected)
        g=self.game(249)
        for name in ('司马懿','曹爽'):
            i=next(i for i,p in g.catalog.by_id.items() if p['name']==name)
            self.assertEqual(g.state.officers[i].faction_id,'wei')

    def test_death_year_snapshot_allows_sun_ce_then_next_year_retires_once(self):
        g=self.game(200,'wu');i=next(i for i,p in g.catalog.by_id.items() if p['name']=='孙策')
        self.assertEqual(year_state(g.catalog.definitions[g.state.officers[i].person_id],200),YearState.DEATH_YEAR_REVIEW)
        self.assertTrue(g.state.officers[i].alive)
        self.assertEqual(g.state.extension['leaders']['wu'],i)
        # Advance naturally through all twelve months and any intervening AI
        # battles. No date, cursor, faction or random-state injection.
        for _ in range(1500):
            if g.state.year==201:break
            if g.state.phase=='city':g.command('end_turn',{},g.revision)
            elif g.state.phase=='ai':g.command('ai',{'turn':g.state.turn},g.revision)
            elif g.state.phase in ('battle','duel'):
                g.command('retreat',{'battle_id':g.state.battle['id']},g.revision)
            elif g.state.phase=='result':g.command('settle',{'battle_id':g.state.battle['id']},g.revision)
            else:self.fail(g.state.phase)
        self.assertEqual(g.state.year,201);self.assertFalse(g.state.officers[i].alive)
        self.assertNotEqual(g.state.extension['leaders']['wu'],i)
        g.validate(g.state)
        receipts=[r for r in g.state.year_events if r==f'remove_after_death_year:{g.state.officers[i].person_id}:201']
        self.assertEqual(len(receipts),1)
        self.assertEqual(sum(i in c.roster.officer_ids for c in g.state.cities.values()),0)

    def test_future_and_unconfigured_people_not_implicitly_spawned(self):
        g=self.game(217)
        for name in ('姜维','曹叡'):
            i=next(i for i,p in g.catalog.by_id.items() if p['name']==name)
            self.assertNotIn(i,g.state.officers)
        for i,p in g.catalog.profiles.items():
            if p.missing:self.assertNotIn(i,g.state.officers)
        # Source dead/not-yet-allowed rows cannot slip through initial spawning.
        for i,o in g.state.officers.items():
            r=g.catalog.data['era_assignments'][o.person_id]
            self.assertIn(r['status'],('serving','free'))

    def test_saves_across_six_eras_and_two_legacy_catalogs_keep_hash_checks(self):
        paths=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json']+self.paths
        session=CampaignSession(paths)
        for c in session.catalogs.values():
            faction=next(iter(c.factions))
            session.command('new',{'scenario':c.data['id'],'faction':faction,'seed':2026},session.revision)
            saved=session.export_save();before=session.to_dict()
            session.command('new',{'scenario':'mainland217-v2','faction':'shu','seed':33},session.revision)
            session.load_save(saved,session.revision)
            self.assertEqual(session.to_dict(),before)
            invalid=deepcopy(saved);invalid['catalog_sha256']='0'*64
            invalid['checksum']=digest({k:v for k,v in invalid.items() if k!='checksum'})
            snap=session.to_dict();rev=session.revision
            with self.assertRaises(ValueError):session.load_save(invalid,rev)
            self.assertEqual(session.to_dict(),snap);self.assertEqual(session.revision,rev)

    def test_generation_is_deterministic_and_legacy_map_unchanged(self):
        import subprocess
        tracked=[ROOT/'game/data/demo.json',ROOT/'game/data/mainland.json',ROOT/'game/assets/map.png']+list((ROOT/'game/data/eras').glob('*.json'))
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
        subprocess.run([sys.executable,'-B','game/build_eras.py'],cwd=ROOT,check=True,capture_output=True)
        self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked})
