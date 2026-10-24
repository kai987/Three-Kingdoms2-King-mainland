"""Civil employees exercised through real campaign transactions and saves.

The controlled geography keeps historical identities/profiles from the current
catalog. Direct setup is confined to otherwise impractical capacity/defeat
boundaries; the operations under test are the same atomic game commands.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, digest
from remake.errors import GameError
from remake import domestic, equipment, treasures
from remake.officers import YearState, initialize_officer, year_state
from campaign_fixtures import controlled_catalog


FREE_PERSON = 'san14-candidate-0001'


def staff_catalog(*, free=True, extra=False, enemy=False):
    data = deepcopy(controlled_catalog().data)
    data.update(id='controlled-civil-staff', title='地方文吏集成測試')
    active = data['active_cities']
    active.append('yingchuan')
    data['initial_owners'].update(nanjun='wei' if enemy else 'shu', yingchuan='wei')
    if extra:
        active.append('runan')
        data['initial_owners']['runan'] = 'shu'
    if not enemy:
        data['initial_officers'] = [r for r in data['initial_officers'] if r['person_id'] != FREE_PERSON]
    data['initial_free_officers'] = ([dict(person_id=FREE_PERSON, city='nanjun')]
                                     if free and not enemy else [])
    data['initial_city_resources'] = {key: dict(gold=1200, grain=3800, reserves=1200) for key in active}
    data['city_income'] = {key: dict(gold=35, grain=90, reserves=0) for key in active}
    # Prevent unrelated persuasion rolls from masking the staff/global RNG split.
    data['rules']['persuade_officer_gold'] = 100000000
    pairs = [('yingchuan', 'nanjun' if enemy else 'nanyang')]
    if extra:
        pairs.append(('runan', 'xiangyang'))
    for a, b in pairs:
        data['links'].append([a, b])
        data['travel_routes'].append(dict(id=f'civil-staff:{a}:{b}', **{'from': a, 'to': b},
            mode='land', terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'civil-staff.json'
        path.write_text(json.dumps(data, ensure_ascii=False))
        return Catalog(path)


class CivilStaffCampaignTests(unittest.TestCase):
    def new(self, *, player='shu', **options):
        game = Campaign(staff_catalog(**options))
        game.command('new', dict(faction=player, seed=2026), 0)
        return game

    def cmd(self, game, kind, **payload):
        return game.command(kind, payload, game.revision)

    def step(self, game):
        """Run one real player/AI旬, including due noncombat arrivals."""
        if game.state.phase == 'arrivals':
            self.cmd(game, 'arrivals')
        self.assertEqual(game.state.phase, 'city')
        turn = game.state.turn
        self.cmd(game, 'end_turn')
        for _ in range(30):
            if game.state.phase != 'ai':
                break
            self.cmd(game, 'ai', turn=turn)
        self.assertEqual(game.state.turn, turn + 1)
        if game.state.phase == 'arrivals':
            self.cmd(game, 'arrivals')
        game.validate(game.state)

    def pool(self, game):
        return game.state.extension['civil_staff']

    def hire(self, game, city='nanjun'):
        candidate = self.pool(game)['cities'][city]['candidate']
        self.assertIsNotNone(candidate)
        ident = candidate['id']
        self.cmd(game, 'hire_staff', city=city, candidate=ident)
        return ident

    def fails_atomically(self, game, kind, payload, *, revision=None):
        before, cursor, journal = game.export_save(), game.revision, deepcopy(game.journal)
        with self.assertRaises((GameError, ValueError)):
            game.command(kind, payload, cursor if revision is None else revision)
        self.assertEqual(game.export_save(), before)
        self.assertEqual(game.revision, cursor)
        self.assertEqual(game.journal, journal)

    def fill(self, game, city, historical_count):
        """Populate with eligible real IDs and zero troops, preserving the ledger."""
        target = game.state.cities[city]
        for ident, row in game.catalog.by_id.items():
            if sum(type(i) is int for i in target.roster.officer_ids) >= historical_count:
                break
            person = game.catalog.definitions[row['person_id']]
            if ident in game.state.officers or year_state(person, game.state.year) not in {
                    YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW}:
                continue
            game.state.officers[ident] = initialize_officer(person, ident,
                game.catalog.profiles[ident], year=game.state.year,
                faction_id=target.owner, loyalty=80, troops=0,
                resolve_death_year=True, rules=game.catalog.rules)
            target.roster.officer_ids.append(ident)
        self.assertEqual(sum(type(i) is int for i in target.roster.officer_ids), historical_count)
        treasures.synchronize(game,game.state)
        if 'equipment' in game.state.extension:
            equipment.synchronize(game, game.state)
        game.validate(game.state)

    def test_all_current_actual_openings_keep_historical_ids_and_offer_only_owned_empty_cities(self):
        index = json.loads((ROOT / 'game/data/campaigns/index.json').read_text())
        self.assertEqual(len(index['catalogs']), 29)
        for filename in index['catalogs']:
            with self.subTest(scenario=filename):
                game = Campaign(Catalog(ROOT / 'game/data' / filename))
                faction = next(iter(game.catalog.factions))
                skeleton = game._new(faction, 2026)
                self.cmd(game, 'new', faction=faction, seed=2026)
                expected = {key for key, city in skeleton.cities.items()
                            if city.owner != 'neutral' and not city.roster.officer_ids}
                actual = {key for key, row in self.pool(game)['cities'].items() if row['candidate']}
                self.assertEqual(actual, expected)
                self.assertEqual(game.state.officers, skeleton.officers)
                self.assertEqual(game.state.rng, skeleton.rng)
                self.assertEqual(len(game.catalog.definitions), 1023)
                self.assertTrue(all(type(ident) is int for ident in game.state.officers))
                self.assertEqual(game.state.extension['events']['items'][0]['kind'], 'campaign_start')
                game.validate(game.state)

    def test_zero_officer_city_hires_once_without_actor_and_rejects_stale_nonce_or_revision(self):
        game = self.new()
        self.assertEqual(game.state.cities['nanjun'].roster.officer_ids, [])
        candidate = self.pool(game)['cities']['nanjun']['candidate']['id']
        self.fails_atomically(game, 'hire_staff', dict(city='nanjun', candidate='clerk-999999'))
        game.state.cities['nanjun'].gold = 59
        self.fails_atomically(game, 'hire_staff', dict(city='nanjun', candidate=candidate))
        game.state.cities['nanjun'].gold = 1200
        historical, combat_rng = deepcopy(game.state.officers), deepcopy(game.state.rng)
        ledger, revision = deepcopy(game.state.soldiers), game.revision
        ident = self.hire(game)
        self.assertEqual(game.state.cities['nanjun'].gold, 1140)
        self.assertTrue(game.state.cities['nanjun'].action_used)
        self.assertEqual({i:o for i,o in game.state.officers.items() if type(i) is int}, historical)
        self.assertIn(ident, game.state.officers)
        self.assertEqual(game.state.rng, combat_rng)
        self.assertEqual(game.state.soldiers, ledger)
        self.assertEqual(self.pool(game)['people'][ident]['troops'], 0)
        self.fails_atomically(game, 'hire_staff', dict(city='nanjun', candidate=candidate), revision=revision)
        self.fails_atomically(game, 'hire_staff', dict(city='nanjun', candidate=candidate))

    def test_clerk_uses_original_recruitment_formula_and_only_actual_attempt_draws_combat_rng(self):
        game = self.new()
        ident = self.hire(game)
        target = game.catalog.ids[FREE_PERSON]
        payload = dict(city='nanjun', actor=ident, officer=target)
        self.fails_atomically(game, 'staff_recruit', payload)
        self.step(game)
        person = self.pool(game)['people'][ident]
        candidate = game.state.officers[target]
        chance = max(15, min(95, 35 + person['profile']['virtue']//2 +
            person['profile']['intellect']//5 - candidate.profile.virtue//5))
        expected_rng = deepcopy(game.state.rng)
        expected_success = expected_rng.next() % 100 < chance
        own_rng, gold = deepcopy(self.pool(game)['rng']), game.state.cities['nanjun'].gold
        self.cmd(game, 'staff_recruit', **payload)
        self.assertEqual(game.state.rng, expected_rng)
        self.assertEqual(self.pool(game)['rng'], own_rng)
        self.assertEqual(game.state.cities['nanjun'].gold, gold - 60)
        self.assertEqual(game.state.officers[target].faction_id, 'shu' if expected_success else None)
        self.assertEqual(self.pool(game)['people'][ident]['action_turn'], game.state.turn)
        event = game.state.extension['events']['items'][-1]
        self.assertEqual(event['kind'], 'recruit_success' if expected_success else 'recruit_failure')
        self.assertEqual(event['details']['actor'], ident, 'Generated actors retain their independent person reference')
        self.fails_atomically(game, 'staff_recruit', payload)

    def test_save_restore_keeps_next_staff_rng_candidate_and_real_turn_results(self):
        game = self.new(free=False)
        self.hire(game)
        save = game.export_save()
        twin = Campaign(game.catalog)
        twin.load_save(save, 0)
        self.assertEqual(twin.export_save(), save)
        for _ in range(9):
            self.step(game)
            self.step(twin)
            self.assertEqual(game.export_save(), twin.export_save())
        self.assertGreater(self.pool(game)['rng']['draws'], 0, 'Monthly shortage generation actually exercised its independent stream')
        self.assertEqual(game.state.rng.draws, 0)

    def test_rejection_expiry_and_signed_but_tampered_saves_are_atomic(self):
        game = self.new(free=False, extra=True)
        candidate = self.pool(game)['cities']['nanjun']['candidate']['id']
        self.cmd(game, 'reject_staff', city='nanjun', candidate=candidate)
        self.assertEqual(game.state.cities['nanjun'].gold, 1200)
        self.assertFalse(game.state.cities['nanjun'].action_used)
        self.fails_atomically(game, 'hire_staff', dict(city='nanjun', candidate=candidate))
        held = self.pool(game)['cities']['runan']['candidate']['id']
        for _ in range(9):
            self.step(game)
        self.assertIsNone(self.pool(game)['cities']['runan']['candidate'])
        self.fails_atomically(game, 'hire_staff', dict(city='runan', candidate=held))
        self.assertTrue(any(e['kind'] == 'staff_expired' and e['details']['staff_id'] == held
                            for e in game.state.extension['events']['items']))
        other = self.new()
        self.hire(other)
        for mutation in ('virtue', 'historical_id', 'troops', 'rng', 'payroll'):
            with self.subTest(mutation=mutation):
                save = other.export_save()
                pool = save['state']['extension']['civil_staff']
                employee = next(iter(pool['people'].values()))
                if mutation == 'virtue': employee['profile']['virtue'] = 99
                elif mutation == 'historical_id': employee['id'] = str(next(iter(other.state.officers)))
                elif mutation == 'troops': employee['troops'] = 1
                elif mutation == 'rng': pool['rng']['draws'] = -1
                else: pool['last_payroll_month'] += 1
                save['checksum'] = digest({k: v for k, v in save.items() if k != 'checksum'})
                before, revision = other.export_save(), other.revision
                with self.assertRaises(GameError): other.load_save(save, revision)
                self.assertEqual(other.export_save(), before)
                self.assertEqual(other.revision, revision)

    def test_monthly_salary_is_one_player_summary_and_income_and_soldiers_reconcile(self):
        game = self.new(free=False, extra=True)
        self.hire(game, 'nanjun')
        self.hire(game, 'runan')
        owned = [c for c in game.state.cities.values() if c.owner == 'shu']
        before = {field: sum(getattr(c, field) for c in owned) for field in ('gold', 'grain', 'reserves')}
        for _ in range(3): self.step(game)
        salaries = [e for e in game.state.extension['events']['items'] if e['kind'] == 'staff_salary']
        self.assertEqual(len(salaries), 1)
        event = salaries[0]
        self.assertEqual(event['factions'], ['shu'])
        self.assertEqual(len(event['city_ids']), 1)
        details = event['details']
        self.assertEqual(details['counts'], dict(staff=2, total_unpaid=0, cities=2))
        self.assertEqual((details['amount'], details['paid']), (10, 10))
        for field in before:
            current = sum(getattr(game.state.cities[c.id], field) for c in owned)
            base = sum(game.catalog.data['city_income'][c.id][field] for c in owned)
            self.assertEqual(current, before[field] + base + details['bonus'][field] - (10 if field == 'gold' else 0))
        frozen = game.export_save()
        for _ in range(3): game.view(); game.export_save()
        self.assertEqual(game.export_save(), frozen)
        game.validate(game.state)

    def test_actual_ai_hires_and_clerk_recruits_with_the_same_cost_and_rng(self):
        game = self.new(player='wu', free=False)
        # The faction military official can now recruit even in an empty city.
        # A satisfied reserve target isolates the actual AI hiring/personnel
        # commands from that independent city-action competitor.
        domestic.appointments(game.state, 'shu')['policy']['reserve_target'] = 0
        local_soldiers = game.state.cities['nanjun'].reserves
        self.step(game)
        people = self.pool(game)['people']
        clerk = next(p for p in people.values() if p['city'] == 'nanjun')
        training = sum(r['details']['gold'] for r in game.state.extension['domestic']['reports']
            if r['city'] == 'nanjun' and r['turn'] == game.state.turn - 1 and r['kind'] == 'training')
        self.assertEqual(game.state.cities['nanjun'].gold, 1200 - 60 - training)
        self.assertTrue(any(r['action'] == 'hire_staff' and r['city'] == 'nanjun'
                            for r in game.state.extension['ai_reports']))
        self.assertEqual(game.state.officers[clerk['id']].troops, 999,
                         'The shared military official fills a hired defender to the normal troop cap')
        self.assertEqual(game.state.cities['nanjun'].reserves, local_soldiers - 999)
        self.assertEqual(game.state.rng.draws, 0)
        # Explicitly give the generated officer the one faction civil post.
        # Leaving the best historical appointee in that post would correctly
        # have that person perform the remote recruitment instead of the clerk.
        domestic.set_policy(game, game.state, dict(faction='shu', civil=clerk['id']), 'shu')
        target = game.catalog.ids[FREE_PERSON]
        game.state.officers[target] = initialize_officer(game.catalog.definitions[FREE_PERSON], target,
            game.catalog.profiles[target], year=game.state.year, rules=game.catalog.rules)
        game.state.extension['free_locations'][str(target)] = 'nanjun'
        if 'equipment' in game.state.extension:
            equipment.synchronize(game, game.state)
        game.validate(game.state)
        gold = game.state.cities['nanjun'].gold
        self.step(game)
        training = sum(r['details']['gold'] for r in game.state.extension['domestic']['reports']
            if r['city'] == 'nanjun' and r['turn'] == game.state.turn - 1 and r['kind'] == 'training')
        self.assertEqual(game.state.cities['nanjun'].gold, gold - 60 - training,
                         'Shared reserve assignment does not charge the former AI-only top-up fee')
        self.assertEqual(game.state.officers[clerk['id']].troops, 999)
        self.assertEqual(game.state.rng.draws, 1)
        self.assertEqual(game.state.officers[target].faction_id, 'shu')
        self.assertEqual(game.state.officers[target].troops, local_soldiers - 999,
                         'The newly recruited historical officer receives the remaining local reserves')
        self.assertEqual(game.state.cities['nanjun'].reserves, 0)
        self.assertEqual(sum(game.state.officers[i].troops
                            for i in game.state.cities['nanjun'].roster.officer_ids), local_soldiers,
                         'Hiring, personnel work and reserve assignment preserve local soldiers')
        self.assertEqual(self.pool(game)['people'][clerk['id']]['action_turn'], game.state.turn - 1)
        self.assertTrue(any(r['action'] in {'staff_recruit','recruit_officer'} and r['city'] == 'nanjun'
                            for r in game.state.extension['ai_reports']))
        self.assertFalse(any(e['kind'].startswith('staff_') for e in game.state.extension['events']['items']),
                         'Remote AI paperwork must not flood the player event window')

    def test_combined_99_capacity_blocks_historical_and_clerk_recruitment_and_transfers(self):
        game = self.new()
        clerk = self.hire(game)
        self.fill(game, 'nanjun', 98)
        game.state.cities['nanjun'].action_used = False
        target = game.catalog.ids[FREE_PERSON]
        actor = game.state.cities['nanjun'].roster.officer_ids[0]
        for kind, payload in [
                ('recruit_officer', dict(city='nanjun', actor=actor, officer=target)),
                ('staff_recruit', dict(city='nanjun', actor=clerk, officer=target)),
                ('transfer', dict(source='xiangyang', target='nanjun', officers=[146]))]:
            with self.subTest(command=kind): self.fails_atomically(game, kind, payload)
        self.assertEqual(game._city_occupancy(game.state, game.state.cities['nanjun']), 99)

    def test_previously_queued_transfer_waits_when_recruitment_fills_the_last_combined_slot(self):
        game = self.new()
        self.hire(game)
        self.fill(game, 'nanjun', 97)
        game.state.cities['nanjun'].action_used = False
        self.cmd(game, 'transfer', source='xiangyang', target='nanjun', officers=[146])
        actor = game.state.cities['nanjun'].roster.officer_ids[0]
        target = game.catalog.ids[FREE_PERSON]
        self.cmd(game, 'recruit_officer', city='nanjun', actor=actor, officer=target)
        self.assertEqual(game.state.officers[target].faction_id, 'shu')
        self.assertEqual(game._city_occupancy(game.state, game.state.cities['nanjun']), 99)
        soldiers = deepcopy(game.state.soldiers)
        self.step(game)
        waiting = [m for m in game.state.extension['travel']['marches'] if 146 in m['officers']]
        self.assertEqual(len(waiting), 1)
        self.assertLessEqual(waiting[0]['arrival_turn'], game.state.turn)
        self.assertEqual(waiting[0]['checked_turn'], game.state.turn)
        self.assertIn(146, game.state.cities['xiangyang'].roster.officer_ids)
        self.assertNotIn(146, game.state.cities['nanjun'].roster.officer_ids)
        self.assertEqual(game.state.soldiers, soldiers)
        game.validate(game.state)

    def test_defeated_historical_officer_cannot_escape_into_98_officers_plus_one_clerk(self):
        game = self.new(enemy=True, free=False)
        # Keep the capacity fixture focused on a real hired clerk. Otherwise
        # global military recruitment legally consumes this empty city's action
        # before the central civil official can hire the candidate.
        domestic.appointments(game.state, 'wei')['policy']['reserve_target'] = 0
        self.step(game)
        self.assertEqual(sum(p['city'] == 'yingchuan' for p in self.pool(game)['people'].values()), 1)
        self.cmd(game, 'allocate', city='xiangyang', officer=146, troops=999)
        self.cmd(game, 'depart', source='xiangyang', target='nanjun', officers=[146])
        self.step(game)
        self.assertEqual(game.state.phase, 'battle')
        self.fill(game, 'yingchuan', 98)
        # Wound the actual defending battle unit so one real attack/settlement
        # reaches the escape boundary, without altering its reserved start ledger.
        battle = game.state.battle
        battle['defenders'][0]['troops'] = 1
        game.validate(game.state)
        defender = battle['defenders'][0]['id']
        self.cmd(game, 'attack', battle_id=battle['id'], actor=146, target=defender)
        self.assertEqual(game.state.phase, 'result')
        self.cmd(game, 'settle', battle_id=battle['id'])
        self.assertEqual(game.state.cities['nanjun'].owner, 'shu')
        self.assertIsNone(game.state.officers[defender].faction_id)
        self.assertEqual(game.state.extension['free_locations'][str(defender)], 'nanjun')
        self.assertEqual(game._city_occupancy(game.state, game.state.cities['yingchuan']), 99)
        game.validate(game.state)

    def test_generated_person_can_preserve_faction_and_inherit_without_consuming_history_id(self):
        game = self.new(free=False)
        clerk = self.hire(game)
        for city in game.state.cities.values():
            if city.owner != 'shu': continue
            for ident in list(city.roster.officer_ids):
                if ident == clerk: continue
                officer = game.state.officers[ident]
                city.reserves += officer.troops
                officer.troops = 0
                officer.alive = False
                officer.faction_id = None
                officer.loyalty = 0
                city.roster.officer_ids.remove(ident)
        game._reconcile_factions(game.state)
        self.assertEqual(game.state.phase, 'city')
        self.assertNotIn('shu', game.state.extension['ended_factions'])
        self.assertEqual(game.state.extension['pending_succession']['shu']['candidates'], [clerk])
        self.cmd(game, 'choose_successor', officer=clerk)
        self.assertEqual(game.state.extension['leaders']['shu'], clerk)
        self.assertEqual(game.state.officers[clerk].loyalty, 100)
        self.assertEqual(self.pool(game)['people'][clerk]['city'], 'nanjun')
        self.assertEqual(self.pool(game)['people'][clerk]['owner'], 'shu')
        self.assertIn(clerk, game.state.officers)
        self.assertNotIn(clerk, game.catalog.by_id)
        game.validate(game.state)


if __name__ == '__main__': unittest.main()
