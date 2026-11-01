"""Bounded observations of ordinary campaigns under explicit player policies.

This is a balance benchmark, separate from release correctness/parity gates.
No resources, loyalties, routes, AI settings or RNG state are edited to force
an outcome. A terminal result is required before a run counts as won or lost.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source'))
from remake import command_books, logistics
from remake.campaign import Catalog, digest
from remake.march_core import using_backend
from remake.strategic_ai import StrategicAI

_spec = importlib.util.spec_from_file_location('_balance_soak', ROOT/'tools/campaign-soak/run.py')
soak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(soak)

SCHEMA = 'tk2-campaign-balance-v1'
POLICY_VERSION = 'public-orders-v1'
ERAS = {
    'early': dict(scenario='184-02', factions=['han', 'yellow_turban']),
    'middle': dict(scenario='217-07', factions=['wei', 'shu']),
    'late': dict(scenario='263-05', factions=['wei', 'wu']),
}
POLICIES = ('defensive', 'offensive', 'transport')


class LimitReached(Exception):
    pass


def distribution(values):
    values = sorted(values)
    return dict(total=sum(values), minimum=values[0] if values else None,
                median=statistics.median(values) if values else None,
                maximum=values[-1] if values else None)


def metrics(game):
    """Observe present front-line staff and city stocks without performing work."""
    state = game.state
    unavailable = game._march_ids(state)
    if state.battle:
        unavailable = unavailable | {row['id'] for side in ('attackers', 'defenders') for row in state.battle[side]}
    factions = {}
    for owner in sorted(game.catalog.factions):
        cities = sorted((c for c in state.cities.values() if c.owner == owner), key=lambda c: c.id)
        fronts = logistics._fronts(game, state, owner)
        short = [c.id for c in fronts if sum(
            i not in unavailable and state.officers[i].alive and state.officers[i].health > 0
            for i in c.roster.officer_ids) < 2]
        factions[owner] = dict(cities=len(cities), fronts=len(fronts), short_fronts=short,
            officers=sum(o.alive and o.faction_id == owner for o in state.officers.values()),
            stocks={field: distribution([getattr(c, field) for c in cities])
                    for field in ('gold', 'grain', 'reserves')})
    return dict(turn=state.turn, date=[state.year, state.month, state.day], phase=state.phase,
                factions=factions, rng=dict(state=state.rng.state, draws=state.rng.draws))


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(path)


class BalanceReplay(soak.Replay):
    """Reuse the real transaction/combat resolver; vary only public orders."""
    def __init__(self, catalog, spec, *, checkpoint=None):
        self.spec = deepcopy(spec)
        self.started = time.monotonic()
        self.deadline = self.started+spec['max_seconds']
        self.checkpoint = checkpoint
        self.first_invasion = {}
        self.seen_marches = set()
        self.timeline = []
        self.previous_ownership = {}
        super().__init__(catalog, spec['faction'], spec['seed'], spec['backend'])
        self.initial_ownership = dict(self.initial['ownership'])
        self.sample()

    def command(self, kind, **payload):
        if time.monotonic() >= self.deadline:
            raise LimitReached('wall_time')
        if sum(getattr(self, 'commands', {}).values()) >= self.spec['max_commands']:
            raise LimitReached('commands')
        if kind == 'new':
            payload['difficulty'] = self.spec['difficulty']
        elif kind == 'set_domestic':
            payload = deepcopy(payload)
            payload['policy']['task_order'] = (['transport', 'recruit', 'personnel']
                if self.spec['policy'] == 'transport' else ['recruit', 'personnel', 'transport'])
        super().command(kind, **payload)
        for march in self.game.state.extension['travel']['marches']:
            if march['id'] in self.seen_marches:
                continue
            self.seen_marches.add(march['id'])
            target = self.game.state.cities[march['target']]
            if march['kind'] == 'attack' and target.owner not in (march['owner'], 'neutral'):
                self.first_invasion.setdefault(march['owner'], march['departure_turn'])

    def sample(self):
        row = metrics(self.game)
        ownership = {key: c.owner for key, c in sorted(self.game.state.cities.items())}
        # A final partial phase replaces its own turn's sample, rather than
        # inflating the number of stagnant turns with duplicate observations.
        if self.timeline and self.timeline[-1]['turn'] == row['turn']:
            self.timeline.pop()
            previous = dict(self.initial_ownership)
            for prior in self.timeline:
                for change in prior['ownership_changes']:
                    previous[change['city']] = change['to']
        else:
            previous = self.previous_ownership
        row['ownership_changes'] = [dict(city=key, **{'from': previous.get(key), 'to': owner})
            for key, owner in ownership.items() if previous and previous.get(key) != owner]
        row['ownership_sha256'] = digest(ownership)
        self.timeline.append(row)
        self.previous_ownership = ownership

    def administer(self):
        super().administer()
        if self.spec['policy'] == 'offensive':
            self.attack()
        elif self.spec['policy'] == 'transport':
            self.configure_transport()

    def attack(self):
        # The existing planner supplies legal, provisioned armies and routes.
        # This simple player policy never rewrites the AI's persistent plan.
        for _ in range(2):
            game, state = self.game, self.game.state
            if not command_books.can_spend(state, state.player, 'depart'):
                return
            planner, options = StrategicAI(game, state), []
            for city in sorted(state.cities.values(), key=lambda c: c.id):
                if city.owner != state.player:
                    continue
                for target in planner.neighbors(city):
                    if target.owner == state.player:
                        continue
                    option = planner.attack_option(city, target)
                    if not option:
                        continue
                    strength = planner.strength(target)
                    if option['survivors']*100 < strength*planner.settings['attack_ratio_percent']:
                        continue
                    options.append((target.owner != 'neutral', strength, option['quote']['days'],
                                    city.id, target.id, option))
            if not options:
                return
            option = min(options, key=lambda row: row[:5])[-1]
            self.command('depart', source=option['source'], target=option['target'],
                         officers=option['officers'], route_mode=option['mode'])

    def configure_transport(self):
        game, state = self.game, self.game.state
        fronts = logistics._fronts(game, state, state.player)
        front_ids = {c.id for c in fronts}
        rear = sorted((c for c in state.cities.values() if c.owner == state.player
                       and c.id not in front_ids and len(c.roster.officer_ids) > 2),
                      key=lambda c: (-c.grain, c.id))
        configured = sum(r['owner'] == state.player and r['policy']['enabled']
                         for r in state.extension['logistics']['cities'].values())
        for source in rear[:3]:
            if configured >= 3:
                break
            if state.extension['logistics']['cities'][source.id]['policy']['enabled']:
                continue
            options = []
            for target in fronts:
                if len(target.roster.officer_ids) >= 98:
                    continue
                quote = game._travel_path(state, source.id, target.id, state.player, 'land')
                if quote and not any(r.get('hazard') for r in quote['routes']):
                    options.append((len(target.roster.officer_ids), target.grain,
                                    quote['days'], target.id, target))
            if options:
                target = min(options, key=lambda row: row[:4])[-1]
                self.command('set_logistics', city=source.id, policy=dict(enabled=True,
                    target_city=target.id, target_gold=target.gold+200,
                    target_grain=target.grain+600, target_reserves=target.reserves+300,
                    target_officers=min(99, len(target.roster.officer_ids)+1)))
                configured += 1

    def report(self, reason):
        self.sample()
        state = self.game.state
        native = state.extension['outcome'] if state.phase == 'finished' else None
        outcome = {'victory': 'win', 'defeat': 'loss'}.get(native, 'unresolved')
        stagnant = longest = 0
        for before, after in zip(self.timeline, self.timeline[1:]):
            stagnant = stagnant+after['turn']-before['turn'] if before['ownership_sha256'] == after['ownership_sha256'] else 0
            longest = max(longest, stagnant)
        player = state.player
        save = self.game.export_save()
        return dict(spec=self.spec, policy_version=POLICY_VERSION, initialized=True,
            scenario_id=self.game.catalog.data['id'], catalog_sha256=self.game.catalog.sha256,
            outcome=outcome, stop_reason='terminal' if outcome != 'unresolved' else reason,
            completed_turns=state.turn-self.initial['turn'], revision=self.game.revision,
            first_invasion_turns=dict(sorted(self.first_invasion.items())),
            first_player_invasion_turn=self.first_invasion.get(player),
            longest_unchanged_ownership_turns=longest,
            front_shortage_samples=sum(bool(r['factions'][player]['short_fronts']) for r in self.timeline),
            initial_ownership=self.initial_ownership,
            final_ownership={k: c.owner for k, c in sorted(state.cities.items())},
            timeline=self.timeline, commands=dict(self.commands),
            transport_receipts=dict(self.receipts), command_sha256=self.transcript.hexdigest(),
            final_save_sha256=digest(save), final_rng=dict(state=state.rng.state, draws=state.rng.draws),
            elapsed_seconds=round(time.monotonic()-self.started, 3))

    def run_bounded(self):
        reason = 'turn_limit'
        if self.checkpoint:
            _write(self.checkpoint, self.report('initializing'))
        try:
            for _ in range(self.spec['turns']):
                self.resolve()
                if self.game.state.phase == 'finished':
                    break
                self.administer()
                self.command('end_turn')
                self.resolve()
                soak.assert_invariants(self.game)
                if self.game.state.day == 1:
                    self.restore()
                self.sample()
                if self.checkpoint:
                    _write(self.checkpoint, self.report('in_progress'))
        except LimitReached as error:
            reason = str(error)
        self.game.validate(self.game.state)
        if digest(self.game.catalog.data) != self.catalog_sha:
            raise AssertionError('Balance policy mutated its catalog')
        return self.report(reason)


def summarize(runs):
    groups = []
    for policy in POLICIES:
        rows = [r for r in runs if r['spec']['policy'] == policy]
        counts = Counter(r['outcome'] for r in rows)
        resolved = counts['win']+counts['loss']
        groups.append(dict(policy=policy, runs=len(rows), wins=counts['win'], losses=counts['loss'],
            unresolved=counts['unresolved'], resolved_only_win_rate=counts['win']/resolved if resolved else None,
            terminal_fraction=resolved/len(rows) if rows else None,
            budget_stops=sum(r['stop_reason'] in ('wall_time', 'hard_wall_time', 'commands') for r in rows)))
    return groups


def plan(eras, factions, seeds, policies, **settings):
    result = []
    for era in eras:
        row = ERAS[era]
        selected = factions or row['factions']
        for faction in selected:
            for seed in seeds:
                for policy in policies:
                    result.append(dict(era=era, scenario=row['scenario'], faction=faction,
                                       seed=seed, policy=policy, **settings))
    return result


def execute(spec):
    """A subprocess also bounds one unusually slow public transaction."""
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='tk2-balance-') as folder:
        checkpoint, output = Path(folder)/'checkpoint.json', Path(folder)/'result.json'
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker',
                   json.dumps(spec), '--checkpoint', str(checkpoint), '--output', str(output)]
        try:
            completed = subprocess.run(command, capture_output=True, text=True,
                                       timeout=spec['max_seconds']+2)
        except subprocess.TimeoutExpired:
            if checkpoint.exists():
                result = json.loads(checkpoint.read_text())
                result.update(outcome='unresolved', stop_reason='hard_wall_time',
                              elapsed_seconds=round(time.monotonic()-started, 3))
                return result
            return dict(spec=spec, policy_version=POLICY_VERSION, initialized=False,
                        scenario_id=None, catalog_sha256=None, revision=None,
                        outcome='unresolved', stop_reason='hard_wall_time',
                        completed_turns=0, timeline=[], commands={},
                        first_player_invasion_turn=None, first_invasion_turns={},
                        final_save_sha256=None, final_rng=None,
                        elapsed_seconds=round(time.monotonic()-started, 3))
        if completed.returncode or not output.exists():
            raise RuntimeError('Benchmark child failed: '+completed.stderr[-2000:])
        return json.loads(output.read_text())


def comparison_key(row):
    return tuple(row['spec'][k] for k in ('scenario', 'faction', 'seed', 'policy', 'difficulty', 'backend', 'turns'))


def comparison_index(runs):
    indexed = {}
    for row in runs:
        key = comparison_key(row)
        if key in indexed:
            raise ValueError('Duplicate comparison key: '+json.dumps(key, ensure_ascii=False))
        indexed[key] = row
    return indexed


def comparison(current, previous):
    old = comparison_index(previous['runs'])
    comparison_index(current)
    rows = []
    for row in current:
        prior = old.get(comparison_key(row))
        if prior is None:
            continue
        comparable = (row.get('policy_version') == prior.get('policy_version') == POLICY_VERSION
                      and row.get('catalog_sha256') == prior.get('catalog_sha256')
                      and row['completed_turns'] == prior['completed_turns']
                      and row['stop_reason'] in ('turn_limit', 'terminal')
                      and prior['stop_reason'] in ('turn_limit', 'terminal'))
        rows.append(dict(spec=row['spec'], comparable=comparable,
            previous_outcome=prior['outcome'], outcome=row['outcome'],
            previous_completed_turns=prior['completed_turns'], completed_turns=row['completed_turns'],
            previous_save_sha256=prior.get('final_save_sha256'), final_save_sha256=row.get('final_save_sha256')))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--eras', nargs='+', choices=ERAS, default=list(ERAS))
    parser.add_argument('--factions', nargs='+', help='Override the two representative factions in each selected era')
    parser.add_argument('--seeds', nargs='+', type=int, default=[3])
    parser.add_argument('--policies', nargs='+', choices=POLICIES, default=list(POLICIES))
    parser.add_argument('--turns', type=int, default=6)
    parser.add_argument('--max-seconds', type=int, default=45)
    parser.add_argument('--max-commands', type=int, default=3000)
    parser.add_argument('--max-runs', type=int, default=18)
    parser.add_argument('--difficulty', choices=['easy', 'normal', 'hard'], default='normal')
    parser.add_argument('--backend', choices=['python', 'rust'], default='python')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    parser.add_argument('--checkpoint', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        spec = json.loads(args.worker)
        catalog = Catalog(ROOT/'game/data/campaigns'/(spec['scenario']+'.json'))
        if spec['faction'] not in catalog.factions:
            parser.error('Faction is absent from this scenario: '+spec['faction'])
        with using_backend(spec['backend']):
            _write(args.output, BalanceReplay(catalog, spec, checkpoint=args.checkpoint).run_bounded())
        return 0
    if not 1 <= args.turns <= 360 or not 5 <= args.max_seconds <= 600 or not 10 <= args.max_commands <= 100000 or not 1 <= args.max_runs <= 72:
        parser.error('Bounds: turns 1..360, seconds 5..600, commands 10..100000, runs 1..72')
    if any(not 1 <= seed <= 0xffffffff for seed in args.seeds):
        parser.error('Seeds must be between 1 and 2^32-1')
    specs = plan(args.eras, args.factions, args.seeds, args.policies, turns=args.turns,
                 max_seconds=args.max_seconds, max_commands=args.max_commands,
                 difficulty=args.difficulty, backend=args.backend)
    if len(specs) > args.max_runs:
        parser.error(f'{len(specs)} requested runs exceed --max-runs {args.max_runs}; select a smaller matrix')
    if len({digest(row) for row in specs}) != len(specs):
        parser.error('Duplicate eras/factions/seeds/policies are not allowed')
    previous = None
    if args.compare:
        try:
            previous = json.loads(args.compare.read_text())
            if (not isinstance(previous, dict) or previous.get('schema') != SCHEMA
                    or not isinstance(previous.get('runs'), list)
                    or any(not isinstance(row, dict) or not isinstance(row.get('spec'), dict)
                           or row.get('outcome') not in ('win', 'loss', 'unresolved')
                           or not isinstance(row.get('stop_reason'), str)
                           or type(row.get('completed_turns')) is not int
                           or any(key not in row['spec'] for key in
                                  ('scenario', 'faction', 'seed', 'policy', 'difficulty', 'backend', 'turns'))
                           or any(not isinstance(row['spec'][key], str) for key in
                                  ('scenario', 'faction', 'policy', 'difficulty', 'backend'))
                           or any(type(row['spec'][key]) is not int for key in ('seed', 'turns'))
                           for row in previous['runs'])):
                raise ValueError('Unsupported comparison report')
            comparison_index(previous['runs'])
        except (OSError, ValueError) as error:
            parser.error(str(error))
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    source_sha = hashlib.sha256()
    for file in sorted((ROOT/'source/remake').glob('*.py')):
        source_sha.update(file.name.encode()+b'\0'+file.read_bytes())
    started = time.monotonic()
    report = dict(schema=SCHEMA, commit=revision, engine_source_sha256=source_sha.hexdigest(),
                  benchmark_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  policy_version=POLICY_VERSION, runs=[], failures=[])
    for spec in specs:
        try:
            report['runs'].append(execute(spec))
        except Exception as error:
            report['failures'].append(dict(spec=spec, error=f'{type(error).__name__}: {error}'))
    report['summary'] = summarize(report['runs'])
    if previous is not None:
        report['comparison'] = comparison(report['runs'], previous)
    report['elapsed_seconds'] = round(time.monotonic()-started, 3)
    _write(args.output, report)
    print(json.dumps(dict(runs=len(report['runs']), failures=len(report['failures']),
                         elapsed_seconds=report['elapsed_seconds'], output=str(args.output))))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
