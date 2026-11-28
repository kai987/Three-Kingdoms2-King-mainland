"""Replay two additional original 30412 states without recapturing them."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import ExitStack
import gzip
import json
from pathlib import Path

from common import sha256, to_json
from remake import faction_economy, facilities, grain_dispatch, grain_units, logistics_strategy
from remake import transport_coordination, transport_infrastructure as wharf
from remake.campaign import digest, verified_save_content
from v3021_checkpoints import campaign, configure
from v3042_experiments import log, open_stream, provenance

CASES = (
    ('xuantu', '208-10', 'xuantu', 44, 3, None, 'D2'),
    ('weimieshu', '263-05', 'jiameng', 60, 7, 111, 'D0+30412'),
)


def replay(source, archived, output, case, enabled):
    label, scenario, city, start, turns, army, background = case
    original = json.loads((archived/f'{label}-same-state-comparison.json').read_bytes())
    supplied = source/f'{label}-control'/f'{label}-before-{start}.save.json.gz'
    compressed = supplied.read_bytes()
    input_hash = sha256(compressed)
    assert input_hash == original.get('saved_file_sha256', original.get('original_save_sha256'))
    save = json.loads(gzip.decompress(compressed))
    save_hash = digest(verified_save_content(save))
    assert save_hash == original.get('exact_pre_debit_state', original.get('original_state_checksum'))
    game = campaign(scenario)
    mode = 'with-wharves' if enabled else 'control'
    file = output/f'{label}-{mode}.jsonl.gz'
    meals, courier = Counter(), []
    turns_state = []
    pending = []

    def actual(kind, row):
        if kind == 'unit_meal_settled' and row['unit_kind'] == 'march' and row['unit_id'] == army:
            meals.update(required=row['required_grain'], paid=row['paid_grain'], missing=row['missing_grain'],
                         hunger_days=int(row['hunger_day']), losses=row['losses'],
                         city_refill=(row['refill'] or {}).get('actual_received_grain', 0))
        elif kind == 'city_meal_settled' and row['city'] == city:
            meals.update(city_due=row['required_grain'], city_paid=row['paid_grain'], city_missing=row['missing_grain'])
        elif kind == 'relief_handoff' and army and row.get('army') == army:
            courier.append(row)
        else:
            return
        log(events, kind, row)

    def diagnostic(kind, row):
        if (army and row.get('target_kind') == 'march' and row.get('target') == army) or (
                row.get('target') == city or row.get('demand_target') == city):
            log(events, kind, row)
            if kind == 'demand':
                pending.append(row)

    with ExitStack() as stack:
        configure(stack, 211, 23)
        game.load_save(save, 0)
        assert digest(verified_save_content(game.export_save(compact=True))) == save_hash
        state = game.state
        assert state.turn == start
        rng = game.to_dict()['rng']
        with grain_units.using(state):
            if enabled:
                wharf.initialize(game, state, wharf.VERSION)
            owner = state.cities[city].owner
            plan = faction_economy.plan(game, state, owner, granary=True, coordinated=True)
            market = facilities.emergency_quote(game, state, state.cities[city], plan.cities[city].monthly*2)
            groups, excluded = grain_dispatch._donors(game, state, plan, coordinated=True,
                                                        reserve=transport_coordination.feature(state, 'reserve'))
            donors = [dict(city=key, actor=actor, reserve=floor)
                      for rows in groups.values() for key, actor, _, floor in rows if key != city]
        game.validate(state)
        events = open_stream(stack, file)
        stack.enter_context(logistics_strategy.observing(actual))
        stack.enter_context(transport_coordination.observing(diagnostic))
        stack.enter_context(wharf.observing(lambda kind, row: log(events, kind, row)))
        for _ in range(turns):
            game.command('observe_turn', {}, game.revision)
            current = game.to_dict()
            current['extension'].pop(wharf.FIELD, None)
            current['extension'].pop(wharf.POOL, None)
            turns_state.append(dict(turn=current['turn'], domain_sha256=digest(current), rng=current['rng']))
    assert meals['city_due'] - meals['city_paid'] == meals['city_missing']
    if army is not None:
        assert meals['required'] - meals['paid'] == meals['missing']
    return dict(label=label, mode=mode, scenario=scenario, city=city, army=army,
                background=background, turns=turns, start_turn=start, initial_rng=rng,
                input_sha256=input_hash, loaded_save_checksum=save_hash,
                market=market, donors=donors, donor_exclusion=excluded,
                facility_corridors=[ident for ident, row in game.catalog.infrastructure_routes.items()
                                    if city in (row['from'], row['to'])],
                meal_totals=dict(meals), real_courier_handoffs=courier,
                demand_marks=pending, checkpoints=turns_state, events=file.name,
                events_sha256=sha256(file.read_bytes()))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='V30412 validation build, with preserved control saves')
    parser.add_argument('archived_checks', type=Path, help='Published V30412 summary/checks directory')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    results = [replay(args.source, args.archived_checks, args.output, case, enabled)
               for case in CASES for enabled in (False, True)]
    for off, on in zip(results[::2], results[1::2], strict=True):
        assert off['checkpoints'] == on['checkpoints'], off['label']
        assert off['meal_totals'] == on['meal_totals'], off['label']
        assert off['real_courier_handoffs'] == on['real_courier_handoffs'], off['label']
    to_json(args.output/'checkpoint-probes.json', dict(provenance=provenance(), results=results))


if __name__ == '__main__':
    main()
