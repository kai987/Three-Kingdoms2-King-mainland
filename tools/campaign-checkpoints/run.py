"""Observe real committed intermediate saves without changing the soak policy.

Only public commands from explicitly named existing Replay policies are used. First states
are saved; their next actual command is replayed on fresh Python/Rust clones.
Turn/command/wall limits are verification budgets, never campaign outcomes.
"""
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'source'))
from remake.campaign import Catalog, canonical, digest
from remake.march_core import backend_status, using_backend

_spec = importlib.util.spec_from_file_location('_checkpoint_soak', ROOT/'tools/campaign-soak/run.py')
soak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(soak)
_spec = importlib.util.spec_from_file_location('_checkpoint_balance', ROOT/'tools/campaign-balance/run.py')
balance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(balance)

SCHEMA = 'tk2-natural-checkpoints-v3'
KINDS = ('partial_placement', 'active_conditions', 'siege_formation',
         'siege_orders', 'siege_combat', 'duel')
STAGES = ('formation', 'orders', 'combat')
CONDITIONS = ('phantom', 'chain', 'qimen')
ENCOUNTERS = tuple(mode+'_'+stage for mode in ('field', 'fort') for stage in STAGES)
STRATA = ('partial_placement',) + tuple('condition_'+kind for kind in CONDITIONS) + ENCOUNTERS + ('duel',)
BACKENDS = ('python', 'rust')
POLICIES = ('soak', 'offensive')


class VerificationLimit(Exception):
    pass


def encoded(value):
    return json.loads(canonical(value))


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(path)


def output_directory(value, *, root=ROOT):
    """Refuse repository/symlink targets and every nonempty existing folder."""
    if value is None:
        raise ValueError('An explicit output directory is required')
    target, repository = Path(value).expanduser().resolve(), Path(root).resolve()
    if target == repository or repository in target.parents:
        raise ValueError('Output must be outside the repository, including symlinks')
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError('Output directory must be absent or empty; prior evidence is preserved')
    target.mkdir(parents=True, exist_ok=True)
    return target


def settings(catalog, faction, seed, turns, max_commands, max_seconds):
    for value, low, high, label in ((seed, 1, 0xffffffff, 'seed'),
            (turns, 1, 360, 'turns'), (max_commands, 1, 100000, 'max commands')):
        if type(value) is not int or not low <= value <= high:
            raise ValueError('Invalid '+label)
    if (type(max_seconds) not in (int, float) or not math.isfinite(max_seconds)
            or not 5 <= max_seconds <= 3600):
        raise ValueError('Invalid max seconds')
    if type(faction) is not str or faction not in catalog.factions:
        raise ValueError('Faction is absent from the selected catalog')
    return dict(faction=faction, seed=seed, turns=turns,
                max_commands=max_commands, max_seconds=max_seconds)


def observed_kinds(state):
    """Read validated committed states, not ephemeral work inside an AI call."""
    if state.phase != 'battle' or not state.battle:
        return ()
    extension = state.battle['extended']
    result = []
    placement = extension.get('placement') or {}
    confirmed, order = placement.get('confirmed'), placement.get('order')
    if (type(confirmed) is int and isinstance(order, list)
            and 0 < confirmed < len(order)):
        result.append('partial_placement')
    conditions = extension.get('conditions', {}).get('units', {})
    if any(type(row.get('remaining')) is int and row['remaining'] > 0
           for row in conditions.values()):
        result.append('active_conditions')
    stage = (extension.get('siege') or {}).get('stage')
    if stage in ('formation', 'orders', 'combat'):
        result.append('siege_'+stage)
    if extension.get('duel'):
        result.append('duel')
    return tuple(result)


