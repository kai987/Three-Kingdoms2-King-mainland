"""Exact Python/native/WASM parity, including current save/RNG fixtures.

Use --wasm-vectors to emit read-only Python reference vectors for Node's real
WebAssembly ABI test. No live server or existing player campaign is changed.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.campaign import Campaign, Catalog, canonical, digest
from remake.errors import GameError
from remake.march_core import CoreUnavailable, config_for, invoke, using_backend
from remake.route_hazards import allocate_survivors, evaluate_leg, route_allowed
from remake.travel import TravelCampaign

CASES = [
    ('plain', 'shu', 'jiameng', 'fuxian', 'fastest', 7),
    ('yinping', 'wei', 'yinping', 'shujun', 'special', 7),
    ('ziwu-rain', 'wei', 'hanzhong', 'jingzhao', 'special', 7),
    ('ziwu-dry', 'wei', 'hanzhong', 'jingzhao', 'special', 4),
    ('sea-tail', 'wu', 'hepu', 'zhuya', 'sea', 1),
    ('sea-head', 'wu', 'hepu', 'zhuya', 'sea', 7),
    ('sea-calm', 'wu', 'hepu', 'zhuya', 'sea', 4),
    ('explore', 'wu', 'hepu', 'yizhou', 'explore', 7),
]


def campaign_fixture(case):
    name, side, source, target, mode, month = case
    # Keep the fixed march vectors independent of seasonal city disasters.
    # Dedicated facility tests exercise those new calendar RNG draws.
    data=json.loads((ROOT/'game/data/campaigns/217-07.json').read_text())
    data['facility_rules']['disasters_enabled']=False
    data['facility_ai_default']=False
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'march-fixture.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        catalog=Catalog(path)
    game = Campaign(catalog)
    game.command('new', dict(faction=side, seed=2026), 0)
    while game.state.month != month:
        game._complete_turn(game.state)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
    destination = game.state.cities[target]
    if destination.owner != side:
        # Controlled friendly destination; preserve all identities and troops.
        for ident in destination.roster.officer_ids:
            other = next(c for c in game.state.cities.values()
                         if c.id != target and c.owner == destination.owner and len(c.roster.officer_ids) < game.catalog.rules.city_officer_capacity)
            other.roster.officer_ids.append(ident)
        destination.roster.officer_ids.clear()
        destination.owner = side
    game._reconcile_factions(game.state)
    game.validate(game.state)
    return game


def campaign_result(case, alternate_backend=None):
    name, side, source, target, mode, month = case
    game = campaign_fixture(case)
    result = {}

    def checkpoint(label):
        game.validate(game.state)
        saved = game.export_save()
        result[label] = dict(save=digest(saved), state=digest(game.to_dict()),
                             rng=dict(state=game.state.rng.state, draws=game.state.rng.draws),
                             soldiers=game.state.soldiers.copy(), turn=game.state.turn)

    checkpoint('before')
    for _ in range(3):
        game._travel_path(game.state, source, target, side, mode)
    checkpoint('preview')
    ids = game.state.cities[source].roster.officer_ids[:3]
    game.command('transfer', dict(source=source, target=target, officers=ids, route_mode=mode), game.revision)
    checkpoint('queued')
    result['quote'] = game.state.extension['travel']['marches'][0]['quote']
    saved = game.export_save()
    if alternate_backend:
        with using_backend(alternate_backend):
            loaded = Campaign(game.catalog)
            loaded.load_save(saved, 0)
            assert canonical(loaded.export_save()) == canonical(saved)
    loaded = Campaign(game.catalog)
    loaded.load_save(saved, 0)
    assert canonical(loaded.to_dict()) == canonical(game.to_dict())
    assert canonical(loaded.export_save()) == canonical(saved)
    while game.state.turn < game.state.extension['travel']['marches'][0]['arrival_turn']:
        game._complete_turn(game.state)
        game._spawn_eligible(game.state)
        game._reconcile_factions(game.state)
        game.validate(game.state)
    game.command('arrivals', {}, game.revision)
    checkpoint('arrived')
    result['troops'] = [game.state.officers[i].troops for i in ids]
    assert not game.state.extension['travel']['marches']
    loaded = Campaign(game.catalog)
    loaded.load_save(game.export_save(), 0)
    assert canonical(loaded.export_save()) == canonical(game.export_save())
    return result


def route_state(cities, month, discovered=(), player='friendly'):
    return SimpleNamespace(cities={row['id']: SimpleNamespace(**row) for row in cities},
                           month=month, player=player,
                           extension={'travel': {'discovered': list(discovered)}})


def reference(request, data=None):
    """Run only retained Python arithmetic; never silently call the native core."""
    args = {k: v for k, v in request.items() if k not in ('op', 'config')}
    try:
        with using_backend('python'):
            op = request['op']
            if op == 'allocate':
                value = allocate_survivors(args['troops'], args['numerator'], args['denominator'])
            elif op == 'allowed':
                value = route_allowed(data, args['route'], args['source'], args['target'])
            elif op == 'evaluate_leg':
                value = evaluate_leg(data, args['route'], args['source'], args['target'], args['month'])
            elif op in ('path', 'batch'):
                travel = TravelCampaign()
                travel.catalog = SimpleNamespace(data=data, links={frozenset(p) for p in data.get('links', [])})
                state = route_state(args['cities'], args['month'], args.get('discovered', []), args.get('player', 'friendly'))
                if op == 'path':
                    value = travel._travel_path(state, args['source'], args['target'], args['owner'],
                                                args['mode'], adjacent=args.get('adjacent', False))
                else:
                    value = travel._travel_view(state)['travel_quotes']
            elif op == 'survival_preview':
                low, high = list(args['troops']), list(args['troops'])
                seen_storm = False
                for leg in args['quote']['routes']:
                    hazard = leg.get('hazard')
                    if not hazard:
                        continue
                    if hazard['kind'] == 'monsoon_storm':
                        if seen_storm:
                            continue
                        seen_storm = True
                        low = allocate_survivors(low, 100 - hazard['loss_percent_max'], 100)
                        high = allocate_survivors(high, 100 - hazard['loss_percent_min'], 100)
                    else:
                        low = allocate_survivors(low, hazard['survival_numerator'], hazard['survival_denominator'])
                        high = allocate_survivors(high, hazard['survival_numerator'], hazard['survival_denominator'])
                value = dict(minimum=low, maximum=high)
            else:
                raise AssertionError(op)
        return dict(ok=True, value=value)
    except (ValueError, GameError) as error:
        return dict(ok=False, error=str(error))


def synthetic_config():
    def leg(ident, a, b, mode='land', distance=2.25):
        return dict(id=ident, **{'from': a, 'to': b}, mode=mode, terrain='plain',
                    distance_km=distance, land_km=0 if mode == 'sea' else distance,
                    sea_km=distance if mode == 'sea' else 0, days=1,
                    provenance={'whole_float': 4.0, 'keep': ['metadata']})
    # The direct scalar uses ID as its final tie break, bulk quotes retain raw
    # route order. A and B queue ties resolve by city ID before insertion order.
    return dict(travel_rules=dict(speeds={'plain': 30, 'sea': 70}, embark_days=2),
                travel_hazards={'schema': 'parity', 'coastal_cities': ['s', 'a', 'b', 't']},
                city_coordinates={'s': [110, 20], 'a': [111, 21], 'b': [109, 19], 't': [112, 22]},
                travel_routes=[leg('z-sea', 's', 't', 'sea'), leg('a-sea', 's', 't', 'sea'),
                               leg('s-b', 's', 'b'), leg('s-a', 's', 'a'),
                               leg('b-t', 'b', 't'), leg('a-t', 'a', 't')],
                exploration_routes=[leg('explore:a:b', 'a', 'b', 'sea')],
                links=[['s', 't'], ['s', 'a'], ['s', 'b'], ['a', 't'], ['b', 't']])


def neutral_transit_config():
    """A long neutral corridor with a shorter enemy-owned shortcut."""
    keys = ['s', *(f'n{i:02}' for i in range(1, 33)), 't']
    pairs = list(zip(keys, keys[1:])) + [('s', 'enemy'), ('enemy', 't')]
    return dict(travel_rules=dict(speeds={'plain': 30, 'sea': 70}, embark_days=2),
                travel_hazards={'schema': 'parity', 'coastal_cities': []},
                city_coordinates={key: [110 + index / 100, 30] for index, key in enumerate(keys + ['enemy'])},
                travel_routes=[dict(id=f'{a}:{b}:land', **{'from': a, 'to': b}, mode='land',
                    terrain='plain', distance_km=30, land_km=30, sea_km=0, days=1)
                    for a, b in pairs], exploration_routes=[], links=[list(p) for p in pairs])


def river_config():
    """Two surveyed water reaches with distinct directional cargo speeds."""
    return dict(travel_rules=dict(speeds={'plain': 30, 'sea': 70}, embark_days=2,
                    river_embark_days=1, river_speeds=dict(
                        yangtze=dict(upstream=20, downstream=50),
                        xiang=dict(upstream=22.5, downstream=35))),
                travel_hazards={'schema': 'parity', 'coastal_cities': []},
                city_coordinates={'s': [114.3, 30.5], 't': [112.9, 28.2]},
                travel_routes=[dict(id='s:t:river', **{'from': 's', 'to': 't'},
                    mode='river', terrain='river', distance_km=556, land_km=31,
                    river_km=525, sea_km=0, days=28,
                    river_segments=[dict(speed_key='yangtze', distance_km=300, downstream_from='t'),
                                    dict(speed_key='xiang', distance_km=225, downstream_from='t')]),
                    dict(id='s:t:land', **{'from': 's', 'to': 't'}, mode='land',
                    terrain='plain', distance_km=600, land_km=600, sea_km=0, days=20)],
                exploration_routes=[], links=[['s', 't']])


def vector_document():
    """Reference matrices cover every current leg in both directions/months."""
    current = config_for(Catalog(ROOT / 'game/data/campaigns/217-07.json').data)
    return [current, synthetic_config(), neutral_transit_config(), river_config()]


def vectors(configs):
    current, synthetic, neutral, river = configs
    for index, data in enumerate(configs):
        routes = data['travel_routes'] + data.get('exploration_routes', [])
        months = range(1, 13)
        for row in routes:
            for source, target in ((row['from'], row['to']), (row['to'], row['from'])):
                allowed = dict(op='allowed', config=index, route=row, source=source, target=target)
                yield f'allowed:{index}:{row["id"]}:{source}', allowed
                for month in months:
                    yield f'leg:{index}:{row["id"]}:{source}:{month}', dict(
                        allowed, op='evaluate_leg', month=month)
    data = current
    cities = [{'id': city['id'], 'owner': 'friendly' if i % 3 else 'enemy'}
              for i, city in enumerate(Catalog(ROOT / 'game/data/campaigns/217-07.json').data['cities'])]
    for month in (4, 7, 11):
        # Every physical connection, not only routes held by the player's faction.
        for row in data['travel_routes']:
            for mode in ('fastest', 'land', 'river', 'sea', 'special', 'explore'):
                request = dict(op='path', config=0, cities=cities, month=month, discovered=[],
                               source=row['from'], target=row['to'], owner='friendly', mode=mode, adjacent=True)
                yield f'path:{row["id"]}:{month}:{mode}', request
    keys = list(synthetic['city_coordinates'])
    for ownership in (['friendly'] * 4, ['friendly', 'enemy', 'friendly', 'enemy'],
                      ['friendly', 'neutral', 'neutral', 'friendly']):
        cities = [dict(id=key, owner=owner) for key, owner in zip(keys, ownership)]
        for discovered in ([], ['explore:a:b']):
            for month in (4, 7, 11):
                base = dict(config=1, cities=cities, month=month, discovered=discovered)
                yield f'batch:tie:{ownership}:{discovered}:{month}', dict(base, op='batch', player='friendly')
                for source in keys:
                    for target in keys + ['missing']:
                        for mode in ('fastest', 'land', 'river', 'sea', 'special', 'explore'):
                            yield f'tie:{source}:{target}:{mode}:{month}', dict(
                                base, op='path', source=source, target=target,
                                owner='friendly', mode=mode, adjacent=ownership[keys.index(target)] != 'friendly' if target in keys else True)
    for side in ('shu', 'wu', 'wei'):
        game = Campaign(Catalog(ROOT / 'game/data/campaigns/217-07.json'))
        with using_backend('python'):
            game.command('new', dict(faction=side, seed=2026), 0)
        yield f'batch:actual:{side}', dict(op='batch', config=0,
            cities=[dict(id=c.id, owner=c.owner) for c in game.state.cities.values()],
            month=game.state.month, discovered=[], player=side)
    neutral_owners = {key: 'friendly' if key in ('s', 't') else
                      'enemy' if key == 'enemy' else 'neutral' for key in neutral['city_coordinates']}
    for changed, owner in ((None, None), ('n01', 'friendly'), ('n16', 'enemy'),
                           ('n32', 'enemy'), ('t', 'neutral'), ('t', 'enemy')):
        owners = dict(neutral_owners)
        if changed is not None:
            owners[changed] = owner
        base = dict(config=2, cities=[dict(id=key, owner=value) for key, value in owners.items()],
                    month=4, discovered=[])
        yield f'batch:neutral:{changed}:{owner}', dict(base, op='batch', player='friendly')
        for source, target in (('s', 't'), ('t', 's'), ('s', 'n01'), ('s', 'n32'), ('s', 'enemy')):
            for mode in ('fastest', 'land'):
                for adjacent in (False, True):
                    yield f'path:neutral:{changed}:{owner}:{source}:{target}:{mode}:{adjacent}', dict(
                        base, op='path', source=source, target=target, owner='friendly',
                        mode=mode, adjacent=adjacent)
    for month in range(1, 13):
        for destination_owner in ('friendly', 'neutral', 'enemy'):
            base = dict(config=3, cities=[dict(id='s', owner='friendly'),
                        dict(id='t', owner=destination_owner)], month=month, discovered=[])
            yield f'batch:river:{month}:{destination_owner}', dict(base, op='batch', player='friendly')
            for source, target in (('s', 't'), ('t', 's')):
                for mode in ('fastest', 'land', 'river', 'sea', 'explore'):
                    for adjacent in (False, True):
                        yield f'path:river:{month}:{destination_owner}:{source}:{mode}:{adjacent}', dict(
                            base, op='path', source=source, target=target, owner='friendly',
                            mode=mode, adjacent=adjacent)
    for name, patch in (
            ('no-segments', {'river_segments': []}),
            ('missing-flow', {'river_segments': [dict(distance_km=30)]}),
            ('unknown-flow', {'river_segments': [dict(distance_km=30, downstream_from='missing')]}),
            ('boolean-flow', {'river_segments': [dict(distance_km=30, downstream_from=True)]}),
            ('zero-distance', {'river_segments': [dict(distance_km=0, downstream_from='t')]}),
            ('boolean-distance', {'river_segments': [dict(distance_km=True, downstream_from='t')]}),
            ('unknown-speed', {'river_segments': [dict(distance_km=30, downstream_from='t', speed_key='missing')]}),
            ('bad-speed-key', {'river_segments': [dict(distance_km=30, downstream_from='t', speed_key=[])]}),
            ('negative-land', {'land_km': -1})):
        raw = dict(river['travel_routes'][0], **patch)
        yield f'invalid-river:{name}', dict(op='evaluate_leg', config=3, route=raw,
            source='s', target='t', month=7)
    seeded = random.Random(20261022)
    counts = [[], [0], [1, 1, 1], [1, 2], [0, 1, 2, 999, 1000], [999] * 30, [1000] * 30, [1000] * 99]
    counts += [[seeded.randrange(100001) for _ in range(seeded.randrange(31))] for _ in range(40)]
    for troops in counts:
        for numerator, denominator in ((0, 1), (1, 1), (1, 3), (1, 2), (4, 5), (1, 10), (19, 100)):
            yield f'allocate:{len(troops)}:{numerator}:{denominator}', dict(
                op='allocate', troops=troops, numerator=numerator, denominator=denominator)
    for troops, numerator, denominator in (([-1], 1, 3), ([True], 1, 3), ([1.5], 1, 3),
                                          ([1], True, 3), ([1], 1, 1.0), ([1], -1, 3), ([1], 4, 3), ([1], 1, 0)):
        yield ('invalid-float-spelling' if type(denominator) is float else 'invalid-allocation'), dict(op='allocate', troops=troops, numerator=numerator, denominator=denominator)
    raw = current['travel_routes'][0]
    for month in (0, 13, True, 1.5):
        yield 'invalid-month', dict(op='evaluate_leg', config=0, route=raw,
                                   source=raw['from'], target=raw['to'], month=month)
    # Two storms plus a fixed loss: storm is applied once at its first leg.
    storm = dict(kind='monsoon_storm', loss_percent_min=80, loss_percent_max=90)
    fixed = dict(kind='yinping', survival_numerator=1, survival_denominator=3)
    quote = {'routes': [{'hazard': storm}, {'hazard': fixed}, {'hazard': storm}]}
    for troops in counts:
        yield 'survival-preview-multileg', dict(op='survival_preview', quote=quote, troops=troops)


class MarchReferenceBaselineTests(unittest.TestCase):
    def test_current_python_campaign_save_and_rng_hashes(self):
        expected = json.loads((ROOT / 'tests/fixtures/march-python-baseline.json').read_text())
        with using_backend('python'):
            for case in CASES:
                with self.subTest(case=case[0]):
                    self.assertEqual(canonical(campaign_result(case)), canonical(expected[case[0]]))


class MarchNativeParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            with using_backend('rust'):
                invoke('allocate', troops=[], numerator=1, denominator=1)
        except CoreUnavailable as error:
            if os.environ.get('MARCH_CORE_BACKEND') == 'rust':
                raise
            raise unittest.SkipTest(f'Build Rust march core first: {error}')

    def test_every_leg_month_paths_batches_and_integer_casualties(self):
        configs = vector_document()
        with using_backend('rust'):
            for label, request in vectors(configs):
                config = request.get('config')
                data = configs[config] if config is not None else None
                expected = reference(request, data)
                args = {k: v for k, v in request.items() if k not in ('op', 'config')}
                try:
                    actual = dict(ok=True, value=invoke(request['op'], data=data, **args))
                except ValueError as error:
                    actual = dict(ok=False, error=str(error))
                # Canonical comparison catches 50.0 vs50 and1ULP differences that
                # Python equality would otherwise hide from saved checksums.
                if canonical(actual) != canonical(expected):
                    self.fail(f'{label}\nrequest={request}\nexpected={canonical(expected)}\nactual={canonical(actual)}')

    def test_abi_rejects_malformed_json_and_concurrent_calls_do_not_mix_buffers(self):
        from concurrent.futures import ThreadPoolExecutor
        import ctypes
        import remake.march_core as adapter
        with using_backend('rust'):
            lib = adapter._load()
            with adapter._lock:
                malformed = b'{invalid-json'
                source = lib.march_alloc(len(malformed))
                ctypes.memmove(source, malformed, len(malformed))
                result = lib.march_call(source, len(malformed))
                length = lib.march_result_len()
                try:
                    self.assertFalse(json.loads(ctypes.string_at(result, length))['ok'])
                finally:
                    lib.march_free(result, length)
                    lib.march_free(source, len(malformed))

        def calculate(index):
            with using_backend('rust'):
                troops = [index, index + 1, index + 2]
                actual = invoke('allocate', troops=troops, numerator=1, denominator=3)
            with using_backend('python'):
                expected = allocate_survivors(troops, 1, 3)
            return actual == expected

        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertTrue(all(pool.map(calculate, range(200))))

    def test_native_context_cache_is_bounded_and_releases_evicted_contexts(self):
        import remake.march_core as adapter
        with using_backend('rust'):
            for index in range(150):
                data = dict(travel_rules={'parity_index': index}, travel_routes=[])
                self.assertEqual(invoke('allocate', data=data, troops=[1, 1, 1], numerator=1, denominator=3), [1, 0, 0])
            self.assertLessEqual(adapter.backend_status()['contexts'], 128)

    def test_mutable_pure_helper_inputs_refresh_without_mutating_or_caching_them(self):
        data = synthetic_config()
        raw = data['travel_routes'][0]
        changes = [
            lambda: None,
            lambda: data['travel_hazards'].update(monsoon={'storm_loss_percent': [70, 72]}),
            lambda: data['travel_rules']['speeds'].update(plain=50),
            lambda: data['city_coordinates'].update(t=[100, 10]),
            lambda: data['travel_hazards']['monsoon'].update(headwind_speed_divisor=2),
        ]
        with using_backend('rust'):
            for change in changes:
                change()
                before = deepcopy(data)
                request = dict(op='evaluate_leg', route=raw, source='s', target='t', month=7)
                expected = reference(request, data)
                actual = dict(ok=True, value=invoke('evaluate_leg', data=data, route=raw, source='s', target='t', month=7))
                self.assertEqual(canonical(actual), canonical(expected))
                self.assertEqual(data, before)
            land = next(row for row in data['travel_routes'] if row['id'] == 's-a')
            self.assertTrue(invoke('allowed', data=data, route=land, source='a', target='s'))
            data['travel_hazards']['yinping'] = {'from': 's', 'to': 'a'}
            self.assertFalse(invoke('allowed', data=data, route=land, source='a', target='s'))

    def test_three_natural_ai_ten_day_turns_preserve_each_command_state_save_and_rng(self):
        catalog = Catalog(ROOT / 'game/data/campaigns/217-07.json')
        reference_game, native_game = Campaign(catalog), Campaign(catalog)
        transcript, phases, saw_march = [], set(), False

        def dispatch(kind, payload):
            nonlocal saw_march
            with using_backend('python'):
                reference_game.command(kind, deepcopy(payload), reference_game.revision)
                expected_state = canonical(reference_game.to_dict())
                expected_save = canonical(reference_game.export_save())
            with using_backend('rust'):
                native_game.command(kind, deepcopy(payload), native_game.revision)
                actual_state = canonical(native_game.to_dict())
                actual_save = canonical(native_game.export_save())
            transcript.append((kind, payload))
            label = f'command{len(transcript)}: {kind} {payload}'
            self.assertEqual(actual_state, expected_state, label)
            self.assertEqual(actual_save, expected_save, label)
            self.assertEqual(native_game.revision, reference_game.revision, label)
            self.assertEqual(native_game.journal, reference_game.journal, label)
            self.assertEqual((native_game.state.rng.state, native_game.state.rng.draws),
                             (reference_game.state.rng.state, reference_game.state.rng.draws), label)
            saw_march |= bool(reference_game.state.extension['travel']['marches'])

        dispatch('new', dict(faction='wu', seed=2026))
        for _ in range(100):
            state = reference_game.state
            phases.add(state.phase)
            if state.turn >= 4 and state.phase == 'city':
                break
            if state.phase == 'city':
                kind, payload = 'end_turn', {}
            elif state.phase == 'ai':
                kind, payload = 'ai', {'turn': state.turn}
            elif state.phase == 'arrivals':
                kind, payload = 'arrivals', {}
            elif state.phase == 'battle':
                kind, payload = 'retreat', {'battle_id': state.battle['id']}
            elif state.phase == 'result':
                kind, payload = 'settle', {'battle_id': state.battle['id']}
            else:
                self.fail(f'Unexpected natural replay phase: {state.phase}; commands={transcript}')
            dispatch(kind, payload)
        else:
            self.fail(f'Natural AI replay exceeded100commands: {transcript}')
        self.assertEqual((reference_game.state.year, reference_game.state.month, reference_game.state.day), (217, 8, 1))
        self.assertTrue({'ai', 'arrivals'} <= phases)
        self.assertTrue(saw_march, 'Natural AI must queue a real march')
        self.assertGreater(reference_game.state.rng.draws, 0)

    def test_full_campaigns_and_cross_backend_pending_save_loads_match_reference(self):
        expected = json.loads((ROOT / 'tests/fixtures/march-python-baseline.json').read_text())
        for backend, alternate in (('rust', 'python'), ('python', 'rust')):
            with using_backend(backend):
                for case in CASES:
                    with self.subTest(backend=backend, case=case[0]):
                        self.assertEqual(canonical(campaign_result(case, alternate)), canonical(expected[case[0]]))


if __name__ == '__main__':
    if '--wasm-vectors' in sys.argv:
        configs = vector_document()
        print(json.dumps(dict(configs=configs), ensure_ascii=False, separators=(',', ':')))
        for label, request in vectors(configs):
            config = request.get('config')
            expected = reference(request, configs[config] if config is not None else None)
            print(json.dumps(dict(label=label, request=request, expected=expected), ensure_ascii=False, separators=(',', ':')))
    else:
        unittest.main()
