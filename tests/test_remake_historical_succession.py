"""Historical nominations at a ruler vacancy use actual campaign membership."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import unittest
from unittest.mock import patch

from remake import dated_events, strategic_ai, succession
from remake.campaign import Campaign, Catalog, GameError, digest


CATALOGS = Path(__file__).resolve().parents[1] / 'game/data/campaigns'


def person(suffix):
    return f'san14-candidate-{suffix:04d}'


@lru_cache(maxsize=None)
def scenario(date):
    return Catalog(CATALOGS / f'{date}.json')


def opening(date, faction):
    game = Campaign(scenario(date))
    game.command('new', dict(faction=faction, seed=2026), 0)
    return game


def vacancy(game, faction):
    previous = game.state.extension['leaders'][faction]
    dated_events._retire(game, game.state, game.state.officers[previous].person_id)
    game._reconcile_factions(game.state)
    return previous


def advance_to(game, year, month, day=1):
    """Advance the real turn calendar while keeping opening city ownership."""
    state = game.state
    while (state.year, state.month, state.day) < (year, month, day):
        game._complete_turn(state)
        game._reconcile_factions(state)


def transfer_member(game, ident, city_id):
    state = game.state
    home = next(city for city in state.cities.values() if ident in city.roster.officer_ids)
    new_home = state.cities[city_id]
    home.roster.officer_ids.remove(ident)
    new_home.roster.officer_ids.append(ident)
    state.officers[ident].faction_id = new_home.owner


class HistoricalSuccessionTests(unittest.TestCase):
    def assert_pending_recruit(self, game, faction, officer, city):
        state = game.state
        pending = state.extension['pending_succession'][faction]
        self.assertEqual(pending['candidates'], [officer])
        self.assertIsNone(pending['provisional'])
        self.assertEqual(pending['recruit'], dict(officer=officer, city=city, declined=[]))
        self.assertEqual(state.extension['leaders'][faction], pending['previous'])
        self.assertFalse(state.officers[pending['previous']].alive)
        self.assertIsNone(state.officers[officer].faction_id)
        self.assertEqual(state.extension['free_locations'][str(officer)], city)
        self.assertNotIn(officer, state.cities[city].roster.officer_ids)

    def test_wei_shu_and_early_wu_prefer_the_eligible_dynastic_successor(self):
        for date, faction, expected in (
            ('190-01', 'wei', 510),       # Cao Cao's eldest Cao Ang is still alive.
            ('219-07', 'wei', 526),       # Cao Pi was formally appointed in 217.
            ('225-07', 'wei', 501),       # Cao Rui succeeds Cao Pi.
            ('221-07', 'shu', 945),       # Liu Shan is already crown prince.
            ('238-01', 'shu', 943),       # Liu Xuan is the designated crown prince.
            ('190-01', 'sun_jian', 557),  # Sun Jian's son Sun Ce.
            ('200-01', 'wu', 553),        # Sun Ce's younger brother Sun Quan.
        ):
            with self.subTest(date=date, faction=faction, expected=expected):
                game = opening(date, faction)
                heir = game.catalog.ids[person(expected)]
                self.assertEqual(game.state.officers[heir].faction_id, faction)
                original_draws = game.state.rng.draws
                vacancy(game, faction)
                pending = game.state.extension['pending_succession'][faction]
                self.assertEqual(pending['candidates'], [heir])
                self.assertEqual(pending['provisional'], heir)
                self.assertEqual(game.state.rng.draws, original_draws)
                game.validate(game.state)

    def test_wei_preserves_seniority_when_the_designated_heir_changes_sides(self):
        game = opening('219-07', 'wei')
        cao_pi = game.catalog.ids[person(526)]
        cao_zhang = game.catalog.ids[person(515)]
        self.assertEqual(game.state.cities['danyang'].owner, 'wu')
        transfer_member(game, cao_pi, 'danyang')
        vacancy(game, 'wei')
        self.assertEqual(game.state.extension['pending_succession']['wei']['candidates'],
                         [cao_zhang])
        self.assertEqual(game.state.officers[cao_pi].faction_id, 'wu')
        game.validate(game.state)

    def test_wei_adopted_heir_can_join_at_the_historical_accession(self):
        game = opening('238-01', 'wei')
        state = game.state
        heir = game.catalog.ids[person(529)]
        self.assertNotIn(heir, state.officers)
        state.year, state.month = 240, 1
        game._monthly_calendar(state)
        self.assertEqual(state.extension['free_locations'][str(heir)], 'henan')
        self.assertEqual(state.cities['henan'].owner, 'wei')
        game._reconcile_factions(state)
        self.assert_pending_recruit(game, 'wei', heir, 'henan')
        self.assertEqual(state.officers[heir].troops, 0)

    def test_historical_free_heir_keeps_a_faction_with_no_other_living_officer(self):
        game = opening('238-01', 'wei')
        state = game.state
        heir = game.catalog.ids[person(529)]
        advance_to(game, 239, 12, 21)
        ruler = state.extension['leaders']['wei']
        self.assertEqual(state.extension['free_locations'][str(heir)], 'henan')
        for officer in state.officers.values():
            if officer.runtime_id != ruler and officer.alive and officer.faction_id == 'wei':
                dated_events._retire(game, state, officer.person_id)
        advance_to(game, 240, 1)
        self.assertFalse(any(officer.alive and officer.faction_id == 'wei'
                             for officer in state.officers.values()))
        self.assertNotIn('wei', state.extension['ended_factions'])
        self.assertEqual(state.cities['henan'].owner, 'wei')
        self.assert_pending_recruit(game, 'wei', heir, 'henan')

        pending_save = game.export_save()
        declined = Campaign(game.catalog)
        declined.load_save(pending_save, 0)
        declined.command('choose_successor', {'officer': heir, 'decline_recruit': True},
                         declined.revision)
        self.assertEqual(declined.state.phase, 'finished')
        self.assertEqual(declined.state.extension['outcome'], 'defeat')
        self.assertIsNone(declined.state.officers[heir].faction_id)

        game.command('choose_successor', {'officer': heir}, game.revision)
        self.assertEqual(game.state.phase, 'city')
        self.assertEqual(game.state.extension['leaders']['wei'], heir)
        self.assertEqual(game.state.officers[heir].faction_id, 'wei')
        self.assertEqual(game.state.cities['henan'].owner, 'wei')

    def test_wu_designations_change_in_each_late_opening(self):
        for date, expected in (
            ('238-01', 570),  # Sun Deng takes priority while alive and designated.
            ('249-01', 542),  # Sun He, not his older brother's former claim.
            ('263-05', 554),  # Sun Hao follows his uncle Sun Xiu.
        ):
            with self.subTest(date=date, expected=expected):
                game = opening(date, 'wei')
                heir = game.catalog.ids[person(expected)]
                self.assertEqual(game.state.officers[heir].faction_id, 'wu')
                vacancy(game, 'wu')
                self.assertEqual(game.state.extension['leaders']['wu'], heir)
                self.assertEqual(game.state.officers[heir].loyalty, 100)
                self.assertNotIn('wu', game.state.extension['pending_succession'])
                game.validate(game.state)

    def test_early_sun_faction_keeps_its_identity_across_two_transitions(self):
        game = opening('190-01', 'sun_jian')
        sun_ce = game.catalog.ids[person(557)]
        sun_quan = game.catalog.ids[person(553)]
        vacancy(game, 'sun_jian')
        game.command('choose_successor', dict(officer=sun_ce), game.revision)
        state = game.state
        self.assertEqual(state.extension['leaders']['sun_jian'], sun_ce)

        state.year, state.month = 200, 4
        game._monthly_calendar(state)
        expected_city = state.cities['wujun']
        self.assertEqual(expected_city.owner, 'neutral')
        self.assertEqual(state.extension['free_locations'][str(sun_quan)], expected_city.id)
        expected_city.owner = 'sun_jian'
        vacancy(game, 'sun_jian')
        self.assert_pending_recruit(game, 'sun_jian', sun_quan, expected_city.id)

    def test_attested_succession_is_used_by_other_opening_powers(self):
        for date, faction, expected in (
            ('190-01', 'liu_yan', 938),
            ('190-01', 'gongsun', 264),
            ('190-01', 'ma_teng', 769),
            ('194-06', 'zhang_ji', 625),
            ('200-01', 'yuan_shao', 34),
            ('207-09', 'liu_biao', 946),
        ):
            with self.subTest(date=date, faction=faction):
                game = opening(date, 'wei')
                heir = game.catalog.ids[person(expected)]
                self.assertEqual(game.state.officers[heir].faction_id, faction)
                vacancy(game, faction)
                self.assertEqual(game.state.extension['leaders'][faction], heir)
                self.assertNotIn(faction, game.state.extension['pending_succession'])
                game.validate(game.state)

    def test_shu_has_no_designated_crown_prince_before_liu_xuan_enters(self):
        game = opening('235-01', 'shu')
        heir = game.catalog.ids[person(943)]
        self.assertNotIn(heir, game.state.officers)
        vacancy(game, 'shu')
        choices = game.state.extension['pending_succession']['shu']['candidates']
        self.assertGreater(len(choices), 1)
        self.assertNotIn(heir, choices)
        game.validate(game.state)

    def test_dead_or_enemy_heir_leaves_the_existing_fallback_available(self):
        for situation in ('dead', 'enemy'):
            with self.subTest(situation=situation):
                game = opening('221-07', 'shu')
                heir = game.catalog.ids[person(945)]
                if situation == 'dead':
                    dated_events._retire(game, game.state, person(945))
                else:
                    self.assertEqual(game.state.cities['henan'].owner, 'wei')
                    transfer_member(game, heir, 'henan')
                vacancy(game, 'shu')
                choices = game.state.extension['pending_succession']['shu']['candidates']
                self.assertGreater(len(choices), 1)
                self.assertNotIn(heir, choices)
                if situation == 'enemy':
                    self.assertEqual(game.state.officers[heir].faction_id, 'wei')
                else:
                    self.assertFalse(game.state.officers[heir].alive)
                game.validate(game.state)

    def test_player_without_a_designated_heir_can_only_choose_serving_blood_relatives(self):
        game = opening('212-12', 'wu')
        sister, cousin = (game.catalog.ids[person(number)] for number in (565, 555))
        outsider = next(i for i, row in game.catalog.by_id.items() if row['name'] == '鲁肃')
        self.assertEqual(game.state.officers[outsider].faction_id, 'wu')
        vacancy(game, 'wu')
        pending = game.state.extension['pending_succession']['wu']
        self.assertEqual(pending['candidates'], [sister, cousin])
        self.assertEqual(pending['provisional'], sister)
        saved = game.export_save()
        restored = Campaign(game.catalog)
        restored.load_save(saved, 0)
        with self.assertRaises(GameError):
            restored.command('choose_successor', {'officer': outsider}, restored.revision)
        restored.command('choose_successor', {'officer': cousin}, restored.revision)
        self.assertEqual(restored.state.extension['leaders']['wu'], cousin)

    def test_ai_prefers_close_family_and_considers_nieces_nephews_and_grandchildren(self):
        game = opening('190-01', 'wei')
        brother, nephew, granddaughter = (game.catalog.ids[person(number)]
                                           for number in (743, 727, 741))
        prev = vacancy(game, 'dong_zhuo')
        self.assertEqual(game.state.extension['leaders']['dong_zhuo'], brother)
        self.assertNotIn('dong_zhuo', game.state.extension['pending_succession'])
        # With the brother gone and the original ruler's vacancy evaluated,
        # both next-of-kin qualify, but an oath or surname alone cannot qualify.
        unrelated = game.catalog.ids[person(987)]  # Lü Bu
        ranks = succession.family_priorities(game.state, prev, [nephew, granddaughter, unrelated])
        self.assertEqual(ranks, {nephew: 1, granddaughter: 1})
        game.validate(game.state)

    def test_sun_liang_can_take_his_historical_accession_when_locally_available(self):
        for location, owner in (('danyang', 'wu'), ('henan', 'wei')):
            with self.subTest(location=location):
                game = opening('249-01', 'wu')
                state = game.state
                heir = game.catalog.ids[person(578)]
                self.assertNotIn(heir, state.officers)
                state.year, state.month = 252, 1
                game._monthly_calendar(state)
                self.assertIsNone(state.officers[heir].faction_id)
                free = state.extension['free_locations']
                self.assertEqual(free[str(heir)], 'danyang')
                self.assertEqual(state.cities[location].owner, owner)
                free[str(heir)] = location
                state.month = 4
                succession.process_ruler_death(game, state)
                game._reconcile_factions(state)
                choices = state.extension['pending_succession']['wu']['candidates']
                if owner == 'wu':
                    self.assert_pending_recruit(game, 'wu', heir, location)
                else:
                    self.assertNotIn(heir, choices)
                    self.assertNotIn('recruit', state.extension['pending_succession']['wu'])
                    self.assertIsNone(state.officers[heir].faction_id)
                    self.assertEqual(free[str(heir)], location)
                self.assertEqual(state.officers[heir].troops, 0)

    def test_sun_quan_dies_in_april_and_sun_liang_can_succeed_in_the_same_turn(self):
        for faction in ('wu', 'observer'):
            with self.subTest(faction=faction):
                game = opening('249-01', faction)
                father, heir = (game.catalog.ids[person(number)] for number in (553, 578))
                advance_to(game, 251, 12, 21)
                self.assertNotIn(heir, game.state.officers)
                advance_to(game, 252, 1)
                self.assertEqual(game.state.extension['free_locations'][str(heir)], 'danyang')
                advance_to(game, 252, 3, 21)
                self.assertTrue(game.state.officers[father].alive)
                with patch.object(strategic_ai, '_open_ai_queue'):
                    if faction == 'observer':
                        game.command('observe_turn', {}, game.revision)
                    else:
                        turn = game.state.turn
                        game.command('end_turn', {}, game.revision)
                        game.command('ai', {'turn': turn}, game.revision)
                self.assertEqual((game.state.year, game.state.month, game.state.day), (252, 4, 1))
                self.assertFalse(game.state.officers[father].alive)
                if faction == 'wu':
                    self.assert_pending_recruit(game, 'wu', heir, 'danyang')
                    pending_save = game.export_save()
                    rejected = Campaign(game.catalog)
                    rejected.load_save(pending_save, 0)
                    self.assertEqual(rejected.export_save(), pending_save)
                    malformed = deepcopy(pending_save)
                    malformed['state']['extension']['pending_succession']['wu']['recruit']['city'] = 'henan'
                    malformed.pop('checksum')
                    malformed['checksum'] = digest(malformed)
                    with self.assertRaises(GameError):
                        rejected.load_save(malformed, rejected.revision)
                    wrong = next(ident for ident, officer in rejected.state.officers.items()
                                 if officer.alive and officer.faction_id == 'wu')
                    with self.assertRaises(GameError):
                        rejected.command('choose_successor', {'officer': wrong}, rejected.revision)
                    with self.assertRaises(GameError):
                        rejected.command('end_turn', {}, rejected.revision)
                    self.assertEqual(rejected.export_save(), pending_save)

                    rejected.command('choose_successor', {'officer': heir, 'decline_recruit': True},
                                     rejected.revision)
                    pending = rejected.state.extension['pending_succession']['wu']
                    self.assertNotIn('recruit', pending)
                    self.assertNotIn(heir, pending['candidates'])
                    self.assertTrue(all(rejected.state.officers[ident].faction_id == 'wu'
                                        for ident in pending['candidates']))
                    self.assertIsNone(rejected.state.officers[heir].faction_id)
                    self.assertEqual(rejected.state.extension['free_locations'][str(heir)], 'danyang')
                    rejected.command('choose_successor', {'officer': pending['candidates'][0]},
                                     rejected.revision)

                    city = game.state.cities['danyang']
                    money_and_troops = (city.gold, city.grain, city.reserves)
                    draws = game.state.rng.draws
                    game.command('choose_successor', {'officer': heir}, game.revision)
                    city = game.state.cities['danyang']
                    self.assertEqual((city.gold, city.grain, city.reserves), money_and_troops)
                    self.assertEqual(game.state.rng.draws, draws)
                self.assertEqual(game.state.extension['leaders']['wu'], heir)
                self.assertEqual(game.state.officers[heir].faction_id, 'wu')
                self.assertNotIn(str(heir), game.state.extension['free_locations'])
                self.assertNotIn('wu', game.state.extension['pending_succession'])
                events = [row for row in game.state.extension['events']['items'] if row['kind'] == 'succession']
                self.assertEqual(sum(row['person_ids'] == [person(578)] for row in events), 1)
                self.assertEqual(events[-1]['person_ids'], [person(578)])
                self.assertEqual(events[-1]['details']['previous'], person(553))

    def test_sun_deng_appears_in_his_designation_year(self):
        game = opening('221-07', 'wu')
        heir = game.catalog.ids[person(570)]
        self.assertEqual(game.catalog.definitions[person(570)].service_year, 221)
        advance_to(game, 221, 10)
        self.assertNotIn(heir, game.state.officers)
        advance_to(game, 221, 11)
        self.assertEqual(game.state.extension['free_locations'][str(heir)], 'danyang')
        vacancy(game, 'wu')
        self.assert_pending_recruit(game, 'wu', heir, 'danyang')

    def test_unlimited_lifespan_keeps_sun_quan_on_the_throne(self):
        game = Campaign(scenario('249-01'))
        game.command('new', {'faction': 'wu', 'seed': 2026, 'lifespan': 'none'}, 0)
        father, heir = (game.catalog.ids[person(number)] for number in (553, 578))
        advance_to(game, 252, 4)
        self.assertTrue(game.state.officers[father].alive)
        self.assertEqual(game.state.extension['leaders']['wu'], father)
        self.assertIsNone(game.state.officers[heir].faction_id)

    def test_old_mid_252_save_loads_and_joins_the_new_calendar(self):
        with patch.object(succession, 'apply_appearance_corrections', return_value={}), \
                patch.object(succession, 'process_ruler_death'):
            old_catalog = Catalog(CATALOGS / '249-01.json')
            old_game = Campaign(old_catalog)
            old_game.command('new', {'faction': 'wu', 'seed': 2026}, 0)
            advance_to(old_game, 252, 4, 21)
            old_save = old_game.export_save()
            self.assertTrue(old_game.state.officers[old_catalog.ids[person(553)]].alive)
            self.assertNotIn(old_catalog.ids[person(578)], old_game.state.officers)
            advance_to(old_game, 253, 1)
            old_game.command('choose_successor', {'officer': old_catalog.ids[person(578)]},
                             old_game.revision)
            old_later_save = old_game.export_save()
        father, heir = (old_catalog.ids[person(number)] for number in (553, 578))
        new_game = Campaign(scenario('249-01'))
        self.assertEqual(old_catalog.sha256, new_game.catalog.sha256)
        new_game.load_save(old_save, 0)
        self.assertIn(f'service_eligible:{person(578)}:252', new_game.state.year_events)
        self.assertEqual(new_game.state.extension['leaders']['wu'], father)
        advance_to(new_game, 252, 5)
        self.assert_pending_recruit(new_game, 'wu', heir, 'danyang')
        new_game.validate(new_game.state)
        new_game.load_save(old_later_save, new_game.revision)
        self.assertIn(f'service_eligible:{person(578)}:252', new_game.state.year_events)
        self.assertNotIn(f'service_eligible:{person(578)}:253', new_game.state.year_events)
        self.assertEqual(new_game.state.extension['leaders']['wu'], heir)

    def test_existing_confirmation_command_and_saves_preserve_the_designated_heir(self):
        game = opening('221-07', 'shu')
        heir = game.catalog.ids[person(945)]
        other = next(ident for ident, officer in game.state.officers.items()
                     if officer.faction_id == 'shu' and ident not in
                     {heir, game.state.extension['leaders']['shu']})
        previous = vacancy(game, 'shu')
        initial_hash = game.catalog.sha256
        pending_save = game.export_save()
        with self.assertRaises(GameError):
            game.command('choose_successor', dict(officer=other), game.revision)
        self.assertEqual(game.export_save(), pending_save)

        restored = Campaign(game.catalog)
        restored.load_save(pending_save, 0)
        self.assertEqual(restored.export_save(), pending_save)
        restored.command('choose_successor', dict(officer=heir), restored.revision)
        self.assertNotIn('shu', restored.state.extension['pending_succession'])
        self.assertEqual(restored.state.extension['leaders']['shu'], heir)
        self.assertEqual(restored.catalog.sha256, initial_hash)
        row = restored.state.extension['events']['items'][-1]
        self.assertEqual(row['kind'], 'succession')
        self.assertEqual(row['person_ids'], [person(945)])
        self.assertEqual(row['details']['previous'], restored.state.officers[previous].person_id)
        final_save = restored.export_save()
        loaded = Campaign(restored.catalog)
        loaded.load_save(final_save, 0)
        self.assertEqual(loaded.export_save(), final_save)
