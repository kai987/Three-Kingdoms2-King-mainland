"""Replay army 111 at an exact pre-gate state from the actual 263-05 observation."""
from argparse import ArgumentParser
from collections import Counter
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path.cwd()/'tools'/'economy-balance'))
from common import sha256, to_json
from observe import RecordedCampaign
from remake import command_books, logistics_strategy, transport_coordination
from remake.campaign import digest, verified_save_content
from v3021_checkpoints import campaign, configure
from v30412_campaigns import run_pair_side


ARMY = 111
CITY = 'jiameng'
START = 60
TURNS = 7


def compare(saved, scene, strategy):
    results = []
    original_state = digest(verified_save_content(saved))
    for variant in ('K0', 'K1', 'K2'):
        measures, transit, city_meals, orders = [], [], [], []

        def actual(event, row):
            if event == 'city_meal_settled' and row['city'] == CITY:
                city_meals.append(row)
            if event == 'unit_meal_settled' and row['unit_kind'] == 'march' and row['unit_id'] == ARMY:
                measures.append(row)
            if event == 'relief_handoff' and row.get('army') == ARMY:
                transit.append(row)

        def diagnostic(event, row):
            if event == 'demand' and row.get('target_kind') == 'march' and row.get('target') == ARMY:
                orders.append(row)

        game = campaign(scene)
        with ExitStack() as stack:
            configure(stack, strategy, 23)
            game.load_save(saved, 0)
            if digest(verified_save_content(game.export_save(compact=True))) != original_state:
                raise ValueError('Reloaded short window differs from the original observation')
            state = game.state
            army = next(row for row in state.extension['travel']['marches'] if row['id'] == ARMY)
            opening = dict(turn=state.turn, rng=game.to_dict()['rng'], city_grain=state.cities[CITY].grain,
                           next_meal_resources=army['supply']['remaining'],
                           command_books=command_books.remaining(state, army['owner']),
                           route=army['quote']['path'])
            if variant == 'K0':
                state.extension.pop(transport_coordination.FIELD)
                state.extension.pop(transport_coordination.POOL)
            elif variant == 'K1':
                state.extension[transport_coordination.FIELD] = transport_coordination.RECOVERY
                features = state.extension[transport_coordination.POOL]['features']
                for key in features.keys() - transport_coordination.FEATURES:
                    features.pop(key)
            game.validate(state)
            stack.enter_context(logistics_strategy.observing(actual))
            stack.enter_context(transport_coordination.observing(diagnostic))
            for _ in range(TURNS):
                game.command('observe_turn', {}, game.revision)
        totals = Counter()
        for row in measures:
            totals.update(required=row['required_grain'], paid=row['paid_grain'], missing=row['missing_grain'],
                          hungry_days=int(row['hunger_day']), hunger_losses=row['losses'],
                          city_refill=(row['refill'] or {}).get('actual_received_grain', 0))
        results.append(dict(variant=variant, opening=opening, army_meals=measures, city_meals=city_meals,
                            courier_handoffs=transit, scheduler=orders, totals=dict(totals),
                            endpoint=digest(game.to_dict()), rng=game.to_dict()['rng']))
    return results


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('observation', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    proof = json.loads(args.observation.read_bytes())
    case = dict(proof['case'], wave='weimieshu-recapture')
    case.pop('options')
    case.pop('winter_221')
    saved = []
    snapshot = args.output/'weimieshu-before-60.save.json.gz'
    original = RecordedCampaign.command

    def capture(game, action, payload, revision):
        if action == 'observe_turn' and game.state.turn == START and not saved:
            saved.append(game.export_save(compact=True))
        return original(game, action, payload, revision)

    with patch.object(RecordedCampaign, 'command', capture):
        repeated = run_pair_side((args.output/'recapture', case))
    if not saved and snapshot.is_file():
        with gzip.open(snapshot, 'rt', encoding='utf-8') as stream:
            saved.append(json.load(stream))
    if repeated['terminal_checksum'] != proof['terminal_checksum'] or len(saved) != 1:
        raise ValueError('The exact full run could not be reproduced')
    if not snapshot.is_file():
        with gzip.open(snapshot, 'wt', encoding='utf-8') as stream:
            json.dump(saved[0], stream, ensure_ascii=False, separators=(',', ':'))
    results = compare(saved[0], case['scenario'], case['strategy'])
    to_json(args.output/'weimieshu-same-state-comparison.json',
            dict(original_terminal_matches=True, terminal_checksum=proof['terminal_checksum'],
                 start_turn=START, turns=TURNS, original_save_sha256=sha256(snapshot.read_bytes()),
                 original_state_checksum=digest(verified_save_content(saved[0])), results=results))
    for row in results:
        print(row['variant'], row['opening'], row['totals'], len(row['courier_handoffs']), flush=True)


if __name__ == '__main__':
    main()
