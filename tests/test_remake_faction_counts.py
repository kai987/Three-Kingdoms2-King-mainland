"""Displayed faction membership must follow actual playable rosters and actions."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import SeedRng
from remake import civil_staff
from remake.officers import OFFICER_TROOP_CAP
from remake.session import CampaignSession,faction_officer_counts,faction_resources
from remake import capital_openings
from remake.starting_garrisons import mobilize_reserves
from remake.view_transport import ViewTransport
from campaign_fixtures import controlled_catalog


class FactionOfficerCountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
        if index['schema']!='tk2-campaign-index-v1' or len(index['catalogs'])!=29:
            raise AssertionError('Expected29 current campaign catalogs')
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
            stocks, troop_plan = catalog.opening_garrisons
            baseline_stocks, baseline_plan = mobilize_reserves(catalog)
            for city, stock in stocks.items():
                capital = capital_openings.opening(catalog.data, city)
                self.assertEqual(stock, {field: capital.get(field, value) for field, value in baseline_stocks[city].items()})
            expected_troops = Counter()
            baseline_troops = Counter()
            for member in catalog.data['initial_officers']:
                owner = catalog.data['initial_owners'][member['city']]
                person = member['person_id']
                self.assertLessEqual(troop_plan[person], OFFICER_TROOP_CAP, (row['id'], person))
                if capital_openings.opening(catalog.data, member['city']).get('troop_percent', 100) >= 100:
                    self.assertGreaterEqual(troop_plan[person], baseline_plan[person], (row['id'], person))
                expected_troops[owner] += troop_plan[person]
                baseline_troops[owner] += baseline_plan[person]
            for side, resources in row['faction_resources'].items():
                self.assertEqual(resources['troops'], expected_troops[side], (row['id'], side))
                if baseline_troops[side]:
                    self.assertGreater(resources['troops'], sum(baseline_plan[m['person_id']] * capital_openings.opening(catalog.data, m['city']).get('troop_percent', 100) // 100 for m in catalog.data['initial_officers'] if catalog.data['initial_owners'][m['city']] == side), (row['id'], side))
                else:
                    self.assertEqual(resources['troops'], 0, (row['id'], side))
            if row['id'] == 'mainland200-01':
                self.assertLess(baseline_troops['yuan_shao'], baseline_troops['wei'])
                self.assertGreater(expected_troops['yuan_shao'], expected_troops['wei'])
        self.assertIsNone(session.to_dict());self.assertEqual(session.revision,revision)
        self.assertEqual(before,{key:c.data for key,c in session.catalogs.items()})

    def test_live_counts_and_resource_schema_are_read_only_and_roundtrip(self):
        session=self.session();saved=session.export_save();rng=deepcopy(session.game.state.rng)
        expected=faction_officer_counts(session.game.catalog)
        self.assertEqual(session.view()['catalog']['faction_officers'],expected)
        self.assertGreater(len(session.game.state.officers),sum(expected.values())) # Free officers are not faction members.
        opening = faction_resources(session.game.catalog)
        self.assertEqual(session.view()['catalog']['faction_resources'], opening)
        for values in opening.values():
            self.assertEqual(set(values), {'gold', 'grain', 'reserves', 'cities', 'troops'})
        session.preview_city('mainland225-07','jianning')
        self.assertEqual(session.export_save(),saved);self.assertEqual(session.game.state.rng,rng)
        session.load_save(saved,session.revision)
        self.assertEqual(session.view()['catalog']['faction_officers'],expected)
        self.assertEqual(session.view()['catalog']['faction_resources'], opening)
        self.assertEqual(session.export_save(),saved)

    def test_existing_save_keeps_preincrease_troops_on_load(self):
        path=ROOT/'game/data/campaigns/200-01.json'
        previous=CampaignSession([path])
        with patch('remake.campaign.resolve_opening_garrisons', mobilize_reserves):
            before=previous.command('new', dict(faction='wei', seed=2026), 0)
        save=previous.export_save()

        current=CampaignSession([path])
        current.load_save(save, 0)
        self.assertEqual(current.export_save(), save)
        self.assertEqual(current.view()['catalog']['faction_resources'], before['catalog']['faction_resources'])
        opening=current.command('new', dict(faction='wei', seed=2026), current.revision)['catalog']
        self.assertEqual(opening['faction_resources']['yuan_shao']['troops'], 52892)
        self.assertEqual(opening['faction_resources']['wei']['troops'], 49553)

    def test_in_transit_officers_are_counted_once(self):
        session=self.session();before=session.view()['catalog']
        ids=session.game.state.cities['shujun'].roster.officer_ids[:2]
        session.command('transfer',dict(source='shujun',target='baxi',officers=ids),session.revision)
        state=session.game.state
        self.assertTrue(set(ids)<=set(state.extension['travel']['marches'][0]['officers']))
        self.assertTrue(set(ids)<=set(state.cities['shujun'].roster.officer_ids))
        current = session.view()['catalog']
        self.assertEqual(current['faction_officers'], before['faction_officers'])
        for side, resources in current['faction_resources'].items():
            self.assertEqual(resources['troops'], before['faction_resources'][side]['troops'])
        saved=session.export_save();session.view();self.assertEqual(session.export_save(),saved)

    def test_active_troops_follow_allocation_and_live_battle_losses(self):
        catalog = controlled_catalog()
        with patch('remake.session.Catalog', return_value=catalog):
            session = CampaignSession([ROOT/'controlled.json'])
        transport = ViewTransport()
        opening = transport.pack(session.view(), catalog.sha256)
        preview = opening['static_catalog']['scenarios'][0]['faction_resources']
        initial = session.command('new', dict(faction='shu', seed=2026), 0)['catalog']['faction_resources']
        self.assertEqual(initial, preview)

        game = session.game
        source = game.state.cities['xiangyang']
        actor, second = source.roster.officer_ids[:2]
        result = session.command('allocate', dict(city=source.id, officer=actor, troops=240), session.revision)
        allocated = result['catalog']['faction_resources']
        self.assertEqual(allocated['shu']['troops'], initial['shu']['troops'] + 60)
        self.assertEqual(allocated['shu']['reserves'], initial['shu']['reserves'] - 60)

        state = game.state
        game._start_expanded_battle(state, state.cities[source.id], state.cities['nanyang'], [actor, second])
        battle = state.battle
        # One routed formation and one damaged formation exercise both zero
        # and positive live troop counts before their post-battle writeback.
        routed = battle['attackers'][1]
        routed['troops'] = 0
        battle['defenders'][0]['troops'] -= 17
        game.validate(state)
        expected = {
            'shu': allocated['shu']['troops'] - state.officers[routed['id']].troops,
            'wei': allocated['wei']['troops'] - 17,
            'wu': allocated['wu']['troops'],
        }
        live = transport.pack(session.view(), catalog.sha256, opening['catalog_token'])
        self.assertNotIn('static_catalog', live)
        resources = live['view']['catalog']['faction_resources']
        self.assertEqual({side: row['troops'] for side, row in resources.items()}, expected)

        payload = dict(battle_id=battle['id'])
        for command in ('retreat', 'settle'):
            result = session.command(command, payload, session.revision)
            resources = result['catalog']['faction_resources']
            self.assertEqual({side: row['troops'] for side, row in resources.items()}, expected)

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