def observed_strata(state):
    """Fixed detailed labels; a field witness cannot occupy a fort's slot."""
    coarse = observed_kinds(state)
    if not coarse:
        return ()
    extension = state.battle['extended']
    labels = set(coarse) & {'partial_placement', 'duel'}
    for row in extension.get('conditions', {}).get('units', {}).values():
        if type(row.get('remaining')) is int and row['remaining'] > 0:
            if row.get('kind') not in CONDITIONS:
                raise ValueError('Unsupported observed condition kind')
            labels.add('condition_'+row['kind'])
    encounter = extension.get('siege') or {}
    if encounter.get('stage') in STAGES:
        # Match siege._mode's existing legacy-save default, not city terrain
        # or an assumption that the defending side must own the fort.
        mode = encounter.get('mode', 'siege')
        if mode not in ('field', 'siege'):
            raise ValueError('Unsupported observed encounter mode')
        labels.add(('fort' if mode == 'siege' else 'field')+'_'+encounter['stage'])
    return tuple(key for key in STRATA if key in labels)


def coverage(keys, observed, verified):
    keys = tuple(keys)
    status = lambda present: 'complete' if all(key in present for key in keys) else 'partial' if any(key in present for key in keys) else 'unobserved'
    return dict(denominator=len(keys), observed_count=sum(key in observed for key in keys),
        verified_count=sum(key in verified for key in keys),
        observed_status=status(observed), verified_status=status(verified),
        unobserved=[key for key in keys if key not in observed],
        unverified=[key for key in keys if key not in verified])


def detailed_coverage(observed, verified):
    return dict(**coverage(STRATA, observed, verified),
        encounters=coverage(ENCOUNTERS, observed, verified),
        conditions=coverage(tuple('condition_'+kind for kind in CONDITIONS), observed, verified))


def campaign_status(state):
    owned = sum(city.owner == state.player for city in state.cities.values())
    outcome = state.extension['outcome'] if state.phase == 'finished' else 'unresolved'
    return dict(phase=state.phase, turn=state.turn, date=[state.year,state.month,state.day],
        player=state.player, owned_cities=owned, active_cities=len(state.cities),
        outcome=outcome, unification_verified=state.phase == 'finished'
        and outcome == 'victory' and bool(state.cities) and owned == len(state.cities))


def learnability_snapshot(game):
    """Actual opening/current officers, not a claim about unseen intervals."""
    from remake.tactical_ai import _learnability, maximum_tactic
    special = _learnability()[1]
    state = game.state
    cities = {ident:city.id for city in state.cities.values() for ident in city.roster.officer_ids}
    combat = {unit['id'] for side in ('attackers','defenders')
              for unit in (state.battle or {}).get(side, [])}
    rows = [dict(person_id=officer.person_id, runtime_id=ident,
        alive=officer.alive, faction=officer.faction_id, city=cities.get(ident),
        experience=officer.experience, tier=officer.tier,
        maximum_tactic=maximum_tactic(officer), in_battle=ident in combat)
        for ident,officer in state.officers.items() if officer.person_id in special]
    return sorted(rows, key=lambda row:row['person_id'])


