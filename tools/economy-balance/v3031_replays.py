"""Matched demand replays and verifiable capture of historical convoy 3634."""
from argparse import ArgumentParser
from contextlib import ExitStack
import csv
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import git, sha256, to_json
from remake import convoy_relief, grain_units, logistics, transport_capacity, transport_emergency
from v3021_checkpoints import campaign, configure
from v303_capacity_audit import checkpoint, fixed, fixed_replay
from v303_experiments import options as previous_options
from v303_replay_checks import checksum, journey_snapshot
from v3031_experiments import options


def demand_replay(task):
    with patch('v303_capacity_audit.options', options):
        return fixed_replay(task)


def convoy_snapshot(engine, ident):
    state = engine.state
    row = next((item for item in logistics._pool(state)['convoys'] if item['id'] == ident), None)
    if row is None:
        return None
    detail = journey_snapshot(state, ident)
    with grain_units.using(state):
        review = transport_emergency.Review(engine, state)
        city = state.cities.get(detail['node'])
        receiving = [key for key, point in state.cities.items() if transport_emergency.can_receive(engine,state,row,point)]
        choices = [] if city is None else review.options(row, city.id, receiving)
        relief = convoy_relief.request(engine,state,row)
        detail.update(turn=state.turn, city_owner=None if city is None else city.owner,
            city_stock=None if city is None else city.grain,
            local_grain_legal=None if city is None or city.owner != row['owner']
                              else transport_emergency.stock(engine,state,city),
            source_owner=state.cities[row['source']].owner,
            receives_here=city is not None and city.id in receiving,
            relief_eligible=relief is not None,
            legal_relief_meeting=None if relief is None else relief.city,
            relief_grain_required=None if relief is None else relief.required,
            best_receiving_options=[dict(city=entry.target, needed=entry.budget.total, days=entry.quote.days,
                path=entry.quote.route['path'], stock=state.cities[entry.target].grain)
                for entry in sorted(choices, key=transport_emergency.option_rank)[:5]])
    return detail


def capture(args):
    engine = campaign('208-10')
    actual_events, daily, fixed_states = [], [], []
    args.output.mkdir(parents=True, exist_ok=True)

    def receipt(event, row):
        if row.get('id') == 3634:
            actual_events.append(dict(event=event,**row))

    def details(event, row):
        if row.get('convoy_id', row.get('convoy')) == 3634:
            daily.append(dict(event=event,**row))

    with ExitStack() as stack:
        configure(stack, 211, 221, detailed=True)
        from remake import winter_weather
        stack.enter_context(winter_weather.experiment(5, adjustments=winter_weather.CORRECTIONS,
                                                     detailed=True, observe=details))
        stack.enter_context(transport_capacity.observing(receipt))
        engine.command('new', dict(faction='observer', seed=2026, difficulty='normal',
            transport_capacity_rules_version=303, transport_capacity_options=previous_options('C4')), 0)
        while engine.state.turn <= 721:
            turn = engine.state.turn
            if turn in (711, 712, 715, 721):
                with transport_capacity.observing(None):
                    snapshot = convoy_snapshot(engine, 3634)
                if snapshot is None:
                    raise ValueError(f'Expected historical convoy missing at turn {turn}')
                dest = args.output/f'convoy-3634-turn-{turn}.json.gz'
                with gzip.open(dest,'wt',encoding='utf-8') as stream:
                    json.dump(dict(scenario='208-10', seed=2026, strategy=211, weather=221, turn=turn,
                                   source=git('rev-parse','HEAD').decode().strip(), save=engine.export_save()),stream)
                fixed_states.append(dict(snapshot, state_sha256=checksum(engine), save_sha256=sha256(dest.read_bytes())))
            if turn % 30 == 0:
                print('3634 replay turn', turn, flush=True)
            if turn == 721:
                break
            engine.command('observe_turn',{},engine.revision)
        ending = fixed_states[-1]
    control = args.prior/'transport-capacity-events.jsonl.gz'
    with gzip.open(control,'rt',encoding='utf-8') as stream:
        expected = [row for row in map(json.loads,stream) if row.get('id') == 3634]
    with (args.prior/'convoy-survival.csv').open(encoding='utf-8',newline='') as stream:
        archived = next(row for row in csv.DictReader(stream) if row['convoy_id']=='3634')
    assert actual_events == expected, 'Historical capacity/receipt trace differs'
    assert ending['troops'] == int(archived['current_escort'])
    assert ending['hunger'] == int(archived['escort_hunger_loss'])
    assert ending['node'] == archived['actual_position']
    result = dict(matched_reference_receipts=len(expected), source=git('rev-parse','HEAD').decode().strip(),
                  archive_sha256=sha256(control.read_bytes()), ending=ending, checkpoints=fixed_states,
                  capacity_events=actual_events, weather_events=daily)
    to_json(args.output/'historical-3634-replay.json',result)
    print(json.dumps({key:result[key] for key in ('matched_reference_receipts','ending')},ensure_ascii=False))


