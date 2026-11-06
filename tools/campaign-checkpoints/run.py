"""Observe real committed intermediate saves without changing the soak policy.

Only public commands from the existing Replay are used. First natural states
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

SCHEMA = 'tk2-natural-checkpoints-v1'
KINDS = ('partial_placement', 'active_conditions', 'siege_formation',
         'siege_orders', 'siege_combat', 'duel')
BACKENDS = ('python', 'rust')


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


class CheckpointReplay(soak.Replay):
    def __init__(self, catalog, spec, backend, *, output=None, observe=True,
                 clock=time.monotonic):
        if backend not in BACKENDS or type(observe) is not bool:
            raise ValueError('Invalid checkpoint execution mode')
        self.spec, self.output, self.observe = deepcopy(spec), output, observe
        self.clock, self.started = clock, clock()
        self.captures, self.capture_saves, self.pending = {}, {}, []
        self.observation_counts = dict.fromkeys(KINDS, 0)
        self.main_native_calls = 0
        super().__init__(catalog, spec['faction'], spec['seed'], backend)

    def _probe(self, kind, payload, before, after):
        catalog_before = digest(self.game.catalog.data)
        main_after = encoded(self.game.export_save())
        if main_after != after:
            raise AssertionError('Actual game changed before the continuation probe')
        for key in self.pending:
            if self.capture_saves[key] != before:
                raise AssertionError('Checkpoint is not the immediately preceding actual state')
            probes = []
            for backend in BACKENDS:
                with using_backend(backend):
                    calls = backend_status()
                    clone = soak.HeadlessCampaign(self.game.catalog)
                    clone.load_save(encoded(self.capture_saves[key]), 0)
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
            self.captures[key]['continuation'] = dict(status='verified', command=kind,
                payload=deepcopy(payload), before_checksum=before['checksum'],
                after_checksum=after['checksum'], before_phase=before['state']['phase'],
                after_phase=after['state']['phase'], probes=probes)
        self.pending.clear()

    def command(self, kind, **payload):
        if self.clock()-self.started >= self.spec['max_seconds']:
            raise VerificationLimit('wall_time')
        if sum(getattr(self, 'commands', {}).values()) >= self.spec['max_commands']:
            raise VerificationLimit('command_limit')
        before = encoded(self.game.export_save()) if self.pending else None
        if self.pending and any(self.capture_saves[key] != before for key in self.pending):
            raise AssertionError('Checkpoint is not the immediately preceding actual state')
        status = backend_status()
        if status['engine'] != self.backend:
            raise AssertionError('Caller must select the explicit main backend context')
        super().command(kind, **payload)
        self.main_native_calls += backend_status()['calls']-status['calls']
        if not self.observe:
            return
        after = encoded(self.game.export_save())
        if self.pending:
            self._probe(kind, payload, before, after)
        for key in observed_kinds(self.game.state):
            self.observation_counts[key] += 1
            if key in self.captures:
                continue
            battle = self.game.state.battle
            extension = battle['extended']
            row = dict(kind=key, command=kind, payload=deepcopy(payload),
                command_index=sum(self.commands.values()), phase=self.game.state.phase,
                turn=self.game.state.turn, battle_id=battle['id'], battle_round=battle['round'],
                checksum=after['checksum'], state_sha256=digest(after['state']),
                rng=deepcopy(after['state']['rng']), file=key+'.save.json',
                continuation=dict(status='pending_without_continuation'))
            if key == 'partial_placement':
                p = extension['placement']
                row['placement'] = dict(confirmed=p['confirmed'], count=len(p['order']))
            if key == 'active_conditions':
                row['condition_kinds'] = sorted({v['kind'] for v in extension['conditions']['units'].values()})
            if key.startswith('siege_'):
                row['encounter_mode'] = extension['siege'].get('mode', 'siege')
            self.captures[key], self.capture_saves[key] = row, after
            self.pending.append(key)
            if self.output is not None:
                write(Path(self.output)/row['file'], after)

    def observation(self):
        return dict(observation_counts=deepcopy(self.observation_counts),
                    checkpoints=deepcopy(list(self.captures.values())),
                    unobserved=[key for key in KINDS if not self.observation_counts[key]],
                    pending_without_continuation=list(self.pending))


def run_leg(catalog, spec, backend, *, observe, output=None):
    started = time.monotonic()
    replay, result, stop, status, error = None, None, 'turn_limit', 'passed', None
    try:
        with using_backend(backend):
            replay = CheckpointReplay(catalog, spec, backend, output=output, observe=observe)
            result = replay.run(spec['turns'])
    except VerificationLimit as exc:
        stop, status = str(exc), 'incomplete'
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
    if replay.clock()-replay.started >= spec['max_seconds'] and status == 'passed':
        status, stop = 'incomplete', 'wall_time'
    observation = replay.observation()
    if observation['pending_without_continuation'] and status == 'passed':
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
        elapsed_seconds=round(time.monotonic()-started, 3))
    if output is not None:
        write(Path(output)/'final.save.json', final_save)
    return row, final_save


def source_hashes():
    paths = sorted((ROOT/'source/remake').glob('*.py'))
    paths += sorted((ROOT/'game').glob('*.js'))
    paths += [ROOT/'tools/campaign-soak/run.py', Path(__file__).resolve()]
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


def run(catalog, spec, output, *, backends=BACKENDS):
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
        policy='unchanged campaign-soak Replay', limit_scope='before each public command; no hard per-command timeout',
        checkpoint_scope='first committed natural state of each kind; no injected people/resources/results',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        sources_before=before, legs=[], parity='unverified')
    write(output/'report.json', report)
    materials = []
    for backend in backends:
        folder = output/backend; folder.mkdir()
        observed, saved = run_leg(catalog, spec, backend, observe=True, output=folder)
        row = dict(observed=observed, baseline=None, observer_did_not_change_policy=False)
        report['legs'].append(row)
        if observed['verification_status'] != 'passed':
            break
        baseline_folder = folder/'baseline'; baseline_folder.mkdir()
        baseline, baseline_saved = run_leg(catalog, spec, backend, observe=False, output=baseline_folder)
        row['baseline'] = baseline
        same = (baseline['verification_status'] == 'passed' and saved == baseline_saved
                and observed['result'] == baseline['result'])
        row['observer_did_not_change_policy'] = same
        if not same:
            if baseline['verification_status'] == 'passed':
                row['observed']['verification_status'] = 'failed'
                row['observed']['error'] = 'Observer changed the original policy transcript/save/result'
            break
        observation = deepcopy(observed['observation'])
        # Native register/cache calls are accounting, not game state. They can
        # differ with an already-warm explicit backend context.
        for capture in observation['checkpoints']:
            for probe in capture['continuation'].get('probes', []):
                probe.pop('native_calls')
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
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        catalog = indexed_catalog(args.scenario)
        spec = settings(catalog, args.faction, args.seed, args.turns, args.max_commands, args.max_seconds)
        report = run(catalog, spec, args.output_dir, backends=tuple(args.backends))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({k:report[k] for k in ('verification_status', 'scenario', 'parity',
          'coverage_status', 'observed_kinds', 'unobserved_kinds', 'elapsed_seconds')}, ensure_ascii=False))
    return 0 if report['verification_status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