class _CheckpointObserver:
    policy = 'soak'

    def __init__(self, catalog, spec, backend, *, output=None, observe=True,
                 clock=time.monotonic):
        if backend not in BACKENDS or type(observe) is not bool:
            raise ValueError('Invalid checkpoint execution mode')
        self.spec, self.output, self.observe = deepcopy(spec), output, observe
        self.clock, self.started = clock, clock()
        self.observer_spec, self.observer_started = deepcopy(spec), self.started
        self.captures, self.capture_saves, self.pending = {}, {}, []
        self.observation_counts = dict.fromkeys(KINDS, 0)
        self.stratum_counts = dict.fromkeys(STRATA, 0)
        self.main_native_calls = 0
        self.opening_learnability, self.last_city_checkpoint, self.terminal = None, None, None
        self._progress_turn = None
        if self.policy == 'offensive':
            # Delegate the complete existing policy, including its public
            # set_domestic payload transformation; do not create a hybrid.
            super().__init__(catalog, dict(spec, backend=backend, policy='offensive',
                difficulty='normal', scenario=catalog.data['id']))
        else:
            super().__init__(catalog, spec['faction'], spec['seed'], backend)
        self.opening_learnability = learnability_snapshot(self.game)
        self._persist()

    def _journal(self, kind, payload):
        if self.output is not None:
            row = dict(index=sum(self.commands.values()), command=kind, payload=payload,
                state_sha256=self.game.journal[-1]['after_sha256'],
                phase=self.game.state.phase, turn=self.game.state.turn,
                rng=dict(state=self.game.state.rng.state,draws=self.game.state.rng.draws))
            # Close/flush per accepted command. This is process-stop evidence,
            # not fsync/power-loss durability and not a resumable Python frame.
            with (Path(self.output)/'commands.jsonl').open('a') as stream:
                stream.write(canonical(row)+'\n')

    def _persist(self, verification_status='running'):
        if self.output is not None:
            write(Path(self.output)/'progress.json', dict(schema=SCHEMA,
                verification_status=verification_status, policy=self.policy, observe=self.observe,
                commands=sum(self.commands.values()), campaign=campaign_status(self.game.state),
                last_city_checkpoint=self.last_city_checkpoint,
                opening_learnability=self.opening_learnability,
                current_learnability=learnability_snapshot(self.game),
                observation=self.observation(), terminal=self.terminal))

    def _terminal_loads(self, kind, payload, saved):
        probes = []
        catalog_before = digest(self.game.catalog.data)
        for backend in BACKENDS:
            with using_backend(backend):
                clone = soak.HeadlessCampaign(self.game.catalog)
                clone.load_save(encoded(saved), 0)
                if encoded(clone.export_save()) != saved:
                    raise AssertionError('Terminal save changed on '+backend)
                probes.append(dict(backend=backend, complete_save_equal=True))
        if (encoded(self.game.export_save()) != saved
                or digest(self.game.catalog.data) != catalog_before):
            raise AssertionError('Terminal load probe mutated the actual game or catalog')
        self.terminal = dict(status='verified_terminal_load', command=kind,
            payload=deepcopy(payload), checksum=saved['checksum'],
            campaign=campaign_status(self.game.state), loads=probes,
            next_command='none: finished campaigns do not require another command')
        if self.output is not None:
            write(Path(self.output)/'terminal.save.json', saved)

    def _probe(self, kind, payload, before, after):
        catalog_before = digest(self.game.catalog.data)
        main_after = encoded(self.game.export_save())
        if main_after != after:
            raise AssertionError('Actual game changed before the continuation probe')
        for key in self.pending:
            if self.capture_saves[key] != before:
                raise AssertionError('Checkpoint is not the immediately preceding actual state')
        # All labels from one committed snapshot share one physical save and
        # one actual next-command pair, rather than multiplying proof counts.
        probes = []
        for backend in BACKENDS:
            with using_backend(backend):
                calls = backend_status()
                clone = soak.HeadlessCampaign(self.game.catalog)
                clone.load_save(encoded(before), 0)
                if encoded(clone.export_save()) != before:
                    raise AssertionError('Checkpoint load changed the complete save')
                clone.command(kind, deepcopy(payload), clone.revision)
                result = encoded(clone.export_save())
                if result != after:
                    raise AssertionError('Checkpoint continuation differs on '+backend)
                probes.append(dict(backend=backend, before_checksum=before['checksum'],
                    after_checksum=result['checksum'], state_sha256=digest(result['state']),
                    rng=deepcopy(result['state']['rng']), complete_save_equal=True,
                    native_calls=backend_status()['calls']-calls['calls']))
            if (encoded(self.game.export_save()) != main_after
                    or digest(self.game.catalog.data) != catalog_before):
                raise AssertionError('Continuation probe mutated the actual game or catalog')
        for key in self.pending:
            self.captures[key]['continuation'] = dict(status='verified', command=kind,
                payload=deepcopy(payload), before_checksum=before['checksum'],
                after_checksum=after['checksum'], before_phase=before['state']['phase'],
                after_phase=after['state']['phase'], probes=deepcopy(probes))
        self.pending.clear()

    def command(self, kind, /, **payload):
        if self.clock()-self.observer_started >= self.observer_spec['max_seconds']:
            raise VerificationLimit('wall_time')
        if sum(getattr(self, 'commands', {}).values()) >= self.observer_spec['max_commands']:
            raise VerificationLimit('command_limit')
        before = encoded(self.game.export_save()) if self.pending else None
        if self.pending and any(self.capture_saves[key] != before for key in self.pending):
            raise AssertionError('Checkpoint is not the immediately preceding actual state')
        status = backend_status()
        if status['engine'] != self.backend:
            raise AssertionError('Caller must select the explicit main backend context')
        super().command(kind, **payload)
        self.main_native_calls += backend_status()['calls']-status['calls']
        # BalanceReplay may transform a public payload. Record/probe the
        # effective committed command, never the caller's pre-policy payload.
        payload = deepcopy(self.recent_commands[-1]['payload'])
        self._journal(kind, payload)
        state = self.game.state
        city_boundary = state.phase == 'city' and self._progress_turn != state.turn
        if city_boundary:
            self.last_city_checkpoint = campaign_status(state)
            self.last_city_checkpoint['completed_turns'] = state.turn-getattr(self,'initial',{}).get('turn',state.turn)
            self._progress_turn = state.turn
        if not self.observe:
            if city_boundary:
                self._persist()
            return
        coarse, strata = observed_kinds(self.game.state), observed_strata(self.game.state)
        labels = list(dict.fromkeys((*coarse, *strata)))
        fresh = [key for key in labels if key not in self.captures]
        terminal = state.phase == 'finished' and self.terminal is None
        continued = bool(self.pending)
        after = encoded(self.game.export_save()) if continued or fresh or terminal else None
        if continued:
            self._probe(kind, payload, before, after)
        for key in coarse:
            self.observation_counts[key] += 1
        for key in strata:
            self.stratum_counts[key] += 1
        filename = fresh[0]+'.save.json' if fresh else None
        for key in fresh:
            battle = self.game.state.battle
            extension = battle['extended']
            row = dict(kind=key, command=kind, payload=deepcopy(payload),
                command_index=sum(self.commands.values()), phase=self.game.state.phase,
                turn=self.game.state.turn, battle_id=battle['id'], battle_round=battle['round'],
                checksum=after['checksum'], state_sha256=digest(after['state']),
                rng=deepcopy(after['state']['rng']), file=filename, labels=fresh[:],
                continuation=dict(status='pending_without_continuation'))
            if key == 'partial_placement':
                p = extension['placement']
                row['placement'] = dict(confirmed=p['confirmed'], count=len(p['order']))
            if key == 'active_conditions' or key.startswith('condition_'):
                row['condition_kinds'] = [kind for kind in CONDITIONS if 'condition_'+kind in strata]
            if key in ENCOUNTERS or key.startswith('siege_'):
                row['encounter_mode'] = extension['siege'].get('mode', 'siege')
                row['encounter_mode_source'] = 'explicit' if 'mode' in extension['siege'] else 'legacy_default'
                row['encounter_context'] = {name:deepcopy(extension['siege'].get(name))
                    for name in ('fort', 'map_id', 'cell')}
                row['encounter_context']['mode'] = row['encounter_mode']
            self.captures[key], self.capture_saves[key] = row, after
            self.pending.append(key)
        if fresh and self.output is not None:
            write(Path(self.output)/filename, after)
        if terminal:
            self._terminal_loads(kind, payload, after)
        if fresh or continued or terminal or city_boundary:
            self._persist()

    def observation(self):
        observed = {key for key, count in self.stratum_counts.items() if count}
        verified = {key for key in STRATA if key in self.captures
                    and self.captures[key]['continuation']['status'] == 'verified'}
        files = {row['file'] for row in self.captures.values()}
        continued = {row['file'] for row in self.captures.values()
                     if row['continuation']['status'] == 'verified'}
        return dict(observation_counts=deepcopy(self.observation_counts),
                    checkpoints=deepcopy([row for key,row in self.captures.items() if key in KINDS]),
                    unobserved=[key for key in KINDS if not self.observation_counts[key]],
                    pending_without_continuation=[key for key in self.pending if key in KINDS],
                    strata=dict(observation_counts=deepcopy(self.stratum_counts),
                        checkpoints=deepcopy([row for key,row in self.captures.items() if key in STRATA]),
                        pending_without_continuation=[key for key in self.pending if key in STRATA],
                        coverage=detailed_coverage(observed, verified)),
                    physical_saves=dict(captured=len(files), verified=len(continued),
                        verified_backend_commands=len(BACKENDS)*len(continued)))


