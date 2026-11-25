"""Audit historical army relief by run-scoped convoy ID; optionally replay E4."""
from argparse import ArgumentParser
from collections import Counter
from csv import DictReader
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from io import TextIOWrapper

from common import TOOL_ROOT, to_json
from observe import run_scenario
from observer_telemetry import config
from remake import logistics, march_supply

CASE = 'data/observed/E4/2027/60/207-09/'
FOCUS = {102, 156, 157, 253, 254}
PRIORITY = ((2027, '207-09'), (2027, '190-01'), (2026, '208-10'), (2026, '184-02'))


def table(archive, member):
    with archive.open(member) as stream:
        yield from DictReader(TextIOWrapper(stream, encoding='utf-8'))


def audit(path):
    results = dict(aggregate={}, cases={})
    with ZipFile(path) as archive:
        for group in ('D', 'E4'):
            accum = Counter()
            folders = [name[:-len('convoys.csv')] for name in archive.namelist()
                       if name.startswith(f'data/observed/{group}/')
                       and '/60/' in name and name.endswith('/convoys.csv')]
            if len(folders) != 21:
                raise ValueError(f'Expected 21 historical runs for {group}')
            for folder in folders:
                rows = list(table(archive, folder+'convoys.csv'))
                departures = {int(row['convoy_id']):row for row in rows if row['stage']=='departed'}
                losses = Counter()
                for row in table(archive, folder+'troop-flows.csv'):
                    if row['kind']=='convoy_hunger_deaths':
                        losses[int(row['reference'])] += int(row['count'])
                if losses.keys()-departures.keys():
                    raise ValueError(f'Missing original convoy departures in {folder}')
                for ident, departure in departures.items():
                    kind = 'army_relief' if departure['target_march'] not in ('', 'null') else 'other'
                    accum[kind+'_dispatches'] += 1
                    accum[kind+'_hunger_losses'] += losses[ident]
                    if folder == CASE and ident in FOCUS:
                        results['cases'][ident] = dict(
                            departure=departure, hunger_losses=losses[ident],
                            records=[row for row in rows if int(row['convoy_id'])==ident])
            results['aggregate'][group] = dict(accum)
    return results


def replay(seed, scenario, output):
    dispatch = logistics.dispatch
    cases = {}

    def traced(game, state, payload, owner, **options):
        ident = logistics._pool(state)['next_id']
        if (seed, scenario) != PRIORITY[0] or ident not in FOCUS:
            return dispatch(game, state, payload, owner, **options)
        source = state.cities[payload['source']]
        army = logistics._army(state, payload['target_march'], owner)
        policy = logistics._pool(state)['cities'][source.id]['policy']
        selected = logistics._meeting_quote(game, state, source, army, policy)
        eligibles = logistics._eligible(game, state, source)
        before = dict(turn=state.turn, source_grain=source.grain, requested_cargo=payload['cargo'],
                      source_policy=dict(policy), target_march=army['id'], target_route=army['quote'],
                      target_progress=army['supply']['route_days'], target_grain=army['supply']['remaining'],
                      target_waiting=army['supply']['waiting'], target_troops=march_supply.ration_units(
                          state, army['officers']) - 100*len(army['officers']),
                      meeting=selected[0], escort_candidates={str(i):state.officers[i].troops for i in eligibles})
        returned = logistics._safe_quote(game, state, state.cities[selected[0]], source, policy)
        result = dispatch(game, state, payload, owner, **options)
        journey = result['journeys'][0]
        before.update(actual_bag=journey['supply']['loaded'], actual_source_debit=before['source_grain']-source.grain,
                      escort=journey['departure_troops'], outbound=journey['quote'],
                      legal_return=None if returned is None else returned[1],
                      complete_travel_bag=None if returned is None else logistics.escort_rations(
                          game, state, payload['officers'], journey['quote'], returned[1]))
        cases[ident] = before
        return result

    settings = config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    with patch.object(logistics, 'dispatch', traced):
        run = run_scenario(scenario, seed, 60, output/'observed/E4'/str(seed)/'60', 'E4', settings)
    if cases:
        to_json(output/f'focus-{scenario}-{seed}.json', cases)
    return int(run['outcome']=='error')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--replay', nargs=2, metavar=('SEED','SCENARIO'))
    args = parser.parse_args()
    if args.baseline:
        to_json(args.output/'historical-army-relief.json', audit(args.baseline))
    if args.replay:
        return replay(int(args.replay[0]), args.replay[1], args.output)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
