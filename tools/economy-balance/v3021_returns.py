"""Compare only the new physical return review on a real historical checkpoint."""
from argparse import ArgumentParser
from contextlib import ExitStack
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from common import git, sha256, to_json
from remake import logistics, march_supply, strategic_granary, transport_emergency, winter_weather
from v3021_checkpoints import campaign, configure


def replay(checkpoint, ident, safety, turns):
    game = campaign(checkpoint['scenario'])
    logs, ending = [], []

    def observe(kind, row):
        if row.get('convoy_id',row.get('convoy')) == ident and kind in (
                'convoy_day','convoy_terminal','emergency_refill','emergency_decision','emergency_plan'):
            logs.append(dict(event=kind, **row))

    enabled = strategic_granary.enabled
    review = transport_emergency.review_return_node
    dock = logistics._dock

    def close(game, state, row, city, **options):
        outcome = dock(game,state,row,city,**options)
        if outcome and row['id'] == ident:
            receipt = logistics.grain_receipt(row,returned=True)
            ending.append(dict(city=city.id,
                tick=options.get('terminal_tick') or (state.turn-1)*10,
                troops=sum(state.officers[officer].troops for officer in row['officers']),
                hunger=sum(s['lost'] for journey in row['journeys'] for s in journey['supply']['starvation']),
                receipt=receipt, balanced=logistics.valid_grain_receipt(receipt)))
        return outcome

    with ExitStack() as stack:
        configure(stack, checkpoint['strategy'], checkpoint['weather'])
        stack.enter_context(winter_weather.experiment(5,adjustments=winter_weather.CORRECTIONS,
                                                      detailed=True,observe=observe))
        if safety:
            # Isolate return review from the rest of 3021 and from unrelated
            # convoys. The loaded save, RNG, and other rules stay identical.
            stack.enter_context(patch.object(strategic_granary,'enabled',
                lambda state,feature=None: True if feature=='return_safety' else enabled(state,feature)))
            stack.enter_context(patch.object(transport_emergency,'review_return_node',
                lambda game,state,row,tick: review(game,state,row,tick) if row['id']==ident else False))
        stack.enter_context(patch.object(logistics,'_dock',close))
        game.load_save(checkpoint['save'],0)
        inside = next((row for row in logistics._pool(game.state)['convoys'] if row['id']==ident),None)
        if inside is None:
            return dict(found=False, reason='not_present_at_checkpoint', trace=[], terminal=None)
        current = inside['journeys'][-1]
        before = dict(owner=inside['owner'], source=inside['source'], destination=inside['original_target'],
            status=inside['status'], delivered=inside['delivered']['grain'], path=current['quote']['path'],
            tick=current['supply']['clock_tick'], next_city=march_supply.next_city(current),
            bag=current['supply']['remaining'], initial_bag=inside['journeys'][0]['supply']['loaded'],
            troop_count=sum(inside['journeys'][0]['departure_troops'].values()))
        for _ in range(turns):
            if ending:
                break
            game.command('observe_turn',{},game.revision)
    return dict(found=True, starting=before, trace=logs, terminal=ending[0] if ending else None)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint',type=Path)
    parser.add_argument('convoy',type=int)
    parser.add_argument('output',type=Path)
    parser.add_argument('--turns',type=int,default=6)
    args = parser.parse_args()
    with gzip.open(args.checkpoint,'rt',encoding='utf-8') as stream:
        checkpoint=json.load(stream)
    before, after = (replay(checkpoint,args.convoy,mode,args.turns) for mode in (False,True))
    to_json(args.output,dict(scenario=checkpoint['scenario'],seed=checkpoint['seed'],
        strategy=checkpoint['strategy'],checkpoint_turn=checkpoint['turn'],convoy=args.convoy,
        checkpoint_sha256=sha256(args.checkpoint.read_bytes()), checkpoint_source=checkpoint['source'],
        runtime=git('rev-parse','HEAD').decode().strip(), control=before,candidate_return_only=after))


if __name__ == '__main__':
    main()