class CheckpointReplay(_CheckpointObserver, soak.Replay):
    """Original unchanged soak policy (the default)."""


class OffensiveCheckpointReplay(_CheckpointObserver, balance.BalanceReplay):
    """Existing balance public-orders-v1/offensive policy, kept distinct."""
    policy = 'offensive'


def run_leg(catalog, spec, backend, *, observe, output=None, policy='soak'):
    if policy not in POLICIES:
        raise ValueError('Invalid checkpoint player policy')
    started = time.monotonic()
    replay, result, stop, status, error = None, None, 'turn_limit', 'passed', None
    try:
        with using_backend(backend):
            cls = CheckpointReplay if policy == 'soak' else OffensiveCheckpointReplay
            replay = cls(catalog, spec, backend, output=output, observe=observe)
            result = replay.run(spec['turns'])
    except (VerificationLimit, balance.LimitReached) as exc:
        stop, status = 'command_limit' if str(exc) == 'commands' else str(exc), 'incomplete'
    except AssertionError as exc:
        if str(exc).startswith(('Phase resolution exceeded ', 'Replay exceeded the 100000 command budget')):
            stop, status = 'execution_budget', 'incomplete'
        else:
            stop, status, error = 'execution_error', 'failed', type(exc).__name__+': '+str(exc)
    except Exception as exc:
        stop, status, error = 'execution_error', 'failed', type(exc).__name__+': '+str(exc)
    if replay is None:
        return dict(backend=backend, observe=observe, verification_status=status,
                    stop_reason=stop, error=error, initialized=False), None
    state = replay.game.state
    final_save = encoded(replay.game.export_save())
    if digest(catalog.data) != replay.catalog_sha:
        status, error = 'failed', 'Replay mutated the source catalog'
    if replay.clock()-replay.observer_started >= spec['max_seconds'] and status == 'passed':
        status, stop = 'incomplete', 'wall_time'
    observation = replay.observation()
    if (observation['pending_without_continuation'] or observation['strata']['pending_without_continuation']) and status == 'passed':
        status, stop = 'incomplete', 'pending_without_continuation'
    terminal = state.phase == 'finished' and state.extension['outcome'] in ('victory', 'defeat')
    if terminal and status == 'passed':
        stop = 'terminal'
    row = dict(backend=backend, observe=observe, verification_status=status,
        initialized=True, stop_reason=stop, error=error, requested_turns=spec['turns'],
        completed_turns=state.turn-replay.initial['turn'], phase=state.phase,
        campaign_outcome=state.extension['outcome'] if terminal else 'unresolved',
        commands=dict(replay.commands), command_sha256=replay.transcript.hexdigest(),
        main_backend=backend, main_native_calls=replay.main_native_calls,
        final_save_sha256=digest(final_save), final_checksum=final_save['checksum'],
        rng=deepcopy(final_save['state']['rng']), result=result, observation=observation,
        policy=policy, campaign=campaign_status(state),
        last_city_checkpoint=replay.last_city_checkpoint,
        learnability=dict(opening=replay.opening_learnability, final=learnability_snapshot(replay.game)),
        terminal=replay.terminal,
        elapsed_seconds=round(time.monotonic()-started, 3))
    if output is not None:
        write(Path(output)/'final.save.json', final_save)
        journal = Path(output)/'commands.jsonl'
        row['command_journal_sha256'] = hashlib.sha256(journal.read_bytes()).hexdigest()
        write(Path(output)/'leg-report.json', row)
        replay._persist(status)
    return row, final_save


