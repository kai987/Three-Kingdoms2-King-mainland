"""Historical depositions use the ordinary monthly command and save path."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake import succession_depositions
from remake.campaign import Campaign, Catalog
from campaign_fixtures import controlled_catalog


WEI = (254, 'wei', 'san14-candidate-0529', 'san14-candidate-0346', 'san14-candidate-0530')
WU = (258, 'wu', 'san14-candidate-0578', 'san14-candidate-0569', 'san14-candidate-0548')


class HeadlessCampaign(Campaign):
    def view(self):
        return dict(revision=self.revision)


def court(rule, *, regent_side=None, successor_side=None):
    year, faction, ruler, regent, successor = rule
    data = controlled_catalog().data
    homes = {row['id']: row['city'] for row in data['factions']}
    officers = data['initial_officers']
    for row in officers:
        if row['city'] == homes[faction] and row['ruler']:
            row['person_id'] = ruler
    officers.append(dict(person_id=regent, city=homes[regent_side or faction], troops=0,
                         ruler=False, resolve_death_year=True))
    if successor_side is None:
        data['initial_free_officers'] = [dict(person_id=successor, city=homes[faction])]
    else:
        officers.append(dict(person_id=successor, city=homes[successor_side], troops=0, ruler=False))
    data['appearance_locations'] = {row['person_id']: row['city']
                                    for row in officers + data['initial_free_officers']}
    # Isolate the accession from unrelated mortality and AI orders.
    people = {row['person_id']: row for row in data['people']}
    for row in officers:
        if row['person_id'] not in {ruler, regent, successor}:
            people[row['person_id']]['death_year'] = 300
    data['faction_rulers'][faction] = people[ruler]['runtime_id']
    data.update(id=f'controlled-deposition-{year}', start_year=year, start_month=9,
                travel_routes=[], links=[])
    for row in data['factions']:
        if row['id'] == faction:
            row['captain'] = people[ruler]['name']
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'court.json'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        game = HeadlessCampaign(Catalog(path))
    game.command('new', dict(faction=faction, seed=2026), 0)
    return game


def tick(game):
    turn = game.state.turn
    game.command('end_turn', {}, game.revision)
    game.command('ai', dict(turn=turn), game.revision)


def successions(game):
    return [event for event in game.state.extension['events']['items'] if event['kind'] == 'succession']


class HistoricalDepositionsTests(unittest.TestCase):
    def test_both_accessions_fire_once_in_october_and_keep_the_former_ruler_alive(self):
        for rule in (WEI, WU):
            with self.subTest(rule=rule):
                year, faction, ruler, _, successor = rule
                game = court(rule)
                ruler_id, successor_id = (game.catalog.ids[person] for person in (ruler, successor))
                tick(game)
                tick(game)
                self.assertEqual(game.state.extension['leaders'][faction], ruler_id)
                self.assertEqual(successions(game), [])
                before = game.export_save()
                loaded = HeadlessCampaign(game.catalog)
                loaded.load_save(before, 0)
                process = succession_depositions.process

                def unchanged_ledger(campaign, candidate):
                    ledger = candidate.soldiers.copy()
                    draws = candidate.rng.draws
                    process(campaign, candidate)
                    self.assertEqual(candidate.soldiers, ledger)
                    self.assertEqual(candidate.rng.draws, draws)

                with patch.object(succession_depositions, 'process', side_effect=unchanged_ledger):
                    tick(game)
                tick(loaded)
                state = game.state
                self.assertEqual((state.year, state.month, state.day), (year, 10, 1))
                self.assertEqual(state.extension['leaders'][faction], successor_id)
                self.assertFalse(state.extension['pending_succession'])
                self.assertEqual((state.officers[ruler_id].alive, state.officers[ruler_id].faction_id),
                                 (True, faction))
                self.assertLess(state.officers[ruler_id].loyalty, 100)
                self.assertEqual(state.officers[successor_id].loyalty, 100)
                entries = successions(game)
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]['person_ids'], [successor])
                self.assertEqual(entries[0]['details'], {'previous': ruler})
                self.assertEqual(game.export_save(), loaded.export_save())
                tick(game)
                self.assertEqual(successions(game), entries)

    def test_changed_court_or_enemy_nominee_blocks_a_deposition(self):
        for options in (dict(regent_side='shu'), dict(successor_side='shu')):
            with self.subTest(options=options):
                game = court(WU, **options)
                for _ in range(3):
                    tick(game)
                self.assertEqual(game.state.extension['leaders']['wu'], game.catalog.ids[WU[2]])
                self.assertEqual(successions(game), [])
                if 'successor_side' in options:
                    self.assertEqual(game.state.officers[game.catalog.ids[WU[4]]].faction_id, 'shu')

    def test_a_marching_ruler_or_nominee_is_ineligible(self):
        game = court(WEI, successor_side='wei')
        game.state.month = 10
        for person in (WEI[2], WEI[4]):
            with self.subTest(person=person), patch.object(game, '_march_ids', return_value={game.catalog.ids[person]}):
                succession_depositions.process(game, game.state)
                self.assertEqual(game.state.extension['leaders']['wei'], game.catalog.ids[WEI[2]])
