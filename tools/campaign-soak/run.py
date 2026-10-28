"""Bounded, reproducible multi-year campaigns using ordinary transactions.

Only response rendering is omitted. Catalogs, dates, resources, AI, RNG,
combat and save validation are the same services used by the playable game.
The player is a defensive administrator, not an optimal conquest oracle.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, canonical, digest
from remake.campaign_expansion import TACTICS
from remake.difficulty import get_settings
from remake.march_core import using_backend
from remake.officers import ref_sort_key
from remake.tactical_ai import choose_action
from remake import domestic, logistics, command_books

CASES = {
    'early': dict(scenario='184-02', faction='yellow_turban', turns=72),
    'middle': dict(scenario='217-07', faction='wei', turns=144),
    'late': dict(scenario='263-05', faction='wu', turns=72),
}


class HeadlessCampaign(Campaign):
    def view(self):
        # Campaign.command still copies/validates/commits state and captures
        # events. Only the unused UI catalog/route response is skipped.
        return {'revision': self.revision}


def snapshot(game):
    state = game.state
    cities = list(state.cities.values())
    fronts = logistics._fronts(game, state, state.player)
    convoys = state.extension['logistics']['convoys']
    return dict(turn=state.turn, date=[state.year, state.month, state.day], phase=state.phase,
        ownership={c.id: c.owner for c in sorted(cities, key=lambda c: c.id)},
        resources={k: sum(getattr(c, k) for c in cities) for k in ('gold', 'grain', 'reserves')},
        soldiers=dict(state.soldiers),
        roster_max=max((len(c.roster.officer_ids) for c in cities), default=0),
        living=sum(o.alive for o in state.officers.values()),
        player_officers=sum(o.alive and o.faction_id == state.player for o in state.officers.values()),
        short_fronts=[c.id for c in fronts if len(c.roster.officer_ids) < 2],
        marches=len(state.extension['travel']['marches']), convoys=len(convoys),
        waiting_convoys=sum(c['status'] == 'waiting' for c in convoys),
        oldest_convoy_turns=max((state.turn-c['journeys'][0]['departure_turn'] for c in convoys), default=0),
        convoy_wait_reasons=dict(Counter(c['reason'] for c in convoys if c['status'] == 'waiting')),
        in_transit={field: sum(c['cargo'][field] for c in convoys) for field in ('gold', 'grain', 'reserves')},
        overdue_marches=sum(c['arrival_turn'] < state.turn for c in state.extension['travel']['marches']),
        max_march_delay=max(0, max((state.turn-c['arrival_turn'] for c in state.extension['travel']['marches']), default=0)),
        battles=len(state.settled_battles), ended=sorted(state.extension['ended_factions']),
        leaders=dict(state.extension['leaders']), rng=dict(state=state.rng.state, draws=state.rng.draws))


def assert_invariants(game):
    game.validate(game.state)
    state = game.state
    current = (sum(c.reserves for c in state.cities.values())
               + sum(o.troops for o in state.officers.values())
               + logistics.in_transit_reserves(state))
    if current + state.soldiers['lost'] != state.soldiers['initial'] + state.soldiers['recruited']:
        raise AssertionError('Soldier conservation failed')
    if any(len(c.roster.officer_ids) > 99 or min(c.gold, c.grain, c.reserves) < 0
           for c in state.cities.values()):
        raise AssertionError('City capacity/resource boundary failed')
    if state.completed_ai_turns != list(range(1, state.turn)):
        raise AssertionError('AI turn committed more than once or skipped')


class Replay:
    def __init__(self, catalog, faction, seed, backend, *, progress=False):
        self.game = HeadlessCampaign(catalog)
        self.catalog_sha = digest(catalog.data)
        self.backend, self.progress = backend, progress
        self.commands, self.receipts = Counter(), Counter()
        self.recent_commands = []
        self.seen_receipts = set()
        self.transcript = hashlib.sha256()
        self.checkpoints, self.succession, self.samples = [], [], []
        self.command('new', faction=faction, seed=seed, difficulty='normal')
        self.initial = snapshot(self.game)

    def command(self, kind, **payload):
        self.game.command(kind, deepcopy(payload), self.game.revision)
        self.commands[kind] += 1
        # The production transaction already hashes the complete committed
        # state, including both main and civil-staff RNG. Hash every step,
        # not just the final state or sampled monthly summaries.
        state_sha = self.game.journal[-1]['after_sha256']
        self.transcript.update((canonical([kind, payload, state_sha])+'\n').encode())
        self.recent_commands.append(dict(kind=kind, payload=payload, state_sha256=state_sha))
        self.recent_commands[:] = self.recent_commands[-10:]
        if sum(self.commands.values()) > 100000:
            raise AssertionError('Replay exceeded the 100000 command budget')
        for row in self.game.state.extension['logistics']['reports']:
            key = (row['turn'], row['kind'], row['details']['convoy_id'])
            if key not in self.seen_receipts:
                self.seen_receipts.add(key)
                self.receipts[row['kind']] += 1

    def restore(self):
        saved = json.loads(json.dumps(self.game.export_save(), ensure_ascii=False))
        clone = HeadlessCampaign(self.game.catalog)
        clone.load_save(saved, 0)
        if clone.export_save() != saved:
            raise AssertionError('JSON save round trip changed state or RNG')
        self.game = clone
        self.checkpoints.append(dict(turn=clone.state.turn, checksum=saved['checksum']))

    def resolve(self):
        # A command budget detects a stuck phase rather than silently forcing
        # retreat, deleting a convoy, skipping combat or editing the clock.
        for _ in range(2000):
            game, state = self.game, self.game.state
            if state.phase == 'finished':
                return
            if state.phase == 'city':
                pending = state.extension['pending_succession'].get(state.player)
                if not pending:
                    return
                before = snapshot(game)
                successor = pending['candidates'][0]
                self.command('choose_successor', officer=successor)
                after = snapshot(self.game)
                if before['ownership'] != after['ownership'] or before['resources'] != after['resources']:
                    raise AssertionError('Succession unexpectedly changed cities or resources')
                self.succession.append(dict(turn=state.turn, previous=pending['previous'], successor=successor))
                self.restore()
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
                choice = choose_action(state, battle, own, foe,
                    game.catalog.map_cities[battle['target']]['terrain'], TACTICS,
                    settings=get_settings(state), damage_percent=game.catalog.data['rules']['battle_damage_percent'],
                    used=set(battle['used']))
                if choice is None:
                    raise AssertionError(f'No legal battle action: id={battle["id"]}, '
                        f'used={battle["used"]}, own={battle[own]}, foe={battle[foe]}')
                else:
                    payload = dict(battle_id=battle['id'], actor=choice['actor'], target=choice['target'])
                    if choice['kind'] == 'tactic':
                        payload['tactic'] = choice['tactic']
                    self.command(choice['kind'], **payload)
            else:
                raise AssertionError(f'Unhandled phase {state.phase}')
        raise AssertionError(f'Phase resolution exceeded 2000 ordinary commands; recent={self.recent_commands}')

    def administer(self):
        game, state = self.game, self.game.state
        home = next(c for c in state.cities.values() if c.owner == state.player)
        # Appointments are free policy controls. Establish the faction's
        # military office before spending books on individual assignments:
        # its ordinary end-turn service distributes the same local reserves
        # before hostile AI departures, without a second assignment fee.
        ids = sorted((i for i in state.officers if domestic._present(game,state,home,i)),key=ref_sort_key)
        if len(ids) >= 2:
            civil = min(ids, key=lambda i: (-state.officers[i].profile.intellect, ref_sort_key(i)))
            military = min((i for i in ids if i != civil),
                key=lambda i: (-state.officers[i].profile.martial_strength, ref_sort_key(i)))
            post = domestic.appointments(state, state.player)
            if post['civil'] != civil or post['military'] != military or not post['policy']['recruit_enabled']:
                self.command('set_domestic', faction=state.player, civil=civil, military=military,
                    policy=dict(auto_recruit=True, auto_persuade=True, min_chance=20,
                        recruit_enabled=True, training_enabled=True, reserve_target=2000, recruit_budget=100,
                        task_order=['transport', 'personnel', 'recruit']))
        game, state = self.game, self.game.state
        post = domestic.appointments(state, state.player)
        if not domestic._present(game, state, home, post.get('military')):
            # A wounded, absent or unavailable official cannot distribute
            # reserves. Spend the shared pool on urgent/frontline defenders
            # first, using public paid commands and the actual local stock.
            busy = game._march_ids(state)
            fronts = {c.id for c in logistics._fronts(game, state, state.player)}
            incoming = {}
            for march in state.extension['travel']['marches']:
                if march['owner'] != state.player and march['kind'] == 'attack':
                    target = march['target']
                    incoming[target] = min(incoming.get(target, march['arrival_turn']), march['arrival_turn'])
            cities = sorted((c for c in state.cities.values() if c.owner == state.player),
                key=lambda c: (incoming.get(c.id, 10**9), c.id not in fronts, c.id))
            for city in cities:
                officers = sorted(city.roster.officer_ids,key=lambda i:
                    (-state.officers[i].profile.martial_strength,ref_sort_key(i)))
                for ident in officers:
                    person = self.game.state.officers[ident]
                    current = self.game.state.cities[city.id]
                    if ident in busy or not person.alive or person.health < 1:
                        continue
                    target = min(999,person.troops+current.reserves)
                    if target > person.troops and command_books.can_spend(game.state, state.player, 'allocate'):
                        self.command('allocate',city=city.id,officer=ident,troops=target)
        if len(ids) < 2:
            return
        # Configure one genuine friendly source-to-front route through public
        # policy controls as the player. Never inject cargo or shorten routes.
        game, state = self.game, self.game.state
        if not any(r['policy']['enabled'] for r in state.extension['logistics']['cities'].values()
                   if r['owner'] == state.player):
            fronts = logistics._fronts(game, state, state.player)
            front_ids = {f.id for f in fronts}
            rear = sorted((c for c in state.cities.values() if c.owner == state.player
                           and len(c.roster.officer_ids) > 2),
                          key=lambda c: (c.id in front_ids, -c.grain, c.id))
            for source in rear[:3]:
                choices = [(game._travel_path(state, source.id, target.id, state.player, 'land'), target)
                           for target in fronts if target.id != source.id and len(target.roster.officer_ids) < 98]
                choices = [(q, c) for q, c in choices if q and not any(r.get('hazard') for r in q['routes'])]
                if choices:
                    _, target = min(choices, key=lambda p: (p[0]['days'], p[1].id))
                    self.command('set_logistics', city=source.id, policy=dict(enabled=True,
                        target_city=target.id, target_gold=target.gold+200,
                        target_grain=target.grain+600, target_reserves=target.reserves+300,
                        target_officers=min(99, len(target.roster.officer_ids)+1)))
                    break

    def run(self, turns):
        for index in range(turns):
            self.resolve()
            if self.game.state.phase == 'finished':
                break
            self.administer()
            prior = self.game.state.turn
            self.command('end_turn')
            self.resolve()
            assert_invariants(self.game)
            if self.game.state.turn not in (prior, prior+1):
                raise AssertionError('A turn advanced by more than one ten-day period')
            state = self.game.state
            if state.day == 1 or state.phase == 'finished':
                self.restore()
                self.samples.append(snapshot(self.game))
            if self.progress and (index+1) % 12 == 0:
                print(f'{self.game.catalog.data["id"]} {self.backend}: {index+1}/{turns} turns', file=sys.stderr, flush=True)
        self.resolve()
        assert_invariants(self.game)
        self.restore()
        final = snapshot(self.game)
        if digest(self.game.catalog.data) != self.catalog_sha:
            raise AssertionError('Replay mutated the original catalog')
        return dict(backend=self.backend, initial=self.initial, final=final,
            completed_turns=final['turn']-self.initial['turn'], requested_turns=turns,
            coverage=dict(crossed_year=final['date'][0] > self.initial['date'][0],
                          player_successions=len(self.succession),
                          founded_cities=sorted(set(final['ownership'])-set(self.initial['ownership']))),
            commands=dict(self.commands), transport_receipts=dict(self.receipts), succession=self.succession,
            checkpoints=self.checkpoints, samples=self.samples, command_sha256=self.transcript.hexdigest(),
            final_save_sha256=digest(self.game.export_save()))


def observations(result):
    """Indicators are observations, not invented win-rate/balance guarantees."""
    items, rows = [], [result['initial'], *result['samples'], result['final']]
    if result['completed_turns'] < result['requested_turns']:
        items.append(dict(kind='early_finish', turn=result['final']['turn']))
    if len(rows) >= 13 and len({digest(r['ownership']) for r in rows[-13:]}) == 1:
        items.append(dict(kind='unchanged_ownership_12_samples', turn=rows[-1]['turn']))
    for field in ('gold', 'grain', 'reserves'):
        start, end = rows[0]['resources'][field], rows[-1]['resources'][field]
        if end > max(start*10, 1000000):
            items.append(dict(kind='resource_growth', field=field, initial=start, final=end))
    if result['final']['short_fronts']:
        items.append(dict(kind='short_fronts', cities=result['final']['short_fronts']))
    if result['final']['waiting_convoys'] or result['final']['oldest_convoy_turns'] > 36:
        items.append(dict(kind='convoy_backlog', waiting=result['final']['waiting_convoys'],
                          oldest_turns=result['final']['oldest_convoy_turns']))
    return items


def run_case(case, seed, backends=('python', 'rust'), *, turns=None, progress=False):
    spec = CASES[case]
    catalog = Catalog(ROOT / 'game/data/campaigns' / (spec['scenario']+'.json'))
    results = []
    for backend in backends:
        with using_backend(backend):
            replay = Replay(catalog, spec['faction'], seed, backend, progress=progress)
            try:
                results.append(replay.run(turns or spec['turns']))
            except Exception as error:
                error.soak_context = dict(backend=backend, phase=replay.game.state.phase,
                    recent_commands=replay.recent_commands, save=replay.game.export_save())
                raise
    reference = {k: v for k, v in results[0].items() if k != 'backend'}
    for result in results[1:]:
        if {k: v for k, v in result.items() if k != 'backend'} != reference:
            error = AssertionError(f'Backend state/save/RNG/transcript divergence: {case} seed {seed}')
            error.soak_context = dict(results=results, last_save=replay.game.export_save())
            raise error
    # An ordinary early victory/defeat is valid gameplay, but cannot count as
    # having exercised the requested multi-year release gate.
    if turns is None and (reference['completed_turns'] != spec['turns']
            or not reference['coverage']['crossed_year'] or not reference['succession']):
        error = AssertionError(f'Insufficient long-run coverage: {case} seed {seed}')
        error.soak_context = dict(result=reference, observations=observations(results[0]))
        raise error
    return dict(case=case, scenario=spec['scenario'], faction=spec['faction'], seed=seed,
        catalog_sha256=catalog.sha256, backends=list(backends), parity=len(set(backends)) > 1,
        result=reference, observations=observations(results[0]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, nargs='+', default=list(CASES))
    parser.add_argument('--seeds', type=int, nargs='+', default=[3, 2026])
    parser.add_argument('--backends', choices=['python', 'rust'], nargs='+', default=['python', 'rust'])
    parser.add_argument('--turns', type=int, help='Override per-case duration for a bounded smoke test')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--progress', action='store_true')
    args = parser.parse_args(argv)
    if args.turns is not None and not 1 <= args.turns <= 360:
        parser.error('--turns must be between 1 and 360')
    if any(not 1 <= seed <= 0xffffffff for seed in args.seeds):
        parser.error('seeds must be between 1 and 2^32-1')
    report = dict(schema='tk2-campaign-soak-v1', policy='defensive-administrator-v3-shared-order-defense', cases=[], failures=[])
    started = time.monotonic()
    for case in args.case:
        for seed in args.seeds:
            try:
                report['cases'].append(run_case(case, seed, tuple(args.backends), turns=args.turns, progress=args.progress))
            except Exception as error:
                failure = dict(case=case, seed=seed, error=f'{type(error).__name__}: {error}')
                if hasattr(error, 'soak_context'):
                    failure['context'] = error.soak_context
                report['failures'].append(failure)
    report['elapsed_seconds'] = round(time.monotonic()-started, 3)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(cases=len(report['cases']), failures=[{k: v for k, v in f.items() if k != 'context'} for f in report['failures']],
                         elapsed_seconds=report['elapsed_seconds'], output=str(args.output)), ensure_ascii=False))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
