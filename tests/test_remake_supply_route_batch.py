"""A shared route search must preserve the per-target search and its tie order."""
from random import Random
from unittest import TestCase
from unittest.mock import patch

from remake import logistics, march_core, winter_weather
from test_remake_regional_market import OWNER, SOURCE, TARGET, controlled


class SupplyRouteBatchTests(TestCase):
    def test_qualified_route_batches_match_independent_queries_after_input_changes(self):
        with winter_weather.experiment(5, adjustments=winter_weather.CORRECTIONS):
            game = controlled()
        state = game.state
        random = Random(3021)
        keys = list(state.cities)
        policy = logistics._pool(state)['cities'][SOURCE]['policy']
        with march_core.using_backend('python'):
            for revision in range(20):
                state.month = revision % 12 + 1
                state.cities[TARGET].owner = OWNER if revision % 3 else 'neutral'
                pool = state.extension[winter_weather.POOL]
                pool['tick'] = revision
                for index, row in enumerate(pool['regions'].values()):
                    row.update(severity=(revision + index) % 3, depth=revision % 7)
                for index, row in enumerate(pool['ice'].values()):
                    row['state'] = (revision + index) % 4
                policy.update(allow_sea=bool(revision % 2), allow_special=bool(revision % 3))
                owned = [key for key, city in state.cities.items() if city.owner == OWNER]
                pairs = [(random.choice(owned if slot % 2 else keys), random.choice(owned))
                         for slot in range(50)]
                before = game.to_dict()
                engine = logistics._safe_engine(game, policy)
                expected = {f'{a}:{b}:{mode}': engine._python_travel_path(state, a, b, OWNER, mode)
                            for a, b in pairs for mode in ('land', 'fastest')}
                with patch.object(engine, '_known_routes', wraps=engine._known_routes) as graph:
                    actual = engine._python_supply_paths(state, OWNER, pairs)
                self.assertEqual(graph.call_count, 1)
                self.assertEqual(list(expected.items()), list(actual.items()))
                self.assertEqual(game.to_dict(), before)

    def test_multiple_targets_share_the_same_search_and_owner_access(self):
        game = controlled()
        state = game.state
        owned = [key for key, city in state.cities.items() if city.owner == OWNER and key != SOURCE]
        self.assertGreater(len(owned), 1)
        pairs = [(SOURCE, key) for key in owned]
        with patch.object(game, '_python_path_search', wraps=game._python_path_search) as search:
            actual = game._python_supply_paths(state, OWNER, pairs)
        self.assertEqual(search.call_count, 2)
        self.assertTrue(any(quote is not None for quote in actual.values()))
