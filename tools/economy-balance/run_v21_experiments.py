"""Run deterministic, auditable groups in a bounded process pool."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from pathlib import Path

from common import TOOL_ROOT, git, to_json
from observe import SCENARIOS, run_scenario
from observer_telemetry import config

SEEDS = (2026, 2027, 2028)
OPENERS = ('190-01', '208-10')
LONG = ('184-02', '208-10')
STAGES = ('D', 'E1', 'E2', 'E3', 'E4')


def schedule(wave, group):
    if wave == 'pilot':
        return [(name, 2026, 60, scenario) for name, scenario in product(STAGES, OPENERS) if name in group]
    if wave == 'paired':
        return [(name, seed, 60, scenario) for seed, scenario, name in product(SEEDS, SCENARIOS, ('D','E4'))
                if name in group]
    return [(name, 2026, 240, scenario) for scenario, name in product(LONG, ('D','E4')) if name in group]


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('wave', choices=('pilot','paired','long'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workers', default=6, type=int)
    parser.add_argument('--groups', choices=STAGES, nargs='+', default=STAGES)
    parser.add_argument('--missing-only', action='store_true', help='Reuse only runs at this exact commit')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('workers must be positive')
    expected = schedule(args.wave, args.groups)
    settings = config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    head = git('rev-parse','HEAD').decode().strip()
    pending, results = [], []
    for name, seed, months, scenario in expected:
        folder = args.output/'observed'/name/str(seed)/str(months)
        file = folder/scenario/'run.json'
        if args.missing_only and file.is_file():
            import json
            saved = json.loads(file.read_text())
            if (saved['head']==head and saved['seed']==seed and saved['scenario']==scenario
                    and saved['requested_months']==months and saved['outcome'] in ('complete','natural_end')
                    and saved['group']==name and saved['telemetry']['config']==settings):
                results.append(saved)
                continue
        pending.append((scenario, seed, months, folder, name))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        runs = [pool.submit(run_scenario,*params,settings) for params in pending]
        for done in as_completed(runs):
            results.append(done.result())
    ordered = sorted(results,key=lambda row:(row['requested_months'],row['scenario'],row['seed'],row['group']))
    to_json(args.output/f"{args.wave}-{'-'.join(args.groups)}.json",ordered)
    return any(row['outcome']=='error' for row in results)


if __name__=='__main__':
    raise SystemExit(main())
