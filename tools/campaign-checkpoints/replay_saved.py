"""Replay a declared public command sequence from an actual saved campaign.

This starts a NEW directed verification leg, not a resumed Replay call frame.
No new game, administration, end-turn or random draw is inserted on load. The
caller supplies provenance; a valid save checksum alone does not prove natural
origin. Keep the originating report, save and selection policy with the result.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

_spec = importlib.util.spec_from_file_location('_saved_checkpoints', Path(__file__).with_name('run.py'))
checkpoints = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checkpoints)
soak = checkpoints.soak


class _SavedPlayer(soak.Replay):
    def __init__(self, catalog, faction, seed, backend):
        self.game = soak.HeadlessCampaign(catalog)
        self.catalog_sha = checkpoints.digest(catalog.data)
        self.backend, self.progress = backend, False
        self.commands, self.receipts = Counter(), Counter()
        self.recent_commands, self.checkpoints, self.succession, self.samples = [], [], [], []
        self.seen_receipts = set()
        self.transcript = hashlib.sha256()
        self.game.load_save(deepcopy(self._origin_save), 0)
        if checkpoints.encoded(self.game.export_save()) != self._origin_save:
            raise AssertionError('Complete saved origin changed on load')
        if self.game.state.player != faction or self.game.state.seed != seed:
            raise ValueError('Declared faction/seed differs from saved origin')
        self.initial = soak.snapshot(self.game)
        soak.assert_invariants(self.game)
        # Existing historical reports are not receipts of this new leg.
        self.seen_receipts = {(r['turn'], r['kind'], r['details']['convoy_id'])
            for r in self.game.state.extension['logistics']['reports']}


class SavedCheckpointReplay(checkpoints._CheckpointObserver, _SavedPlayer):
    policy = 'directed-public-saved-commands-v1'

    def __init__(self, catalog, saved, spec, backend, *, output=None, observe=True,
                 clock=time.monotonic):
        self._origin_save = checkpoints.encoded(saved)
        # Use the same public bounds as new-game observation.
        checkpoints.settings(catalog, spec['faction'], spec['seed'], spec['turns'],
            spec['max_commands'], spec['max_seconds'])
        super().__init__(catalog, spec, backend, output=output, observe=observe, clock=clock)
        if self.game.state.phase == 'city':
            self.last_city_checkpoint = dict(checkpoints.campaign_status(self.game.state), completed_turns=0)
            self._progress_turn = self.game.state.turn
        self._persist()


def sequence(value):
    """Only accepted commands, including the exact expected committed boundary."""
    if not isinstance(value, list) or not value or len(value) > 100000:
        raise ValueError('Expected 1..100000 accepted public commands')
    for index, row in enumerate(value, 1):
        if (not isinstance(row, dict) or type(row.get('index')) is not int or row['index'] != index
                or not isinstance(row.get('command'), str) or row['command'] in ('new', 'load')
                or not isinstance(row.get('payload'), dict)
                or not isinstance(row.get('state_sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', row['state_sha256'])
                or row.get('phase') not in ('city', 'ai', 'arrivals', 'battle', 'result', 'finished')
                or type(row.get('turn')) is not int or row['turn'] < 1
                or not isinstance(row.get('rng'), dict)
                or set(row['rng']) != {'state', 'draws'}
                or type(row['rng']['state']) is not int or not 1 <= row['rng']['state'] <= 0xffffffff
                or type(row['rng']['draws']) is not int or not 0 <= row['rng']['draws'] <= 100000000):
            raise ValueError('Malformed public journal row '+str(index))
    return value


def replay_leg(catalog, saved, rows, spec, backend, output, *, observe):
    start, replay, status, stop, error = time.monotonic(), None, 'passed', 'sequence_end', None
    try:
        with checkpoints.using_backend(backend):
            replay = SavedCheckpointReplay(catalog, saved, spec, backend, output=output, observe=observe)
            for row in rows:
                replay.command(row['command'], **row['payload'])
                state = replay.game.state
                if (replay.game.journal[-1]['after_sha256'] != row['state_sha256']
                        or state.phase != row['phase'] or state.turn != row['turn']
                        or dict(state=state.rng.state, draws=state.rng.draws) != row['rng']):
                    raise AssertionError('Recorded public boundary differs at '+str(row['index']))
                soak.assert_invariants(replay.game)
                if state.turn - replay.initial['turn'] > spec['turns']:
                    raise checkpoints.VerificationLimit('turn_limit')
    except checkpoints.VerificationLimit as exc:
        status, stop = 'incomplete', str(exc)
    except Exception as exc:
        status, stop, error = 'failed', 'execution_error', type(exc).__name__+': '+str(exc)
    result = dict(backend=backend, observe=observe, verification_status=status,
        stop_reason=stop, error=error, elapsed_seconds=round(time.monotonic()-start, 3))
    if replay is not None:
        final = checkpoints.encoded(replay.game.export_save())
        observation = replay.observation()
        if replay.clock()-replay.observer_started >= spec['max_seconds'] and status == 'passed':
            status, stop = 'incomplete', 'wall_time'
        if replay.pending and status == 'passed':
            status, stop = 'incomplete', 'pending_without_continuation'
        if checkpoints.digest(catalog.data) != replay.catalog_sha:
            status, stop = 'failed', 'catalog_changed'
        result.update(verification_status=status, stop_reason=stop,
            command_count=sum(replay.commands.values()), commands=dict(replay.commands),
            command_sha256=replay.transcript.hexdigest(), final_save_sha256=checkpoints.digest(final),
            campaign=checkpoints.campaign_status(replay.game.state),
            last_city_checkpoint=replay.last_city_checkpoint, observation=observation,
            learnability=dict(opening=replay.opening_learnability,
                final=checkpoints.learnability_snapshot(replay.game)), terminal=replay.terminal,
            main_native_calls=replay.main_native_calls)
        checkpoints.write(output/'final.save.json', final)
        replay._persist(status)
    checkpoints.write(output/'leg-report.json', result)
    return result


def run(catalog, saved, rows, spec, output, *, provenance):
    sequence(rows)
    if not isinstance(provenance, dict) or not all(isinstance(provenance.get(k), str)
            and provenance[k].strip() for k in ('origin', 'selection_policy', 'classification')):
        raise ValueError('Explicit origin, selection_policy and classification required')
    output = checkpoints.output_directory(output)
    before = checkpoints.source_hashes()
    before[str(Path(__file__).relative_to(checkpoints.ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = dict(schema='tk2-directed-saved-replay-v1', policy=SavedCheckpointReplay.policy,
        scenario=catalog.data['id'], catalog_sha256=checkpoints.digest(catalog.data),
        provenance=deepcopy(provenance), origin_save_sha256=checkpoints.digest(saved),
        journal_sha256=checkpoints.digest(rows), sources_before=before, settings=spec, legs=[])
    checkpoints.write(output/'origin.save.json', saved)
    checkpoints.write(output/'input-commands.json', rows)
    for backend in checkpoints.BACKENDS:
        for observe in (True, False):
            folder = output/(backend+('-observed' if observe else '-baseline'))
            folder.mkdir()
            leg = replay_leg(catalog, saved, rows, spec, backend, folder, observe=observe)
            report['legs'].append(leg)
            checkpoints.write(output/'report.json', report)
    after = checkpoints.source_hashes()
    after[str(Path(__file__).relative_to(checkpoints.ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    states = [r['verification_status'] for r in report['legs']]
    status = 'failed' if 'failed' in states else 'incomplete' if 'incomplete' in states else 'passed'
    signatures = [(r.get('command_count'), r.get('command_sha256'), r.get('final_save_sha256'))
        for r in report['legs']]
    parity = 'passed' if status == 'passed' and all(r == signatures[0] for r in signatures) else 'unverified'
    if status == 'passed' and parity != 'passed':
        status = 'failed'
    origin_unchanged = checkpoints.digest(saved) == report['origin_save_sha256']
    report.update(verification_status=status if before == after and origin_unchanged else 'failed', parity=parity,
        sources_after=after, sources_unchanged=before == after,
        origin_unchanged=origin_unchanged)
    checkpoints.write(output/'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--start-save', type=Path, required=True)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--turns', type=int, default=36)
    parser.add_argument('--max-commands', type=int, default=5000)
    parser.add_argument('--max-seconds', type=float, default=300)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        catalog = checkpoints.indexed_catalog(args.scenario)
        saved = json.loads(args.start_save.read_text())
        rows = [json.loads(line) for line in args.journal.read_text().splitlines() if line.strip()]
        spec = checkpoints.settings(catalog, saved['state']['player'], saved['state']['seed'],
            args.turns, args.max_commands, args.max_seconds)
        report = run(catalog, saved, rows, spec, args.output_dir,
            provenance=json.loads(args.provenance.read_text()))
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({k:report[k] for k in ('verification_status','parity','sources_unchanged','origin_unchanged')}))
    return 0 if report['verification_status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