def source_hashes():
    paths = sorted((ROOT/'source/remake').glob('*.py'))
    paths += sorted((ROOT/'game').glob('*.js'))
    paths += [ROOT/'tools/campaign-soak/run.py', ROOT/'tools/campaign-balance/run.py',
              ROOT/'game/config/references/original-battle-tactics-v1.json', Path(__file__).resolve()]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def indexed_catalog(name, *, root=ROOT):
    source = json.loads((root/'game/config/campaigns/index.json').read_text())
    compiled = json.loads((root/'game/data/campaigns/index.json').read_text())
    if (source.get('schema') != 'tk2-campaign-sources-v1'
            or compiled.get('schema') != 'tk2-campaign-index-v1'):
        raise ValueError('Invalid campaign index schema')
    choices = {}
    for row in source['scenarios']:
        file = Path(row['file'])
        if (file.parent != Path('scenarios') or file.suffix != '.json'
                or row['id'] != 'mainland'+file.stem or file.stem in choices):
            raise ValueError('Invalid canonical campaign identity')
        choices[file.stem] = (root/'game/data/campaigns'/file.name, row['id'])
    if (set(compiled['catalogs']) != {'campaigns/'+p.name for p, _ in choices.values()}
            or len(compiled['catalogs']) != len(choices)):
        raise ValueError('Canonical and compiled campaign indexes disagree')
    if type(name) is not str or name not in choices:
        raise ValueError('Scenario must name an indexed shipped campaign')
    path, identity = choices[name]
    if path.resolve().parent != (root/'game/data/campaigns').resolve():
        raise ValueError('Campaign path escapes its indexed directory')
    catalog = Catalog(path)
    if catalog.data['id'] != identity:
        raise ValueError('Catalog identity disagrees with its source index')
    return catalog


