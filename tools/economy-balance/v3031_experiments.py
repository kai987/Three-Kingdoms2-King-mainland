"""Frozen V3.0.3 safety and concurrency ablation with read-only slot observations."""
from argparse import ArgumentParser
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextvars import ContextVar
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import TOOL_ROOT, to_json
from remake import logistics, transport_capacity
from v302_experiments import run
from v303_experiments import WAVES as PRIOR_WAVES, options as prior_options

WAVES = {
    'five': [
        (2026, '184-02', 211, 221, 60), (2026, '184-02', 212, 221, 60),
        (2026, '208-10', 211, 221, 60), (2026, '208-10', 212, 221, 60),
        (2026, '263-05', 211, 221, 60), (2034, '207-09', 211, 221, 60),
        (2027, '190-01', 211, 0, 60),
    ],
    'long': PRIOR_WAVES['long'],
    'holdout': [(2039, '184-02', 211, 221, 60), (2040, '208-10', 212, 221, 60)],
    'smoke': [(2026, '208-10', 211, 221, 2), (2026, '184-02', 211, 0, 2)],
}
GROUPS = ('D0', 'D1', 'D2', 'D3')


def options(group):
    if group == 'D1':
        return dict.fromkeys(transport_capacity.FEATURES, False)
    return prior_options({'D0':'C0', 'D2':'C1', 'D3':'C4'}[group])


def install_urgent_probe(stack, folder):
    """Observe offer screening inside genuine city relief calls, without retrying them."""
    scope = ContextVar('relief_capacity_probe', default=None)
    stream = stack.enter_context(gzip.open(folder/'urgent-slot-observations.jsonl.gz',
                                          'wt', compresslevel=2, encoding='utf-8'))
    supply, blocker = logistics.dispatch_ai_supply, transport_capacity.dispatch_blocker

    def tracked_blocker(state, source, active=None):
        reason = blocker(state, source, active)
        request = scope.get()
        if request is not None and reason is not None:
            request['blocked'].append(dict(source=source.id, reason=reason, stock=source.grain,
                convoys=request['active'].get(source.id, []), dispatches=transport_capacity.dispatch_count(state, source.id)))
        return reason

    def tracked_supply(game, state, target, gold_goal, grain_goal, **kwargs):
        pool = state.extension.get('logistics')
        if pool is None:
            return supply(game, state, target, gold_goal, grain_goal, **kwargs)
        active = defaultdict(list)
        for row in pool['convoys']:
            if row['owner'] == target.owner or not transport_capacity.enabled(state, 'concurrency'):
                active[row['source']].append(dict(id=row['id'], owner=row['owner'], phase=row['status']))
        request = dict(turn=state.turn, owner=target.owner, target=target.id,
                       deadline_turns=kwargs.get('max_turns'), seasonal=bool(kwargs.get('seasonal')),
                       protected_officers=list(kwargs.get('protected_officers', ())),
                       grain_goal=grain_goal, source_stock=target.grain, gold_goal=gold_goal,
                       active=active, blocked=[])
        token = scope.set(request)
        before = pool['next_id']
        try:
            sent = supply(game, state, target, gold_goal, grain_goal, **kwargs)
        finally:
            scope.reset(token)
        request.pop('active')
        request.update(sent=bool(sent), convoy=before if sent else None)
        stream.write(json.dumps(request, ensure_ascii=False, separators=(',', ':'))+'\n')
        return sent

    stack.enter_context(patch.object(logistics, 'dispatch_ai_supply', tracked_supply))
    stack.enter_context(patch.object(transport_capacity, 'dispatch_blocker', tracked_blocker))


def simulate(task):
    folder, background, case = task
    _, cohort, _, _, _, weather, _ = case
    granary = dict(version=3021 if background == 'G4' else 302, proactive=True,
                   winter=bool(weather), relay=False)
    if background == 'G4':
        granary.update(coordination=True, return_safety=True)
    result = run(folder/background, case, granary_options=granary, capacity_options=options(cohort),
                 economy_background=background, instrument=install_urgent_probe, progress=True)
    result = {key:result.get(key) for key in ('source','outcome','group','scenario','wave','weather',
              'economy_background','strategy','seed','completed_turns','output','failure')}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def matrix(waves, groups, background):
    for wave in waves:
        for sample in WAVES[wave]:
            if background == 'G4' and sample != (2026, '208-10', 212, 221, 60):
                continue
            for group in groups:
                yield (wave, group, *sample)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('waves', nargs='+', choices=WAVES)
    parser.add_argument('--groups', nargs='+', choices=GROUPS, default=['D1','D2'])
    parser.add_argument('--background', choices=('G1','G4'), default='G1')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, default=TOOL_ROOT/'build/transport-concurrency-v3031')
    args = parser.parse_args()
    cases = list(matrix(args.waves, args.groups, args.background))
    label = '-'.join((*args.waves, args.background, *args.groups))
    to_json(args.output/f'planned-{label}.json', cases)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(simulate, ((args.output,args.background,case) for case in cases)))
    to_json(args.output/f'completed-{label}.json', results)
    return int(any(row['outcome'] not in ('complete','natural_end') for row in results))


if __name__ == '__main__':
    raise SystemExit(main())
