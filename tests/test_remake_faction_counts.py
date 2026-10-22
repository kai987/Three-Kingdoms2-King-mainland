"""Displayed faction membership must follow actual playable rosters and actions."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import SeedRng
from remake import civil_staff
from remake.session import CampaignSession,faction_officer_counts,faction_resources


class FactionOfficerCountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
        if index['schema']!='tk2-campaign-index-v1' or len(index['catalogs'])!=25:
            raise AssertionError('Expected25 current campaign catalogs')
        cls.paths=[ROOT/'game/data'/name for name in index['catalogs']]

    def session(self):
        session=CampaignSession([ROOT/'game/data/campaigns/225-07.json',ROOT/'game/data/campaigns/217-07.json'])
        session.command('new',dict(scenario='mainland217-07',faction='shu',seed=2026),0)
        return session

    def test_each_preview_counts_actual_starting_members_without_mutation(self):
        session=CampaignSession(self.paths);before=deepcopy({key:c.data for key,c in session.catalogs.items()})
        revision=session.revision
        for row in session.view()['catalog']['scenarios']:
            catalog=session.catalogs[row['id']]
            expected=Counter(catalog.data['initial_owners'][r['city']] for r in catalog.data['initial_officers'])
            self.assertEqual(row['faction_officers'],{side:expected[side] for side in catalog.factions})
            self.assertEqual(sum(row['faction_officers'].values()),row['serving'])
            self.assertLess(row['serving'],len(catalog.definitions))
        self.assertIsNone(session.to_dict());self.assertEqual(session.revision,revision)
        self.assertEqual(before,{key:c.data for key,c in session.catalogs.items()})

    def test_live_counts_and_resource_schema_are_read_only_and_roundtrip(self):
        session=self.session();saved=session.export_save();rng=deepcopy(session.game.state.rng)
        expected=faction_officer_counts(session.game.catalog)
        self.assertEqual(session.view()['catalog']['faction_officers'],expected)
        self.assertGreater(len(session.game.state.officers),sum(expected.values())) # Free officers are not faction members.
        for values in faction_resources(session.game.catalog,session.game.state).values():
            self.assertEqual(set(values),{'gold','grain','reserves','cities'})
        session.preview_city('mainland225-07','jianning')
        self.assertEqual(session.export_save(),saved);self.assertEqual(session.game.state.rng,rng)
        session.load_save(saved,session.revision)
        self.assertEqual(session.view()['catalog']['faction_officers'],expected)
        self.assertEqual(session.export_save(),saved)

    def test_in_transit_officers_are_counted_once(self):
        session=self.session();before=session.view()['catalog']['faction_officers']
        ids=session.game.state.cities['shujun'].roster.officer_ids[:2]
        session.command('transfer',dict(source='shujun',target='baxi',officers=ids),session.revision)
        state=session.game.state
        self.assertTrue(set(ids)<=set(state.extension['travel']['marches'][0]['officers']))
        self.assertTrue(set(ids)<=set(state.cities['shujun'].roster.officer_ids))
        self.assertEqual(session.view()['catalog']['faction_officers'],before)
        saved=session.export_save();session.view();self.assertEqual(session.export_save(),saved)

    def test_actual_recruitment_increases_only_the_recruiting_faction(self):
        session=self.session();game=session.game;state=game.state
        city=next(c for c in state.cities.values() if c.owner=='shu' and c.roster.officer_ids and len(c.roster.officer_ids)<game.catalog.rules.city_officer_capacity and game._free_candidates(state,c))
        actor=city.roster.officer_ids[0];candidate=game._free_candidates(state,city)[0]
        before=session.view()['catalog']['faction_officers']
        # Controlled RNG isolates successful recruitment, using actual people and locations.
        state.rng.state=next(seed for seed in range(1,1000) if SeedRng(seed).next()%100<15)
        session.command('recruit_officer',dict(city=city.id,actor=actor,officer=candidate),session.revision)
        after=session.view()['catalog']['faction_officers']
        self.assertEqual(after,{key:count+(key=='shu') for key,count in before.items()})
        self.assertEqual(session.game.state.officers[candidate].faction_id,'shu')
        session.game.validate(session.game.state)

    def test_actual_defection_moves_one_member_between_factions(self):
        session=self.session();game=session.game;state=game.state
        city=next(c for c in state.cities.values() if c.owner=='shu' and c.roster.officer_ids and len(c.roster.officer_ids)<game.catalog.rules.city_officer_capacity and game._persuadable(state,c))
        actor=city.roster.officer_ids[0];candidate=game._persuadable(state,city)[0]
        prior_side=state.officers[candidate].faction_id
        before=session.view()['catalog']['faction_officers']
        state.rng.state=next(seed for seed in range(1,1000) if SeedRng(seed).next()%100<5)
        session.command('persuade_officer',dict(city=city.id,actor=actor,officer=candidate),session.revision)
        after=session.view()['catalog']['faction_officers']
        self.assertEqual(after,{key:count+(key=='shu')-(key==prior_side) for key,count in before.items()})
        self.assertEqual(sum(after.values()),sum(before.values()))
        session.game.validate(session.game.state)

    def test_annual_retirements_remove_dead_members_without_adding_free_births(self):
        session=self.session();game=session.game
        initial={ident:o.faction_id for ident,o in game.state.officers.items() if o.alive and o.faction_id in game.catalog.factions}
        before=session.view()['catalog']['faction_officers']
        # Isolate the real calendar from AI purchases and battles.
        for _ in range(6 * 3):
            game._complete_turn(game.state)
            # Direct calendar stepping omits the transaction's staff cleanup.
            # Expire candidates without generating people or paying salaries.
            civil_staff.synchronize(game, game.state, checks=False)
        self.assertEqual((game.state.year,game.state.month),(218,1))
        retired=Counter(side for ident,side in initial.items() if not game.state.officers[ident].alive)
        self.assertGreater(sum(retired.values()),0)
        self.assertEqual(session.view()['catalog']['faction_officers'],{side:count-retired[side] for side,count in before.items()})
        game.validate(game.state)


if __name__=='__main__':unittest.main()