def review_1860(args):
    fixture=checkpoint(args.checkpoint)
    engine=campaign(fixture['scenario'])
    with ExitStack() as stack:
        configure(stack,fixture['strategy'],fixture['weather'],detailed=True)
        engine.load_save(fixture['save'],0)
        evidence=[]
        for _ in range(args.turns+1):
            row=convoy_snapshot(engine,1860)
            if row is None:
                break
            evidence.append(row)
            if len(evidence)<=args.turns:
                engine.command('observe_turn',{},engine.revision)
    to_json(args.output,dict(convoy=1860,checkpoint_sha256=sha256(args.checkpoint.read_bytes()),
                             source=git('rev-parse','HEAD').decode().strip(), checkpoints=evidence))
    print(json.dumps(dict(samples=len(evidence), first=evidence[0], last=evidence[-1]),ensure_ascii=False))


def review_fixed_snapshots(args):
    rows = []
    for path in args.checkpoints:
        fixture=checkpoint(path)
        engine=campaign(fixture['scenario'])
        with ExitStack() as stack:
            configure(stack,fixture['strategy'],fixture['weather'],detailed=True)
            engine.load_save(fixture['save'],0)
            row=convoy_snapshot(engine,3634)
            if row is None:
                raise ValueError(f'Missing controlled historical convoy at turn {fixture["turn"]}')
        rows.append(dict(row,fixture_sha256=sha256(path.read_bytes()),loaded_state_sha256=checksum(engine)))
    to_json(args.output,dict(source=git('rev-parse','HEAD').decode().strip(),verified_snapshots=len(rows),rows=rows))
    print(json.dumps([dict(turn=row['turn'],node=row['node'],relief_eligible=row['relief_eligible'],
        legal_relief_meeting=row['legal_relief_meeting']) for row in rows],ensure_ascii=False))


def main():
    parser = ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='mode',required=True)
    replay=subs.add_parser('fixed')
    replay.add_argument('prior',type=Path)
    replay.add_argument('output',type=Path)
    replay.add_argument('checkpoints',nargs='+',type=Path)
    replay.add_argument('--workers',type=int,default=2)
    replay.set_defaults(groups=('D1','D2'))
    historical=subs.add_parser('capture-3634')
    historical.add_argument('prior',type=Path)
    historical.add_argument('output',type=Path)
    other=subs.add_parser('review-1860')
    other.add_argument('checkpoint',type=Path)
    other.add_argument('output',type=Path)
    other.add_argument('--turns',type=int,default=48)
    snapshots=subs.add_parser('review-3634-checkpoints')
    snapshots.add_argument('output',type=Path)
    snapshots.add_argument('checkpoints',nargs='+',type=Path)
    args=parser.parse_args()
    if args.mode=='fixed':
        fixed(args,replay=demand_replay)
    elif args.mode=='capture-3634':
        capture(args)
    elif args.mode=='review-1860':
        review_1860(args)
    else:
        review_fixed_snapshots(args)


if __name__=='__main__':
    main()
