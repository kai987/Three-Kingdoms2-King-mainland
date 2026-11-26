"""Capture and replay real V3.0.2 strategic turns for paired performance checks."""
from argparse import ArgumentParser
from contextlib import ExitStack, nullcontext
import cProfile
import gzip
import json
from pathlib import Path
from resource import RUSAGE_SELF, getrusage
import sys
from time import monotonic, process_time
from unittest.mock import patch

from common import ROOT, Catalog, HeadlessCampaign, git, sha256, to_json
from remake import faction_economy, granary_planning, logistics, logistics_strategy
from remake import market_pricing, march_core, strategic_granary, transport_emergency, winter_weather
from remake.campaign import canonical
from v212_experiments import configured


def configure(stack, strategy, weather, detailed=False):
    flags = dict(proactive=True, winter=bool(weather), relay=False)
    stack.enter_context(configured('G4al') if strategy == 212 else
                        logistics_strategy.experiment(4, army=True, recovery=True))
    stack.enter_context(market_pricing.experiment(2))
    stack.enter_context(winter_weather.experiment(5 if weather else 0,
                        adjustments=winter_weather.CORRECTIONS if weather else 0,
                        detailed=detailed, observe=(lambda *_a, **_k: None) if detailed else None))
    stack.enter_context(transport_emergency.experiment(3 if weather else 0))
    stack.enter_context(strategic_granary.experiment(**flags))


def campaign(scenario):
    return HeadlessCampaign(Catalog(ROOT/'game/data/campaigns'/f'{scenario}.json'), record_journal=False)


def capture(args):
    game = campaign(args.scenario)
    with ExitStack() as stack:
        configure(stack, args.strategy, args.weather)
        if args.resume:
            with gzip.open(args.resume, 'rt', encoding='utf-8') as stream:
                previous = json.load(stream)
            key = args.scenario, args.seed, args.strategy, args.weather
            if key != tuple(previous[field] for field in ('scenario','seed','strategy','weather')):
                raise ValueError('Checkpoint metadata differs')
            game.load_save(previous['save'],0)
        else:
            game.command('new', dict(faction='observer', seed=args.seed, difficulty='normal'), 0)
        if game.state.turn > args.turn:
            raise ValueError('Requested checkpoint precedes the supplied state')
        while game.state.turn < args.turn:
            game.command('observe_turn', {}, game.revision)
            if game.state.turn % 30 == 0:
                print(f'{args.scenario} {args.strategy}: {game.state.turn}/{args.turn}', flush=True)
        saved = game.export_save()
        result = dict(scenario=args.scenario, seed=args.seed, turn=args.turn, strategy=args.strategy,
                      weather=args.weather, source=git('rev-parse', 'HEAD').decode().strip(),
                      map_sha256=sha256((ROOT/'game/assets/map-campaign.png').read_bytes()), save=saved)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(args.output, 'wt', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False)


def replay(args):
    with gzip.open(args.checkpoint, 'rt', encoding='utf-8') as stream:
        source = json.load(stream)
    checks, counters = [], {'route_pairs': 0}
    decisions_hash = None

    def count(stack, module, name, *, route=False):
        impl = getattr(module, name)
        def measured(*values, **options):
            counters[name] = counters.get(name, 0) + 1
            if route:
                counters['route_pairs'] += len(values[3])
            start = process_time()
            result = impl(*values, **options)
            key = name + '_cpu'
            counters[key] = counters.get(key, 0) + process_time() - start
            return result
        stack.enter_context(patch.object(module, name, measured))

    def observe(event, row):
        if decisions_hash is not None and event in {
                'order_reserved', 'order_dispatched', 'order_delivered', 'order_closed', 'escort_receipt'}:
            decisions_hash.update(canonical([event, row]).encode())

    rank = granary_planning._rank

    def ranked(quote):
        result = rank(quote)
        if decisions_hash is not None:
            decisions_hash.update(canonical([quote['source'], quote['target'], quote['path'], result]).encode())
        return result

    from hashlib import sha256 as digest
    game = campaign(source['scenario'])
    with ExitStack() as stack:
        configure(stack, source['strategy'], source['weather'], args.detailed)
        if args.detailed:
            stack.enter_context(strategic_granary.observing(observe))
            stack.enter_context(patch.object(granary_planning, '_rank', ranked))
        if args.counters:
            for module, name in ((granary_planning.Network, '__init__'), (granary_planning.Network, '_donor'),
                                 (faction_economy, 'plan'), (faction_economy, '_forecast'),
                                 (granary_planning, '_risk'), (logistics, 'escort_rations'),
                                 (granary_planning.Network, 'shipment'), (march_core, '_encode_request')):
                count(stack, module, name)
            count(stack, logistics, '_supply_routes', route=True)
        game.load_save(source['save'], 0)
        for n in range(args.turns):
            decisions_hash = digest() if args.detailed else None
            profiler = cProfile.Profile() if n == 0 and args.profile else None
            wall, cpu = monotonic(), process_time()
            with profiler if profiler is not None else nullcontext():
                game.command('observe_turn', {}, game.revision)
            wall, cpu = monotonic()-wall, process_time()-cpu
            if profiler is not None:
                args.profile.parent.mkdir(parents=True, exist_ok=True)
                profiler.dump_stats(args.profile)
            state = game.to_dict()
            checks.append(dict(turn=game.state.turn, checksum=sha256(canonical(state).encode()),
                               rng=state['rng'], wall=wall, cpu=cpu,
                               decisions=None if decisions_hash is None else decisions_hash.hexdigest()))
    peak = getrusage(RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin':
        peak *= 1024
    to_json(args.output, dict(checkpoint_sha256=sha256(args.checkpoint.read_bytes()),
                              revision=git('rev-parse', 'HEAD').decode().strip(), detailed=args.detailed,
                              counters=counters, checks=checks, peak_rss_bytes=peak,
                              backend=march_core.backend_status()))


def main():
    parser = ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    before = modes.add_parser('capture')
    before.add_argument('scenario')
    before.add_argument('turn', type=int)
    before.add_argument('output', type=Path)
    before.add_argument('--seed', type=int, default=2026)
    before.add_argument('--strategy', type=int, choices=(211, 212), default=211)
    before.add_argument('--weather', type=int, choices=(0, 221), default=221)
    before.add_argument('--resume', type=Path)
    after = modes.add_parser('replay')
    after.add_argument('checkpoint', type=Path)
    after.add_argument('output', type=Path)
    after.add_argument('--turns', type=int, default=12)
    after.add_argument('--profile', type=Path)
    after.add_argument('--detailed', action='store_true')
    after.add_argument('--counters', action='store_true')
    args = parser.parse_args()
    (capture if args.mode == 'capture' else replay)(args)


if __name__ == '__main__':
    main()
