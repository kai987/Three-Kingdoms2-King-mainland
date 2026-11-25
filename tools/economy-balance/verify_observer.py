"""Verify that observing a campaign preserves every committed state and RNG cursor."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory

from common import Catalog, HeadlessCampaign, ROOT, TOOL_ROOT, git, to_json
from observe import run_scenario
from observer_telemetry import config
from remake.march_core import backend_status


def plain_checksums(scenario, seed, turns):
    catalog = Catalog(ROOT / 'game/data/campaigns' / (scenario + '.json'))
    game = HeadlessCampaign(catalog, record_journal=False)
    game.command('new', dict(faction='observer', seed=seed, difficulty='normal'), 0)
    hashes = [game.export_save(compact=True)['checksum']]
    for _ in range(turns):
        if game.state.phase == 'finished':
            break
        game.command('observe_turn', {}, game.revision)
        hashes.append(game.export_save(compact=True)['checksum'])
    return hashes


def verify(scenario, seed, months, group):
    with TemporaryDirectory() as path:
        data = run_scenario(scenario, seed, months, Path(path), group,
                            config(TOOL_ROOT / 'tools/economy-balance/observer-config.json'), hash_turns=True)
    if data['outcome'] == 'error':
        raise RuntimeError(data['failure']['trace'])
    observed = data['committed_save_sha256']
    if group.startswith('F'):
        from remake import logistics_strategy
        with logistics_strategy.experiment(4,army=group in {'F1','F3'},recovery=group in {'F2','F3'}):
            expected = plain_checksums(scenario, seed, months * 3)
    elif group.startswith('E'):
        from remake import logistics_strategy
        with logistics_strategy.experiment(int(group[-1])):
            expected = plain_checksums(scenario, seed, months * 3)
    else:
        try:
            from remake import logistics_strategy
        except ImportError:
            expected = plain_checksums(scenario, seed, months * 3)
        else:
            with logistics_strategy.experiment(0):
                expected = plain_checksums(scenario, seed, months * 3)
    if len(observed) != len(expected):
        raise AssertionError(f'{scenario}: committed state count differs')
    for turn, (actual, reference) in enumerate(zip(observed, expected)):
        if actual != reference:
            raise AssertionError(f'{scenario}: observation changed the compact save after {turn} turns')
    return dict(scenario=scenario, seed=seed, group=group, requested_months=months,
                engine_commit=git('rev-parse', 'HEAD').decode().strip(), backend=backend_status()['engine'],
                completed_turns=data['completed_turns'], matched_state_hashes=len(expected),
                observation_rows=data['telemetry']['rows'], checkpoints=expected)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--months', type=int, default=12)
    parser.add_argument('--group', choices=('A','D','E1','E2','E3','E4','F1','F2','F3'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.scenario, args.seed, args.months, args.group)
    to_json(args.output, result)
    print(f"{result['matched_state_hashes']} identical compact saves (including RNG state)")
