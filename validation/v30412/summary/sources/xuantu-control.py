"""Replay the genuine Red Cliffs opening and compare schedulers at its first Xuantu deficit."""
from argparse import ArgumentParser
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path.cwd()/'tools'/'economy-balance'))
from common import sha256, to_json
from observe import RecordedCampaign
from remake import faction_economy, facilities, grain_dispatch, grain_units, logistics_strategy, transport_coordination
from remake.campaign import digest, verified_save_content
from v3021_checkpoints import campaign, configure
from v30412_campaigns import run_pair_side


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('observation', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    case = json.loads(args.observation.read_bytes())
    spec = dict(case['case'], wave='xuantu-recapture')
    spec.pop('options')
    spec.pop('winter_221')
    target_turn = 44
    saved = []
    original = RecordedCampaign.command

    def capture(game, action, payload, revision):
        if action == 'observe_turn' and game.state.turn == target_turn and not saved:
            saved.append(game.export_save(compact=True))
        return original(game, action, payload, revision)

    with patch.object(RecordedCampaign, 'command', capture):
        recaptured = run_pair_side((args.output/'recapture', spec))
    if recaptured['terminal_checksum'] != case['terminal_checksum'] or len(saved) != 1:
        raise ValueError('Controlled pre-debit evidence did not reproduce the actual campaign')
    payload = verified_save_content(saved[0])
    digest_original = digest(payload)
    path = args.output/'xuantu-before-44.save.json.gz'
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        json.dump(saved[0], stream, ensure_ascii=False, separators=(',', ':'))
    cases = []
    for variant in ('L0', 'L1', 'L2'):
        city_id = 'xuantu'
        opening, rows, physical = {}, [], []

        def record(event, row):
            if event == 'city_meal_settled' and row['city'] == city_id:
                rows.append(row)

        def receipt(event, row):
            if event in ('departure','delivery') and row.get('target') == city_id:
                physical.append(dict(event=event, **row))

        game = campaign('208-10')
        with ExitStack() as stack:
            configure(stack, 211, 23)
            game.load_save(saved[0], 0)
            if digest(verified_save_content(game.export_save(compact=True))) != digest_original:
                raise ValueError('Start of paired short window differs')
            state = game.state
            opening_rng = game.to_dict()['rng']
            if variant == 'L0':
                state.extension.pop(transport_coordination.FIELD)
                state.extension.pop(transport_coordination.POOL)
            elif variant == 'L1':
                state.extension[transport_coordination.FIELD] = transport_coordination.RECOVERY
                options = state.extension[transport_coordination.POOL]['features']
                for key in tuple(options):
                    if key not in transport_coordination.FEATURES:
                        options.pop(key)
            game.validate(state)
            with grain_units.using(state):
                city = state.cities[city_id]
                owner = city.owner
                plan = faction_economy.plan(game, state, owner, granary=True,
                                            coordinated=transport_coordination.enabled(state))
                offers = facilities.emergency_quote(game, state, city, plan.cities[city_id].monthly*2)
                included, excluded = grain_dispatch._donors(game, state, plan,
                    coordinated=transport_coordination.enabled(state),
                    reserve=transport_coordination.feature(state,'reserve'))
                opening = dict(owner=owner, grain=city.grain, gold=city.gold, local_offer=offers,
                    sources=[dict(city=key, actor=actor, floor=floor) for group in included.values()
                             for key, actor, _, floor in group if key!=city_id],
                    excluded={key: reason for key,reason in excluded.items() if key!=city_id})
            stack.enter_context(logistics_strategy.observing(record))
            stack.enter_context(transport_capacity.observing(receipt))
            for _ in range(3):
                game.command('observe_turn', {}, game.revision)
        cases.append(dict(variant=variant, opening=opening, opening_rng=opening_rng, settlements=rows,
                          actual_freight=physical, result=digest(game.to_dict())))
    to_json(args.output/'xuantu-same-state-comparison.json',
            dict(original_terminal_matches=True, terminal_checksum=case['terminal_checksum'],
                 exact_pre_debit_state=digest_original, exact_pre_debit_file=path.name,
                 saved_file_sha256=sha256(path.read_bytes()), start_turn=target_turn, cases=cases))


if __name__ == '__main__':
    main()
