"""Natural dated campaigns exercise delegation through public transactions.

No fixture rewrites ownership, dates, profiles, RNG or starting resources. Every
phase is saved as JSON, restored and continued; the small 184 faction is also
replayed command-for-command through both marching engines.

Automatic facility visits and weighted duel combat are disabled in the copied
catalog to preserve the
office-only persuasion/reappointment regression. Actual facility AI, its action
competition and seasonal disasters are covered by the facility campaign tests
and the unmodified cross-year campaign soak.
"""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, digest
from remake import command_books, domestic, logistics
from remake.march_core import using_backend
from remake.officers import ref_sort_key


class DelegationReplayTests(unittest.TestCase):
    def checkpoint(self):
        saves = []
        restored = []
        for backend, game in zip(self.backends, self.games):
            with using_backend(backend):
                game.validate(game.state)
                state = game.state
                current = (sum(c.reserves for c in state.cities.values())
                    + sum(p.troops for p in state.officers.values())
                    + logistics.in_transit_reserves(state))
                self.assertEqual(current + state.soldiers['lost'],
                    state.soldiers['initial'] + state.soldiers['recruited'])
                self.assertTrue(all(0 <= len(c.roster.officer_ids) <= 99
                                    for c in state.cities.values()))
                self.assertTrue(all(min(c.gold, c.grain, c.reserves) >= 0
                                    for c in state.cities.values()))
                saved = game.export_save()
                # Exercise the actual browser/cloud JSON representation, not
                # merely an in-memory dataclass copy.
                wire = json.loads(json.dumps(saved, ensure_ascii=False))
                clone = Campaign(game.catalog)
                clone.load_save(wire, 0)
                self.assertEqual(clone.export_save(), saved)
                saves.append(saved)
                restored.append(clone)
        for save in saves[1:]:
            self.assertEqual(save, saves[0], 'Python and Rust diverged at a real phase boundary')
        self.games = restored
        state = self.games[0].state
        self.phases[state.phase] += 1
        self.player_reports.update((r['turn'], r['city'], r['kind'])
            for r in state.extension['domestic']['reports'] if r['owner'] == state.player)
        self.ai_reports.update((r['turn'], r['city'], r['kind'])
            for r in state.extension['domestic']['reports']
            if r['owner'] not in {state.player, 'neutral'})
        self.convoy_reports.update((r['turn'], r['source'], r['target'], r['kind'])
            for r in state.extension['logistics']['reports'])
        self.ai_work.update((key, row['last_work_turn'])
            for key, row in state.extension['domestic']['cities'].items()
            if row['owner'] not in {state.player, 'neutral'} and row['last_work_turn'])
        return state

    def command(self, kind, **payload):
        for backend, game in zip(self.backends, self.games):
            with using_backend(backend):
                game.command(kind, deepcopy(payload), game.revision)
        self.commands[kind] += 1
        return self.checkpoint()

    def configure(self):
        game, state = self.games[0], self.games[0].state
        cities = sorted((c for c in state.cities.values()
                         if c.owner == state.player and c.roster.officer_ids),
                        key=lambda c: (-len(c.roster.officer_ids), c.id))[:2]
        ids = [i for c in state.cities.values() if c.owner == state.player
               for i in c.roster.officer_ids]
        self.assertGreaterEqual(len(ids), 2, 'Real faction must offer two distinct appointees')
        civil = min(ids, key=lambda i: (-state.officers[i].profile.intellect, ref_sort_key(i)))
        military = min((i for i in ids if i != civil),
            key=lambda i: (-state.officers[i].profile.martial_strength, ref_sort_key(i)))
        self.command('set_domestic', faction=state.player, civil=civil, military=military,
            policy=dict(auto_recruit=True, auto_persuade=True, min_chance=0,
                recruit_enabled=True, training_enabled=True,
                reserve_target=max(c.reserves for c in cities) + 1000, recruit_budget=100,
                task_order=['recruit', 'personnel', 'transport']))
        # Appointment is faction-wide; these two sources only bound the real
        # geographic transport search, not the number of governed cities.
        self.appointed = [city.id for city in cities]
        # A single-city faction has no legal friendly destination. Larger
        # factions choose a real reachable front and use ordinary policy knobs;
        # no cargo or soldiers are injected into the campaign.
        game, state = self.games[0], self.games[0].state
        choices = []
        for source in self.appointed:
            for target in logistics._fronts(game, state, state.player):
                if target.id == source:
                    continue
                quote = game._travel_path(state, source, target.id, state.player, 'land')
                if quote and all(not leg.get('hazard') for leg in quote['routes']):
                    choices.append((quote['days'], source, target.id))
        self.transport_source = None
        if choices:
            _, source, target = min(choices)
            city = state.cities[target]
            self.command('set_logistics', city=source, policy=dict(enabled=True,
                target_city=target, target_gold=city.gold + 100,
                target_grain=city.grain + 300, target_reserves=city.reserves + 200,
                target_officers=len(city.roster.officer_ids) + 1,
                reserve_officers=2, max_gold=100, max_grain=300,
                max_reserves=200, max_officers=1))
            self.command('set_domestic', faction=state.player,
                         policy=dict(task_order=['transport', 'recruit', 'personnel']))
            self.transport_source = source

    def generated_maneuver(self):
        """A hired rear-area clerk uses the same transfer and attack commands."""
        if self.generated is None or self.staff_attack_sent:
            return
        game, state = self.games[0], self.games[0].state
        ident = self.generated
        if ident in game._march_ids(state) or not state.officers[ident].alive:
            return
        home = next((c for c in state.cities.values() if ident in c.roster.officer_ids), None)
        if home is None or home.owner != state.player or not command_books.can_spend(state,state.player):
            return
        choices = []
        for target in game._neighbors(home.id, state):
            city = state.cities[target]
            if city.owner in {state.player, 'neutral'} or not city.roster.officer_ids:
                continue
            quote = game._travel_path(state, home.id, target, state.player, 'land', adjacent=True)
            if quote and all(not leg.get('hazard') for leg in quote['routes']):
                choices.append((quote['days'], target))
        if choices:
            _, target = min(choices)
            self.command('depart', source=home.id, target=target,
                         officers=[ident], route_mode='land')
            self.staff_attack_sent = True
            return
        # A real intervening city is now a stop, so Xiangyang need not itself
        # border the enemy. Move the clerk to the nearest actual land front
        # through public commands rather than assuming a visual bypass.
        fronts = []
        for city in state.cities.values():
            if city.owner != state.player or city.id == home.id:
                continue
            if not any(state.cities[key].owner not in {state.player, 'neutral'}
                       and state.cities[key].roster.officer_ids
                       and game._travel_path(state, city.id, key, state.player, 'land', adjacent=True)
                       for key in game._neighbors(city.id, state) if key in state.cities):
                continue
            quote = game._travel_path(state, home.id, city.id, state.player, 'land')
            if quote and all(not leg.get('hazard') for leg in quote['routes']):
                fronts.append((quote['days'], city.id))
        if fronts:
            self.command('transfer', source=home.id, target=min(fronts)[1],
                         officers=[ident], route_mode='land')

    def reinforce_184_guards(self):
        """Use available reserves before defending the exposed one-city start."""
        game, state = self.games[0], self.games[0].state
        post = domestic.appointments(state, state.player)
        if post['military'] is None:
            # Rival automatic persuasion can legitimately recruit the military
            # official. A human commander must refill that vacancy rather than
            # leave all newly recruited city reserves unassigned indefinitely.
            # Use the real appointment eligibility and public command; do not
            # restore the defecting officer, edit loyalty, or suppress AI work.
            eligible = domestic.view(game, state)['factions'][state.player]['eligible_officers']
            choices = [i for i in eligible if i != post['civil']]
            if choices:
                ident = min(choices, key=lambda i: (-state.officers[i].profile.martial_strength,
                                                  ref_sort_key(i)))
                self.command('set_domestic', faction=state.player, military=ident)
                self.reappointed_military.append((state.turn, ident))
                game, state = self.games[0], self.games[0].state
        for city in sorted(state.cities.values(), key=lambda c: c.id):
            if city.owner != state.player:
                continue
            ids = sorted((i for i in city.roster.officer_ids
                if i not in game._march_ids(state) and state.officers[i].health > 0),
                key=lambda i: (-state.officers[i].profile.martial_strength, ref_sort_key(i)))[:2]
            for ident in ids:
                current = self.games[0].state
                person, home = current.officers[ident], current.cities[city.id]
                target = min(999, person.troops + home.reserves)
                if target > person.troops and command_books.can_spend(current,current.player,'allocate'):
                    self.command('allocate', city=city.id, officer=ident, troops=target)

    def resolve_phases(self):
        # A real battle now includes travel over the original grid and up to30
        # tactical days. Keep a finite bound without assuming remote attacks.
        for _ in range(2000):
            game, state = self.games[0], self.games[0].state
            pending = state.extension['pending_succession'].get(state.player)
            if pending:
                self.command('choose_successor', officer=pending['candidates'][0])
            elif state.phase == 'city' or state.phase == 'finished':
                return
            elif state.phase == 'ai':
                self.command('ai', turn=state.turn)
            elif state.phase == 'arrivals':
                self.command('arrivals')
            elif state.phase == 'result':
                self.command('settle', battle_id=state.battle['id'])
            elif state.phase == 'battle':
                battle = state.battle
                if battle['extended']['duel']:
                    self.command('duel_action', battle_id=battle['id'], move='withdraw')
                    continue
                own, foe = game._player_sides(state)
                actors = [u for u in battle[own] if u['troops'] > 0
                          and isinstance(u['id'], str) and u['id'].startswith('clerk-')]
                targets = [u for u in battle[foe] if u['troops'] > 0]
                if actors and targets and battle['id'] not in self.staff_battles:
                    from remake.campaign_expansion import TACTICS
                    from remake.tactical_ai import candidates
                    choices = candidates(state, battle, own, foe,
                        game.catalog.map_cities[battle['target']]['terrain'], TACTICS,
                        damage_percent=game.catalog.data['rules']['battle_damage_percent'], depth=0)
                    staff_choices = [row for row in choices if row['actor'] == actors[0]['id']]
                    choice = next((row for row in staff_choices if row['kind'] == 'attack'),
                        next((row for row in staff_choices if row['kind'] == 'move'),
                             dict(kind='wait')))
                    self.tactical_command(battle, choice)
                    if choice['kind'] in {'move', 'attack'}:
                        # Movement now spends real shared AP and participates
                        # in the same battle/save ledger. A weak civil clerk
                        # can legitimately be routed before reaching melee.
                        self.staff_battles.add(battle['id'])
                elif own == 'defenders' and targets:
                    # Defend the historical single-city 184 start instead of
                    # surrendering its only city just to advance the clock.
                    # The actual tactical planner supplies legal ordinary or
                    # stratagem commands, including their normal RNG/counters.
                    from remake.campaign_expansion import TACTICS
                    from remake.difficulty import get_settings
                    from remake.tactical_ai import choose_action
                    choice = choose_action(state, battle, own, foe,
                        game.catalog.map_cities[battle['target']]['terrain'], TACTICS,
                        settings=get_settings(state),
                        damage_percent=game.catalog.data['rules']['battle_damage_percent'])
                    self.assertIsNotNone(choice)
                    self.tactical_command(battle, choice)
                else:
                    self.command('retreat', battle_id=battle['id'])
            else:
                self.fail(f'Unhandled natural phase: {state.phase}')
        self.fail('Natural phase flow exceeded the bounded command budget')

    def tactical_command(self, battle, choice):
        kind = choice['kind']
        payload = dict(battle_id=battle['id'])
        if kind == 'wait':
            return self.command('battle_wait', **payload)
        payload['actor'] = choice['actor']
        if kind == 'move':
            return self.command('battle_move', **payload, x=choice['x'], y=choice['y'])
        payload['target'] = choice['target']
        if kind == 'tactic':
            payload['tactic'] = choice['tactic']
        return self.command(kind, **payload)

    def replay(self, filename, faction, turns, *, backends=('rust',), staff=False, seed=2026):
        self.backends, self.games = backends, []
        self.phases, self.commands = Counter(), Counter()
        self.player_reports, self.ai_reports, self.ai_work, self.convoy_reports = set(), set(), set(), set()
        self.generated, self.staff_attack_sent, self.staff_battles = None, False, set()
        self.reappointed_military = []
        data = json.loads((ROOT / 'game/data/campaigns' / filename).read_text())
        data['facility_ai_default'] = False
        data['equipment_rules']['combat_enabled'] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / filename
            path.write_text(json.dumps(data, ensure_ascii=False))
            catalog = Catalog(path)
        original_catalog = digest(catalog.data)
        for backend in backends:
            game = Campaign(catalog)
            with using_backend(backend):
                game.command('new', dict(faction=faction, seed=seed), 0)
            self.games.append(game)
        self.checkpoint()
        self.configure()
        if filename == '184-02.json':
            # An exposed lone-city faction cannot survive by passing every
            # turn. Occupy the actual empty neighbouring city using two real
            # unattached officers, retaining both appointed posts at home.
            self.reinforce_184_guards()
            self.command('depart', source='yan', target='fanyang',
                         officers=[146, 951], route_mode='land')
        if staff:
            candidate = self.games[0].state.extension['civil_staff']['cities']['nanyang']['candidate']
            self.assertIsNotNone(candidate)
            self.generated = candidate['id']
            self.command('hire_staff', city='nanyang', candidate=self.generated)
            self.command('allocate', city='nanyang', officer=self.generated, troops=999)
        initial_turn = self.games[0].state.turn
        for _ in range(turns):
            self.resolve_phases()
            self.assertEqual(self.games[0].state.phase, 'city', 'Faction ended before the replay budget')
            if filename == '184-02.json':
                self.reinforce_184_guards()
            if self.games[0].state.turn > initial_turn:
                self.generated_maneuver()
            prior = self.games[0].state.turn
            self.command('end_turn')
            self.resolve_phases()
            self.assertEqual(self.games[0].state.turn, prior + 1)
        final = self.games[0].state
        self.assertEqual(final.turn, initial_turn + turns)
        self.assertEqual(final.completed_ai_turns, list(range(initial_turn, final.turn)))
        self.assertGreater(self.phases['ai'], 0)
        self.assertTrue(self.ai_work, 'Real AI factions must execute the shared office service')
        self.assertTrue(self.ai_reports, 'Real AI must produce an actual paid or personnel action')
        self.assertTrue(any(kind == 'recruit' for _, _, kind in self.player_reports))
        self.assertGreater(final.soldiers['recruited'], 0)
        if self.transport_source:
            self.assertTrue(any(source == self.transport_source and kind == 'transport_departed'
                for _, source, _, kind in self.convoy_reports))
            self.assertTrue(any(source == self.transport_source
                and kind in {'transport_arrived', 'transport_returned'}
                for _, source, _, kind in self.convoy_reports))
        if staff:
            self.assertTrue(self.staff_attack_sent)
            self.assertTrue(self.staff_battles, 'A generated officer must enter and act in a real arrival battle')
            self.assertGreater(final.officers[self.generated].experience, 0)
            self.assertNotIn(self.generated, catalog.by_id)
            self.assertEqual(len(catalog.definitions), 1052)
        if filename == '184-02.json':
            self.assertTrue(self.reappointed_military,
                'Real persuasion must be followed by a legal replacement military appointment')
            self.assertTrue(any(kind == 'allocation' and turn >= self.reappointed_military[0][0]
                                for turn, _, kind in self.player_reports),
                            'The replacement official must resume actual local reserve allocation')
        self.assertEqual(digest(catalog.data), original_catalog, 'Replay mutated the real catalog')

    def test_184_liu_yan_six_turns_are_identical_in_python_and_rust(self):
        # The revised184 postings and local Han Sui change real AI choices.
        # Seed2032 naturally exercises rival persuasion, a legal replacement
        # appointment and resumed allocation without rewriting state or RNG.
        self.replay('184-02.json', 'liu_yan', 6, backends=('python', 'rust'), seed=2032)

    def test_217_wei_six_turns_staff_arrival_combat_and_real_convoys(self):
        self.replay('217-07.json', 'wei', 6, staff=True)

    def test_263_shu_six_turns_offices_ai_and_frontline_transport(self):
        self.replay('263-05.json', 'shu', 6)


if __name__ == '__main__':
    unittest.main()