def run(catalog, spec, output, *, backends=BACKENDS, policy='soak'):
    if policy not in POLICIES:
        raise ValueError('Invalid checkpoint player policy')
    if (not isinstance(backends, (tuple, list)) or not backends
            or any(type(backend) is not str for backend in backends)
            or len(set(backends)) != len(backends)
            or any(backend not in BACKENDS for backend in backends)):
        raise ValueError('Invalid backend selection')
    if (not isinstance(spec, dict)
            or set(spec) != {'faction', 'seed', 'turns', 'max_commands', 'max_seconds'}):
        raise ValueError('Invalid checkpoint settings')
    spec = settings(catalog, **spec)
    output = output_directory(output)
    before, start = source_hashes(), time.monotonic()
    report = dict(schema=SCHEMA, verification_status='running', scenario=catalog.data['id'],
        catalog_sha256=catalog.sha256, spec=spec, backends=list(backends),
        policy=('unchanged campaign-soak Replay' if policy == 'soak' else
                'existing campaign-balance '+balance.POLICY_VERSION+'/offensive'),
        player_policy=policy, limit_scope='before each public command; no hard per-command timeout',
        checkpoint_scope='first committed state per legacy kind and fixed mode/condition stratum; no injected people/resources/results',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        sources_before=before, legs=[], parity='unverified')
    write(output/'report.json', report)
    materials = []
    for backend in backends:
        folder = output/backend; folder.mkdir()
        observed, saved = run_leg(catalog, spec, backend, observe=True, output=folder, policy=policy)
        row = dict(observed=observed, baseline=None, observer_did_not_change_policy=False)
        report['legs'].append(row)
        if observed['verification_status'] != 'passed':
            break
        baseline_folder = folder/'baseline'; baseline_folder.mkdir()
        baseline, baseline_saved = run_leg(catalog, spec, backend, observe=False, output=baseline_folder, policy=policy)
        row['baseline'] = baseline
        same = (baseline['verification_status'] == 'passed' and saved == baseline_saved
                and observed['result'] == baseline['result']
                and observed['command_journal_sha256'] == baseline['command_journal_sha256'])
        row['observer_did_not_change_policy'] = same
        if not same:
            if baseline['verification_status'] == 'passed':
                row['observed']['verification_status'] = 'failed'
                row['observed']['error'] = 'Observer changed the original policy transcript/save/result'
            break
        observation = deepcopy(observed['observation'])
        # Native register/cache calls are accounting, not game state. They can
        # differ with an already-warm explicit backend context.
        for capture in observation['checkpoints'] + observation['strata']['checkpoints']:
            for probe in capture['continuation'].get('probes', []):
                probe.pop('native_calls', None)
        materials.append(dict(result={k:v for k,v in observed['result'].items() if k != 'backend'},
                              save=saved, observation=observation))
        write(output/'report.json', report)
    states = [r['observed']['verification_status'] for r in report['legs']]
    states += [r['baseline']['verification_status'] for r in report['legs'] if r['baseline']]
    status = 'failed' if 'failed' in states else 'incomplete' if 'incomplete' in states else 'passed'
    if len(materials) != len(backends) and status == 'passed':
        status = 'failed'
    if len(materials) == len(backends):
        report['parity'] = ('single_backend_only' if len(backends) == 1 else
                           'passed' if all(row == materials[0] for row in materials) else 'failed')
        if report['parity'] == 'failed':
            status = 'failed'
    after = source_hashes()
    report.update(verification_status=status, sources_after=after,
                  sources_unchanged=before == after, elapsed_seconds=round(time.monotonic()-start, 3))
    if before != after:
        report['verification_status'] = 'failed'
    observed = {key for leg in report['legs'] for key, count in
                leg['observed'].get('observation', {}).get('observation_counts', {}).items() if count}
    report.update(observed_kinds=[key for key in KINDS if key in observed],
                  unobserved_kinds=[key for key in KINDS if key not in observed],
                  coverage_status='complete' if len(observed) == len(KINDS) else 'partial' if observed else 'unobserved')
    strata = {key for leg in report['legs'] for key,count in
              leg['observed'].get('observation', {}).get('strata', {}).get('observation_counts', {}).items() if count}
    verified = {row['kind'] for leg in report['legs'] for row in
                leg['observed'].get('observation', {}).get('strata', {}).get('checkpoints', [])
                if row['continuation']['status'] == 'verified'}
    report.update(stratum_definitions=list(STRATA), detailed_coverage=detailed_coverage(strata, verified))
    write(output/'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', default='209-06')
    parser.add_argument('--faction', default='wei')
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--turns', type=int, default=3)
    parser.add_argument('--max-commands', type=int, default=2000)
    parser.add_argument('--max-seconds', type=float, default=300)
    parser.add_argument('--backends', choices=BACKENDS, nargs='+', default=list(BACKENDS))
    parser.add_argument('--policy', choices=POLICIES, default='soak')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        catalog = indexed_catalog(args.scenario)
        spec = settings(catalog, args.faction, args.seed, args.turns, args.max_commands, args.max_seconds)
        report = run(catalog, spec, args.output_dir, backends=tuple(args.backends), policy=args.policy)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({k:report[k] for k in ('verification_status', 'scenario', 'parity',
          'coverage_status', 'observed_kinds', 'unobserved_kinds', 'detailed_coverage', 'elapsed_seconds')}, ensure_ascii=False))
    return 0 if report['verification_status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
