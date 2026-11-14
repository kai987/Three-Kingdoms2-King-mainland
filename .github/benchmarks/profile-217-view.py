"""Record full-view timings without changing the original replay or its return values."""
from collections import Counter
from contextlib import ExitStack
from functools import wraps
import importlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter_ns, process_time_ns
from unittest.mock import patch

replay_profile = importlib.import_module('profile-217')

EXPECTED_NATIVE = '9d222a77196b8bb7ad5e827ddcb38b3ecdc3b1c1984ebf0ab8a2f63c463dc553'
EXPECTED_SAVE_SEQUENCE = '355e916b253c67fe37c0ee0f75385d6bc3ba45b19c98eca428ae1ca63a33f74b'
EXPECTED_RESTORE_SEQUENCE = 'acef98bd65742159638ffdf17bedc221971ea6356385f86e66835c8d0daa7cfa'


class ViewProfile:
    def __init__(self, digest):
        self.digest = digest
        self.rows = []
        self.current = None
        self.path = []
        self.seen = {}
        self.held = []
        self.batches = []

    def capture(self, original):
        @wraps(original)
        def measured(game):
            caller = sys._getframe(1)
            file = Path(caller.f_code.co_filename).name
            state = game.state
            battle = state.battle or {}
            extended = battle.get('extended', {})
            placement = extended.get('placement')
            row = dict(index=len(self.rows) + 1, site=f'{caller.f_code.co_name}:{file}:{caller.f_lineno}',
                       turn=state.turn, phase=state.phase, target=battle.get('target'),
                       battle=battle.get('id'), round=battle.get('round'),
                       placement_confirmed=placement['confirmed'] if placement else None,
                       placement_total=len(placement['order']) if placement else None,
                       siege_stage=(extended.get('siege') or {}).get('stage'),
                       modules={}, repeated={})
            assert self.current is None
            self.current = row
            self.path = []
            self.seen = {}
            self.held = []
            start, cpu_start = perf_counter_ns(), process_time_ns()
            try:
                view = original(game)
            finally:
                row['cpu_ns'] = process_time_ns() - cpu_start
                row['wall_ns'] = perf_counter_ns() - start
                self.current = None
                self.seen.clear()
                self.held.clear()
            for batch in self.batches:
                batch['input_sha256'] = self.digest(batch.pop('payload'))
                batch['output_sha256'] = self.digest(batch.pop('result'))
            row['native_batches'] = self.batches
            self.batches = []
            # The output check is outside the timing window and never replaces a view.
            row['view_sha256'] = self.digest(view)
            self.rows.append(row)
            return view
        return measured

    def instrument(self, patches, owner, method, key=None):
        original = getattr(owner, method)
        label = f'{owner.__name__.split(".")[-1]}.{method}'

        @wraps(original)
        def measured(*args, **kwargs):
            if self.current is None:
                return original(*args, **kwargs)
            previous_path = ' > '.join(self.path)
            self.path.append(label)
            path = ' > '.join(self.path)
            start, cpu_start = perf_counter_ns(), process_time_ns()
            try:
                result = original(*args, **kwargs)
            finally:
                cpu = process_time_ns() - cpu_start
                wall = perf_counter_ns() - start
                self.path.pop()
                row = self.current['modules'].setdefault(path, Counter())
                row.update(calls=1, wall_ns=wall, cpu_ns=cpu)
            if key is not None:
                token = label, key(*args, **kwargs)
                previous = self.seen.get(token)
                if previous is None:
                    self.seen[token] = (previous_path, result)
                    # Keep argument identities live until this full view returns.
                    self.held.append((args, kwargs))
                else:
                    first_path, first_result = previous
                    pair = f'{label} | {first_path or "(root)"} -> {previous_path or "(root)"}'
                    repeated = self.current['repeated'].setdefault(pair, Counter())
                    repeated.update(calls=1, equal=int(first_result == result),
                                    wall_ns=wall, cpu_ns=cpu)
            return result

        patches.enter_context(patch.object(owner, method, measured))

    def native_batches(self, patches, march_core):
        original = march_core.invoke

        @wraps(original)
        def measured(operation, *, data=None, **payload):
            if self.current is None or operation != 'batch':
                return original(operation, data=data, **payload)
            start, cpu_start = perf_counter_ns(), process_time_ns()
            result = original(operation, data=data, **payload)
            cpu = process_time_ns() - cpu_start
            wall = perf_counter_ns() - start
            self.batches.append(dict(payload=(march_core.config_for(data), payload), result=result,
                                     wall_ns=wall, cpu_ns=cpu))
            return result

        patches.enter_context(patch.object(march_core, 'invoke', measured))

    def install(self, patches, campaign):
        from remake import battle_ai_deployment, battle_auto_deployment, battle_deployment
        from remake import battle_grid, battle_placement, battle_services, battle_supply
        from remake import city_development, civil_staff, command_books, dated_events
        from remake import difficulty, diplomacy, domestic, equipment, facilities
        from remake import historical_campaigns, logistics, march_core, officer_relations
        from remake import tactic_effects, tactical_ai, treasures, troop_types

        for method in ('to_dict', '_travel_view', '_expanded_catalog_view', '_civil_staff_view'):
            self.instrument(patches, campaign, method)
        for module in (battle_grid, battle_supply, city_development, civil_staff, command_books,
                       diplomacy, domestic, equipment, facilities, logistics, officer_relations,
                       treasures, troop_types):
            self.instrument(patches, module, 'view')
        for module, method in (
            (dated_events, 'visible_factions'), (dated_events, 'foundings'),
            (difficulty, 'catalog_choices'), (historical_campaigns, 'alliances'),
            (battle_supply, 'rules'), (battle_placement, 'view'), (battle_placement, 'validate'),
            (battle_auto_deployment, 'view'), (battle_auto_deployment, 'validate'),
            (battle_grid, '_paths'), (battle_services, 'quote'),
            (tactical_ai, 'tactic_reason'), (tactic_effects, 'preview'),
            (logistics, 'preview'), (logistics, 'rescue_targets'),
            (logistics, 'treasure_transport'), (logistics, '_safe_path'),
            (march_core, 'invoke'), (equipment, 'initial_view'), (equipment, 'shop_stock'),
        ):
            self.instrument(patches, module, method)
        self.instrument(patches, campaign, '_known_routes',
                        lambda game, state: (id(game.catalog.data), id(state)))
        self.instrument(patches, campaign, '_neighbors',
                        lambda game, city, state=None: (id(game.catalog.data), id(state), city))
        for method in ('_free_candidates', '_persuadable'):
            self.instrument(patches, campaign, method,
                            lambda game, state, city: (id(game), id(state), city.id))
        self.instrument(patches, domestic, 'personnel_targets',
                        lambda game, state, city: (id(game), id(state), city))
        self.instrument(patches, domestic, '_owned_ids', lambda state, owner: (id(state), owner))
        self.instrument(patches, campaign, '_march_ids', lambda game, state: (id(game), id(state)))
        self.instrument(patches, facilities, '_prevention_quote',
                        lambda game, city, row, officer: (id(game), id(city), id(row), id(officer)))
        self.instrument(patches, troop_types, 'metadata', lambda person_id, base: (person_id, base))
        self.instrument(patches, troop_types, 'effective_affinity',
                        lambda person_id, base: (person_id, base))
        self.instrument(patches, battle_placement, '_zone',
                        lambda game, battle, side: (id(game.catalog), id(battle), side))
        self.instrument(patches, battle_auto_deployment, '_plans',
                        lambda game, battle: (id(game.catalog), id(battle)))
        self.instrument(patches, battle_deployment, 'placement_zone',
                        lambda catalog, battle, field, side: (id(catalog), id(field), side,
                            self.digest(battle['extended']['deployment'])))
        self.native_batches(patches, march_core)


def main():
    mode, = sys.argv[1:]
    assert mode in ('reference', 'detailed')
    # Import after shard discovery has established the test's normal source path.
    replay_profile.select_case('baseline')
    from remake.campaign import Campaign, digest

    profile = ViewProfile(digest)
    native = replay_profile.ROOT / 'build/march-core/libmarch_core.so'
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        assert replay_profile.sha256(native) == EXPECTED_NATIVE
    with ExitStack() as patches:
        if mode == 'detailed':
            profile.install(patches, Campaign)
        result = replay_profile.trial('baseline', view_profile=profile)
    assert result['save_export_sequence_sha256'] == EXPECTED_SAVE_SEQUENCE
    assert result['restored_save_and_rng_sequence_sha256'] == EXPECTED_RESTORE_SEQUENCE
    assert len(profile.rows) == result['categories']['full_view']['calls'] == 180
    assert Counter(row['site'].split(':')[0] for row in profile.rows) == {
        'presentation_checkpoint': 136, 'view': 44}
    assert all(timing['equal'] == timing['calls']
               for row in profile.rows for timing in row['repeated'].values())
    result.update(mode=mode, views=profile.rows)
    print(json.dumps(result, separators=(',', ':'), sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
