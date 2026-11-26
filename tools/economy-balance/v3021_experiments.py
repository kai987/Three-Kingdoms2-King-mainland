"""Reproduce the V3.0.2.1 comparisons with the released audited observer."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from common import TOOL_ROOT, to_json
from v302_experiments import run

WAVES = {
    'smoke': [(2026, '184-02', 212, 221, 2), (2026, '208-10', 211, 0, 2)],
    'dry': [(2027, '190-01', 211, 0, 60), (2026, '208-10', 211, 0, 60)],
    'winter': [(2026, '184-02', 211, 221, 60), (2026, '184-02', 212, 221, 60),
               (2026, '208-10', 211, 221, 60), (2026, '208-10', 212, 221, 60),
               (2031, '190-01', 211, 221, 60), (2026, '263-05', 211, 221, 60),
               (2034, '207-09', 211, 221, 60)],
    'long': [(2026, '184-02', 211, 221, 240), (2026, '208-10', 211, 221, 240),
             (2026, '208-10', 212, 221, 240)],
    'holdout': [(2035, '184-02', 211, 221, 60), (2036, '208-10', 212, 221, 60)],
    'relay': [(2026, '184-02', 211, 221, 60), (2026, '208-10', 211, 221, 60)],
}
GROUPS = ('G0', 'G1', 'G2', 'G3d', 'G3', 'G4', 'G4-relay', 'G4-no-winter')


def rules(group, weather):
    if group == 'G0':
        return None
    candidate = group not in ('G1', 'G2')
    options = dict(version=3021 if candidate else 302, proactive=True,
                   winter=bool(weather) and group != 'G4-no-winter', relay=group == 'G4-relay')
    if candidate:
        options.update(coordination=group != 'G3d', return_safety=group.startswith('G4'))
    return options


def simulate(output, case):
    wave, group, seed, scene, policy, weather, months = case
    if group == 'G0':
        result = run(output, (wave, 'S1', seed, scene, policy, weather, months), progress=True)
        return dict(result, group=group)
    return run(output, case, granary_options=rules(group, weather), progress=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('wave', choices=WAVES)
    parser.add_argument('--groups', nargs='+', choices=GROUPS, required=True)
    parser.add_argument('--scenario', action='append')
    parser.add_argument('--strategy', type=int, choices=(211, 212))
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--output', type=Path, default=TOOL_ROOT/'build/strategic-granary-v3021/final')
    args = parser.parse_args()
    cases = [(args.wave, group, seed, scene, strategy, weather, months)
             for seed, scene, strategy, weather, months in WAVES[args.wave] for group in args.groups
             if (not args.scenario or scene in args.scenario) and (not args.strategy or strategy == args.strategy)]
    label = '-'.join([args.wave, *args.groups, *(args.scenario or []), str(args.strategy or 'any')])
    to_json(args.output/f'planned-{label}.json', cases)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(simulate, args.output, case) for case in cases]
        finished = []
        for job in as_completed(futures):
            row = job.result()
            finished.append(row)
            print(json.dumps({key: row.get(key) for key in (
                'wave', 'group', 'scenario', 'seed', 'strategy', 'weather', 'outcome', 'completed_turns',
                'source', 'seconds', 'failure')}, ensure_ascii=False), flush=True)
    to_json(args.output/f'completed-{label}.json',
            sorted(finished,key=lambda row:(row['scenario'],row['strategy'],row['group'])))
    return int(any(row['outcome'] not in {'complete','natural_end'} for row in finished))


if __name__ == '__main__':
    raise SystemExit(main())
